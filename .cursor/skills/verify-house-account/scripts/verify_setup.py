#!/usr/bin/env python3
"""Exercise setup in a disposable checkout without installing or configuring clients."""
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path

from verify import ROOT, database_digest, doctor


def main():
    (ROOT / 'artifacts/verification').mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix='setup-', dir=ROOT / 'artifacts/verification'))
    evidence.chmod(0o700)
    result = {'feature': 'setup', 'status': 'running', 'actions': []}

    def save():
        (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

    def drive(command, label, expected=0):
        result['doctor'] = doctor()
        action = {'command': command, 'label': label}
        result['actions'].append(action)
        save()
        child = subprocess.Popen(command, cwd=scratch, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True,
                                 env={**os.environ, 'TMPDIR': str(scratch), 'UV_OFFLINE': '1',
                                      'UV_PYTHON_DOWNLOADS': 'never'})
        try:
            stdout, stderr = child.communicate(timeout=180)
        except BaseException:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = child.communicate()
            raise
        finally:
            action['exit_code'] = child.returncode
            (evidence / (label + '.stdout')).write_text(stdout)
            (evidence / (label + '.stderr')).write_text(stderr)
            save()
        assert child.returncode == expected, f'{label}: expected {expected}, got {child.returncode}'
        return stdout

    def check_state(state, *, uat=False):
        report = json.loads((state / 'import.json').read_text())
        config = json.loads((state / 'mcp-config.json').read_text())['mcpServers']['house_account']
        assert report['status'] == 'success'
        assert config['type'] == 'stdio'
        assert config['command'] == str(checkout / '.venv/bin/python')
        args = config['args']
        assert args[:2] == ['-m', 'house_account.cli']
        database = Path(args[args.index('--database') + 1])
        ledger = Path(args[args.index('--ledger') + 1])
        assert database == (state / 'house_account.sqlite' if uat else checkout / 'var/house_account.sqlite')
        assert ledger == (state / 'decisions.jsonl' if uat else checkout / 'review/decisions.jsonl')
        assert args[args.index('--data') + 1] == str(ROOT / 'data')
        assert args[args.index('--as-of') + 1] == '2026-11-02'
        assert database.stat().st_mode & 0o777 == 0o600
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
            assert db.execute('PRAGMA user_version').fetchone()[0] == 2
        (evidence / (state.name + '-config.json')).write_text(json.dumps(config, indent=2) + '\n')
        return database

    try:
        initial = doctor()
        from house_account import adapters
        from house_account.storage import inventory
        before = inventory(ROOT / 'data', adapters.file_role)
        with tempfile.TemporaryDirectory(prefix='house-account-setup-') as directory:
            scratch = Path(directory).resolve()
            result['scratch'] = str(scratch)
            checkout = scratch / 'checkout with spaces'
            checkout.mkdir()
            for name in ('setup.sh', 'pyproject.toml', 'uv.lock', 'README.md'):
                shutil.copy2(ROOT / name, checkout / name)
            shutil.copytree(ROOT / 'src', checkout / 'src', ignore=shutil.ignore_patterns('__pycache__'))
            (checkout / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/configure_mcp.py', checkout / 'scripts/configure_mcp.py')
            command = ['sh', str(checkout / 'setup.sh'), '--client', 'none', '--data', str(ROOT / 'data')]
            invalid = command[:-1] + [str(scratch / 'missing-pack')]
            drive(invalid, 'missing-pack', expected=1)
            assert not (checkout / 'var').exists() and not (checkout / '.venv').exists()
            drive(command, 'normal-setup')
            normal = check_state(checkout / 'var/setup')
            digest = database_digest(normal)
            runs = []
            for i in range(2):
                drive(command + ['--uat'], f'uat-{i + 1}')
                states = set((checkout / 'var/uat').iterdir()) - set(runs)
                assert len(states) == 1
                state = states.pop()
                runs.append(state)
                assert check_state(state, uat=True) == state / 'house_account.sqlite'
                assert database_digest(normal) == digest
            assert not (checkout / '.mcp.json').exists()
            result['checks'] = ['Missing pack rejected before environment or state creation.',
                                'Real locked install, import, and portable configuration export passed.',
                                'Two UAT runs created distinct snapshots and preserved the normal snapshot.',
                                'No client registration was requested; copied project has no .mcp.json.']
            assert inventory(ROOT / 'data', adapters.file_role) == before
            result['source_files_unchanged'] = initial['input_files']
        result['status'] = 'pass'
    except BaseException as exc:
        result['status'] = 'failed'
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        result['scratch_removed'] = 'scratch' not in result or not Path(result['scratch']).exists()
        save()
        assert (evidence / 'result.json').is_file()
        print(json.dumps({'evidence': str(evidence), 'status': result['status'],
                          'scratch_removed': result['scratch_removed']}))


if __name__ == '__main__':
    main()

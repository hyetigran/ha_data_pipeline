#!/usr/bin/env python3
"""Drive public CLI commands; retain evidence separately from disposable databases."""
import argparse
import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def doctor():
    import house_account.cli
    from house_account import adapters
    from house_account.storage import inventory
    assert Path(house_account.cli.__file__).resolve() == ROOT / 'src/house_account/cli.py'
    assert sys.version_info[:2] == (3, 13)
    files = inventory(ROOT / 'data', adapters.file_role)
    return {'status': 'ready', 'module': house_account.cli.__file__,
            'python': sys.version, 'input_files': len(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('feature', choices=['doctor', 'import', 'inspect', 'replacement'])
    args = parser.parse_args()
    if args.feature == 'doctor':
        print(json.dumps(doctor()))
        return
    evidence_root = ROOT / 'artifacts/verification'
    evidence_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix=args.feature + '-', dir=evidence_root))
    os.chmod(evidence, 0o700)
    results = {'feature': args.feature, 'status': 'running', 'actions': [], 'checks': []}

    def save():
        (evidence / 'result.json').write_text(json.dumps(results, indent=2) + '\n')

    def drive(command, label, expected=0):
        # Each invocation is a fresh noninteractive CLI process, as in scripts/verify.py.
        results['doctor'] = doctor()
        results['actions'].append({'command': command, 'label': label})
        save()
        child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, start_new_session=True,
                                 env={**os.environ, 'TMPDIR': results['scratch']})
        try:
            stdout, stderr = child.communicate(timeout=180)
        except BaseException:
            # Terminate this run's process group, including a lane's importer child.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = child.communicate()
            (evidence / (label + '.stdout')).write_text(stdout)
            (evidence / (label + '.stderr')).write_text(stderr)
            results['actions'][-1]['exit_code'] = child.returncode
            raise
        process = subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
        (evidence / (label + '.stdout')).write_text(process.stdout)
        (evidence / (label + '.stderr')).write_text(process.stderr)
        results['actions'][-1]['exit_code'] = process.returncode
        save()
        assert process.returncode == expected, f'{label}: expected {expected}, got {process.returncode}'
        return process

    try:
        with tempfile.TemporaryDirectory(prefix='house-account-skill-') as scratch:
            database = Path(scratch) / 'snapshot.sqlite'
            results['scratch'] = scratch
            command = [sys.executable, '-m', 'house_account.cli', 'ingest', '--data', str(ROOT / 'data'),
                       '--database', str(database), '--report', str(evidence / 'import.json')]
            process = drive(command, 'ingest')
            report = json.loads(process.stdout)
            assert report['status'] == 'success'
            saved_report = json.loads((evidence / 'import.json').read_text())
            assert saved_report.pop('files')
            assert saved_report == report
            assert database.stat().st_mode & 0o777 == 0o600
            with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
                assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                assert not db.execute('PRAGMA foreign_key_check').fetchall()
                counts = {table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                          for table in ('providers', 'customers', 'properties', 'jobs', 'estimates', 'visits',
                                        'calendar_blocks', 'profiles', 'street_segments')}
                assert counts == report['entities']
                results['stored_counts'] = counts
            results['checks'].append('Report equals stdout; stored counts match; integrity, foreign keys, and mode 0600 pass.')
            lanes = {'import': [1], 'inspect': [2, 3, 4, 5, 6, 7, 10], 'replacement': [8]}[args.feature]
            for lane in lanes:
                drive([sys.executable, str(ROOT / 'scripts/verify.py'), '--stage', 'P1', '--lane', str(lane),
                       '--output', str(evidence / f'lane-{lane}.json')], f'lane-{lane}')
            if args.feature == 'replacement':
                before = hashlib.sha256(database.read_bytes()).hexdigest()
                bad = command.copy()
                bad[bad.index('--data') + 1] = str(Path(scratch) / 'missing-pack')
                failed = drive(bad, 'missing-pack', expected=1)
                assert json.loads(failed.stderr)['status'] == 'failed'
                assert hashlib.sha256(database.read_bytes()).hexdigest() == before
                # A directory is an unwritable report target, even for privileged users.
                failed_report = command.copy()
                failed_report[failed_report.index('--report') + 1] = scratch
                failed = drive(failed_report, 'report-publication-failure', expected=2)
                assert json.loads(failed.stderr)['status'] == 'published_report_failed'
                with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    assert db.execute('SELECT count(*) FROM jobs').fetchone()[0] == counts['jobs']
                results['checks'].append('Missing pack exits 1 and preserves snapshot hash; report failure exits 2 with usable published snapshot.')
            results['status'] = 'pass'
    except BaseException as exc:
        results['status'] = 'failed'
        results['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        results['scratch_removed'] = 'scratch' not in results or not Path(results['scratch']).exists()
        save()
        assert (evidence / 'result.json').is_file()
        print(json.dumps({'evidence': str(evidence), 'status': results['status'],
                          'scratch_removed': results['scratch_removed']}))


if __name__ == '__main__':
    main()

"""Exercise the real P2R migration on an isolated copy of the frozen P2 database."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from house_account.cli import ingest
from house_account.queries import (
    block_schedule,
    history_radius,
    property_history,
    provider_summary,
)

ROOT = Path('artifacts/P2R')
BASELINE = ROOT / 'baseline'


def rows(database: Path, sql: str) -> list:
    with sqlite3.connect(database) as connection:
        return connection.execute(sql).fetchall()


def backup(source: Path, target: Path) -> None:
    with sqlite3.connect(source) as left, sqlite3.connect(target) as right:
        left.backup(right)


def fingerprint(database: Path) -> dict:
    tables = ['source_records', 'occurrences', 'canonical_crosswalk', 'canonical_providers',
              'canonical_properties', 'canonical_jobs', 'canonical_estimates', 'canonical_visits',
              'service_completions', 'reconciliation_metadata']
    result = {}
    for table in tables:
        columns = [r[1] for r in rows(database, f'PRAGMA table_info({table})') if r[1] != 'ingested_at']
        facts = rows(database, f'SELECT {",".join(columns)} FROM {table}')
        result[table] = hashlib.sha256(json.dumps(sorted(facts, key=repr)).encode()).hexdigest()
    return result


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    database = ROOT / 'verified.sqlite'
    if database.exists():
        raise RuntimeError('Use a fresh artifacts/P2R/verified.sqlite for a reproducible migration run')
    backup(BASELINE/'house_account.sqlite', database)
    ledger = ROOT/'verification-empty-ledger.jsonl'
    assert not ledger.exists()
    receipts = []
    def command(*args: str) -> dict:
        proc = subprocess.run([sys.executable, '-m', 'house_account.cli', *args], text=True, capture_output=True, check=False)
        receipts.append({'args': args, 'exit_code': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr})
        (ROOT/'cli-receipts.json').write_text(json.dumps(receipts, indent=2)+'\n')
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)
    inode = database.stat().st_ino
    first = command('ingest', '--database', str(database), '--ledger', str(ledger))
    assert database.stat().st_ino == inode
    restored = ROOT/'restored-p2.sqlite'
    backup(database.with_name(database.name+'.pre-v2.bak'), restored)
    assert rows(restored, 'SELECT * FROM canonical_crosswalk ORDER BY source_id,kind') == rows(BASELINE/'house_account.sqlite', 'SELECT * FROM canonical_crosswalk ORDER BY source_id,kind')
    baseline_answers = json.loads((BASELINE/'queries.json').read_text())
    for kind, value in [('property','5823 Belmont Ave, Dallas, TX 75206'), ('block','4512 Live Oak St, Dallas, TX 75204'), ('radius','4512 Live Oak St, Dallas, TX 75204'), ('provider',baseline_answers['provider']['results']['provider_id'])]:
        proc = subprocess.run([sys.executable, '-m', 'house_account.cli', 'query', kind, value, '--database', str(restored)], env={**os.environ, 'PYTHONPATH':str((BASELINE/'code/src').resolve())}, text=True, capture_output=True, check=True)
        assert json.loads(proc.stdout) == baseline_answers[kind], kind
    assert rows(database, 'PRAGMA user_version') == [(2,)]
    assert rows(database, 'PRAGMA integrity_check') == [('ok',)]
    assert not rows(database, 'PRAGMA foreign_key_check')
    assert rows(database, 'SELECT count(*) FROM source_records') == [(46092,)]
    assert rows(database, 'SELECT count(*) FROM occurrences') == [(46888,)]
    old_sources = rows(BASELINE/'house_account.sqlite', 'SELECT id,content_hash FROM source_records ORDER BY id')
    assert rows(database, 'SELECT id,content_hash FROM source_records ORDER BY id') == old_sources
    before = fingerprint(database)
    repeat = command('ingest', '--database', str(database), '--ledger', str(ledger))
    assert database.stat().st_ino == inode
    assert fingerprint(database) == before
    try:
        ingest(Path('data'), database, ledger=ledger, fail_after=100)
    except (ValueError, RuntimeError):
        pass
    else:
        raise AssertionError('Injected failed import succeeded')
    assert fingerprint(database) == before
    recurring_source = '324f6ef294cb34d3f7c350ce26df2b23496d4335ebb11ff56d4eab1f90e78cfd'
    with sqlite3.connect(database) as connection:
        recurring = connection.execute("SELECT canonical_id FROM canonical_crosswalk WHERE source_id=? AND kind='job'", (recurring_source,)).fetchone()[0]
        assert connection.execute('SELECT lifecycle FROM canonical_jobs WHERE id=?', (recurring,)).fetchone() == ('active',)
        assert connection.execute("SELECT count(*) FROM canonical_visits WHERE job_id=? AND scheduling_state='completed'", (recurring,)).fetchone() == (46,)
        assert connection.execute("SELECT count(*) FROM canonical_visits WHERE job_id=? AND scheduling_state='scheduled'", (recurring,)).fetchone() == (2,)
        assert connection.execute('SELECT count(DISTINCT visit_id) FROM service_completions WHERE job_id=?', (recurring,)).fetchone() == (46,)
        dst = connection.execute("SELECT v.scheduled_start_utc,v.scheduled_start_local_date,v.scheduled_start_state,v.scheduled_end_utc FROM canonical_visits v JOIN canonical_crosswalk x ON x.canonical_id=v.id AND x.kind='visit' JOIN source_records s ON s.id=x.source_id WHERE s.source_key='job:job_ff1d934b288cafe44328e65ac5b42d15'").fetchone()
        assert dst == (None, '2026-11-01', 'ambiguous', '2026-11-01T09:00:00+00:00'), dst
        assert not connection.execute('SELECT c.id FROM service_completions c JOIN canonical_visits v ON v.id=c.visit_id WHERE v.estimate_id IS NOT NULL OR v.job_id != c.job_id').fetchall()
    old_ids = {(r[0], r[1]): r[2] for r in json.loads((BASELINE/'membership.json').read_text())}
    new_ids = {(r[0], r[1]): r[2] for r in rows(database, 'SELECT source_id,kind,canonical_id FROM canonical_crosswalk')}
    changes = [{'source_id': key[0], 'kind': key[1], 'old': value, 'new': new_ids.get(key)} for key,value in old_ids.items() if new_ids.get(key) != value]
    (ROOT/'identity-changes.json').write_text(json.dumps(changes, indent=2)+'\n')
    assert all(new_ids.get(key) for key in old_ids), 'Lost old membership'
    schema = rows(database, "SELECT name,sql FROM sqlite_master WHERE type='table'")
    assert all('document' not in [c[1] for c in rows(database, f'PRAGMA table_info({name})')] for name,_ in schema if name.startswith('canonical_') and name != 'canonical_crosswalk')
    hashes = json.loads((BASELINE/'source-hashes.json').read_text())
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected for path,expected in hashes.items())
    lone = rows(database, "SELECT id FROM canonical_providers WHERE display_name = 'Lone Star Plumbing Co.' LIMIT 1")[0][0]
    answers = {'property': property_history(database, '5823 Belmont Ave, Dallas, TX 75206'),
               'block': block_schedule(database, '4512 Live Oak St, Dallas, TX 75204'),
               'radius': history_radius(database, '4512 Live Oak St, Dallas, TX 75204'),
               'provider': provider_summary(database, lone)}
    (ROOT/'queries.json').write_text(json.dumps(answers, indent=2)+'\n')
    report = {'status': 'pass', 'migration': first, 'repeat': repeat, 'source_hashes_unchanged': len(hashes),
              'source_records': 46092, 'occurrences': 46888, 'prior_memberships':len(old_ids),
              'changed_identity_memberships': len(changes), 'persistent_inode': True, 'backup_restore_reproduces_four_baseline_queries': True,
              'repeat_facts_unchanged': True, 'failed_import_preserves_snapshot': True}
    (ROOT/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'migration','repeat'}}))


if __name__ == '__main__':
    main()

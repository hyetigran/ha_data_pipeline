#!/usr/bin/env python3
"""Drive public CLI commands; retain evidence separately from disposable databases."""
import argparse
import hashlib
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from contextlib import closing
from itertools import pairwise
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


def database_digest(database):
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        digest = hashlib.sha256(str(db.execute('PRAGMA user_version').fetchone()).encode())
        for statement in db.iterdump():
            digest.update(statement.encode())
            digest.update(b'\n')
        return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('feature', choices=['doctor', 'import', 'inspect', 'replacement', 'history', 'review', 'migration', 'availability', 'mcp'])
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
        results['doctor'] = doctor()
        results['actions'].append({'command': command, 'label': label})
        save()
        child = subprocess.Popen(command, cwd=results['scratch'], stdout=subprocess.PIPE,
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
            ledger = Path(scratch) / 'review' / 'decisions.jsonl'
            command = [sys.executable, '-m', 'house_account.cli', 'ingest', '--data', str(ROOT / 'data'),
                       '--database', str(database), '--report', str(evidence / 'import.json'), '--ledger', str(ledger)]
            if args.feature == 'migration':
                baseline = ROOT / 'artifacts/P2R/baseline/house_account.sqlite'
                assert baseline.is_file(), 'Missing frozen legacy baseline: artifacts/P2R/baseline/house_account.sqlite'
                with closing(sqlite3.connect(baseline.as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(database)) as target:
                    source.backup(target)
                database.chmod(0o600)
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    assert db.execute('PRAGMA user_version').fetchone()[0] in (0, 1)
                legacy_digest, legacy_inode = database_digest(database), database.stat().st_ino
            process = drive(command, 'ingest')
            report = json.loads(process.stdout)
            assert report['status'] == 'success'
            saved_report = json.loads((evidence / 'import.json').read_text())
            assert saved_report.pop('files')
            assert saved_report == report
            assert database.stat().st_mode & 0o777 == 0o600
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                assert db.execute('PRAGMA user_version').fetchone()[0] == 2
                assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                assert not db.execute('PRAGMA foreign_key_check').fetchall()
                counts = {table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                          for table in ('providers', 'customers', 'properties', 'jobs', 'estimates', 'visits',
                                        'calendar_blocks', 'profiles', 'street_segments', 'provider_hour_declarations')}
                assert counts == report['entities']
                results['stored_counts'] = counts
            assert report['schema_version'] == 2
            assert report['publication'] == 'transactional' and report['reconciliation']
            results['checks'].append('Report equals stdout; source counts match; reconciliation, schema v2, transactional publication, integrity, foreign keys, and mode 0600 pass.')
            lanes = {'import': [1], 'inspect': [2, 3, 4, 5, 6, 7, 10], 'replacement': [8], 'history': [], 'review': [], 'migration': [], 'availability': [], 'mcp': []}[args.feature]
            for lane in lanes:
                drive([sys.executable, str(ROOT / 'scripts/verify.py'), '--stage', 'P1', '--lane', str(lane),
                       '--output', str(evidence / f'lane-{lane}.json')], f'lane-{lane}')
            if args.feature == 'mcp':
                drive([sys.executable, str(ROOT / 'scripts/verify_p4.py'), '--data', str(ROOT / 'data'),
                       '--database', str(database), '--output', str(evidence / 'p4')], 'mcp')
                summary = json.loads((evidence / 'p4/summary.json').read_text())
                assert summary['status'] == 'pass' and len(summary['tools_called']) == 6
                assert summary['scratch_removed'] and summary['database_logically_unchanged']
                assert summary['source_files_unchanged'] and summary['clean_shutdown']
                results['checks'].append('Six real MCP tools match direct-query expectations; invalid inputs reject safely; data and cleanup invariants pass.')
            if args.feature == 'availability':
                parent = Path(scratch) / 'parent'
                parent.mkdir()
                archive = Path(scratch) / 'parent.tar'
                drive(['git', '-C', str(ROOT), 'archive', '--format=tar', '--output', str(archive),
                       'c6c151ee3e95706ad178d2d661fc791f6106f616'], 'parent-archive')
                with tarfile.open(archive) as source:
                    source.extractall(parent, filter='data')
                before = database_digest(database)
                drive([sys.executable, str(Path(__file__).with_name('verify_availability.py')), '--database', str(database),
                       '--data', str(ROOT / 'data'), '--parent', str(parent),
                       '--output', str(evidence / 'p3')], 'availability')
                summary = json.loads((evidence / 'p3/maintained-summary.json').read_text())
                assert summary['status'] == 'pass' and len(summary['lanes']) == 10
                assert {lane['lane'] for lane in summary['lanes']} == set(range(1, 11))
                assert all(lane['status'] == 'pass' for lane in summary['lanes'])
                assert summary['scratch_removed'] and summary['database_logically_unchanged']
                assert summary['source_files_unchanged'] == results['doctor']['input_files']
                assert database_digest(database) == before
                results['checks'].append('Ten maintained availability lanes pass with original P3 verdicts retained and P4 additive schedule fields checked against SQLite; source files and database facts remain unchanged; nested scratch is removed.')
            if args.feature == 'migration':
                backup = Path(report['migration_backup'])
                assert backup.resolve() == database.with_name(database.name + '.pre-v2.bak').resolve()
                assert backup.stat().st_mode & 0o777 == 0o600
                assert database.stat().st_ino == legacy_inode
                restored = Path(scratch) / 'restored.sqlite'
                with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(restored)) as target:
                    source.backup(target)
                assert database_digest(restored) == legacy_digest
                results['checks'].append('Legacy snapshot migrated in place; private backup restores the original schema and all logical facts.')
            if args.feature == 'replacement':
                inode = database.stat().st_ino
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as reader:
                    reader.execute('BEGIN')
                    old_revision = reader.execute('SELECT id FROM snapshot').fetchone()[0]
                    drive(command, 'repeat-with-reader')
                    assert reader.execute('SELECT id FROM snapshot').fetchone()[0] == old_revision
                    reader.rollback()
                    assert reader.execute('SELECT id FROM snapshot').fetchone()[0] != old_revision
                assert database.stat().st_ino == inode
                results['checks'].append('Repeat publication preserves inode and pinned read revision; ending the transaction reveals the new revision.')
                before = database_digest(database)
                bad = command.copy()
                bad[bad.index('--data') + 1] = str(Path(scratch) / 'missing-pack')
                failed = drive(bad, 'missing-pack', expected=1)
                assert json.loads(failed.stderr)['status'] == 'failed'
                assert database_digest(database) == before
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    previous_snapshot = db.execute('SELECT id FROM snapshot').fetchone()[0]
                failed_report = command.copy()
                failed_report[failed_report.index('--report') + 1] = scratch
                failed = drive(failed_report, 'report-publication-failure', expected=2)
                assert json.loads(failed.stderr)['status'] == 'published_report_failed'
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    published_snapshot = db.execute('SELECT id FROM snapshot').fetchone()[0]
                    assert published_snapshot != previous_snapshot
                    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    assert db.execute('SELECT count(*) FROM jobs').fetchone()[0] == counts['jobs']
                results['publication'] = {'previous_snapshot': previous_snapshot,
                                          'published_snapshot': published_snapshot}
                results['checks'].append('Missing pack exits 1 and preserves logical database state; report failure exits 2 with a new snapshot ID and usable published snapshot.')
            if args.feature == 'history':
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    aliases = db.execute("SELECT DISTINCT p.display_name,x.canonical_id FROM providers p JOIN canonical_crosswalk x ON x.source_id=p.id AND x.kind='provider' WHERE p.display_name IN ('Big D Handyman','Lakewood Home Repair')").fetchall()
                    assert {name for name, _ in aliases} == {'Big D Handyman', 'Lakewood Home Repair'}
                    assert len({canonical for _, canonical in aliases}) == 1
                    provider = db.execute("SELECT id FROM canonical_providers WHERE display_name='Lone Star Plumbing Co.'").fetchone()[0]
                queries = {'property': '5823 Belmont Ave, Dallas, TX 75206',
                           'radius': '4512 Live Oak St, Dallas, TX 75204',
                           'block': '4512 Live Oak St, Dallas, TX 75204', 'provider': provider}
                answers = {}
                before = database_digest(database)
                for kind, value in queries.items():
                    response = drive([sys.executable, '-m', 'house_account.cli', 'query', kind, value,
                                      '--database', str(database)], 'query-' + kind)
                    answers[kind] = json.loads(response.stdout)
                    assert answers[kind]['coverage'] and answers[kind]['limitations']
                assert answers['property']['results']['distinct_jobs'] == 4
                assert len(answers['block']['results']) == 4
                assert answers['block']['uncertain_candidates']
                assert sum(row['distinct_jobs'] for row in answers['radius']['results']) == 969
                assert answers['provider']['results']['completed_distinct_jobs'] == 262
                assert answers['provider']['results']['opening_status'] in {'known', 'partial'}
                openings = answers['provider']['results']['openings']
                assert len(openings) == 3
                assert all(opening['start_utc'] < opening['end_utc'] for opening in openings)
                assert all(left['end_utc'] <= right['start_utc'] for left, right in pairwise(openings))
                import runpy
                reference = runpy.run_path(str(ROOT / 'scripts/verify_p2_independent.py'))
                for answer in answers.values():
                    reference['inspect_public'](answer)
                assert {ref for job in answers['property']['results']['jobs'] for ref in job['evidence_refs']} == reference['BELMONT_COMPLETED']
                assert {visit['visit_id'] for visit in answers['block']['results']} == reference['LIVE_OAK_VISITS']
                assert database_digest(database) == before
                drive([sys.executable, str(ROOT / 'scripts/verify_p2_independent.py'), '--database', str(database),
                       '--output', str(evidence / 'independent.json')], 'independent')
                results['checks'].append('Four public query commands match independently inspected pack answers, preserve database facts, retain uncertainty and exclude private fields; provider aliases reconcile.')
            if args.feature == 'review':
                review_file = Path(scratch) / 'review' / 'reconciliation.json'
                review_base = [sys.executable, '-m', 'house_account.cli', 'review']
                review_flags = ['--data', str(ROOT / 'data'), '--database', str(database),
                                '--file', str(review_file), '--ledger', str(ledger)]
                drive(review_base + ['export'] + review_flags, 'review-export')
                document = json.loads(review_file.read_text())
                assert document['proposals'] and all(p['human']['decision'] == 'defer' for p in document['proposals'])
                assert review_file.stat().st_mode & 0o777 == 0o600
                decisions = {'approve': 0, 'reject': 0, 'defer': 0}
                for proposal in document['proposals']:
                    choice = 'approve' if proposal['kind'] == 'field_correction' else 'reject' if decisions['reject'] == 0 else 'defer'
                    proposal['human'] = {'decision': choice, 'reviewer': 'Isolated verification',
                                         'decided_at': '2026-10-24T15:00:00Z', 'supersedes_decision_id': None,
                                         'reason': 'Disposable verification decision; not approval of active data.'}
                    decisions[choice] += 1
                assert all(decisions.values()), 'Pack must include approve, reject, and defer examples'
                review_file.write_text(json.dumps(document))
                drive(review_base + ['export'] + review_flags, 'review-export-preserve')
                assert json.loads(review_file.read_text()) == document
                correction_queries = {}
                expected_corrections = {'address': 5823, 'start_utc': '2025-11-10T16:00:00+00:00',
                                        'end_utc': '2025-11-10T18:00:00+00:00'}
                assert {p['proposed_action']['field'] for p in document['proposals'] if p['kind'] == 'field_correction'} == set(expected_corrections)
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    for proposal in document['proposals']:
                        if proposal['kind'] != 'field_correction':
                            continue
                        action = proposal['proposed_action']
                        canonical = db.execute("SELECT canonical_id FROM canonical_crosswalk WHERE kind='job' AND source_id=?", (action['targets'][0],)).fetchone()[0]
                        if action['field'] == 'address':
                            sql = 'SELECT p.house_number FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id WHERE j.id=?'
                            expected = 5823
                        else:
                            column = {'start_utc': 'scheduled_start_utc', 'end_utc': 'scheduled_end_utc'}[action['field']]
                            sql = f'SELECT {column} FROM canonical_visits WHERE job_id=?'
                            expected = expected_corrections[action['field']]
                            assert action['proposed'] == expected
                        old = db.execute(sql, (canonical,)).fetchone()[0]
                        correction_queries[proposal['proposal_id']] = (sql, canonical, old, expected)
                assert correction_queries
                before = database_digest(database)
                validation = drive(review_base + ['validate'] + review_flags, 'review-validate')
                assert json.loads(validation.stdout)['status'] == 'valid'
                assert database_digest(database) == before and not ledger.exists()
                preview = drive(review_base + ['apply', '--dry-run'] + review_flags, 'review-preview')
                assert json.loads(preview.stdout)['status'] == 'dry_run'
                assert database_digest(database) == before and not ledger.exists()
                assert not list(Path(scratch).glob('.review-*'))
                applied = drive(review_base + ['apply'] + review_flags, 'review-apply')
                assert json.loads(applied.stdout)['status'] == 'applied'
                assert ledger.stat().st_mode & 0o777 == 0o600
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    for sql, canonical, old, expected in correction_queries.values():
                        assert db.execute(sql, (canonical,)).fetchone()[0] == expected
                events = ledger.read_bytes()
                recorded = {e['proposal']['proposal_id']: e['human'] for e in map(json.loads, events.splitlines())}
                assert recorded == {p['proposal_id']: p['human'] for p in document['proposals']}
                repeat = drive(review_base + ['apply'] + review_flags, 'review-repeat')
                assert json.loads(repeat.stdout)['decisions_to_record'] == 0 and ledger.read_bytes() == events
                active = {e['proposal']['proposal_id']: e['decision_id'] for e in map(json.loads, ledger.read_text().splitlines())}
                for proposal in document['proposals']:
                    if proposal['human']['decision'] == 'approve':
                        proposal['human'].update(decision='defer', reason='Reverse disposable verification decision.',
                                                 supersedes_decision_id=active[proposal['proposal_id']])
                review_file.write_text(json.dumps(document))
                before = database_digest(database)
                drive(review_base + ['apply', '--dry-run'] + review_flags, 'review-reversal-preview')
                assert database_digest(database) == before and ledger.read_bytes() == events
                drive(review_base + ['apply'] + review_flags, 'review-reverse')
                with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
                    for sql, canonical, old, expected in correction_queries.values():
                        assert db.execute(sql, (canonical,)).fetchone()[0] == old
                changed_data = Path(scratch) / 'changed-data'
                shutil.copytree(ROOT / 'data', changed_data)
                changed_file = changed_data / 'sources/workiz/lakewood_air/jobs.json'
                payload = json.loads(changed_file.read_text())
                target = next(job for job in payload['data'] if job['UUID'] == 'J8OMKP')
                target['verification_only_changed_evidence'] = True
                changed_file.write_text(json.dumps(payload))
                stale_flags = review_flags.copy()
                stale_flags[stale_flags.index('--data') + 1] = str(changed_data)
                before, events = database_digest(database), ledger.read_bytes()
                rejected = drive(review_base + ['validate'] + stale_flags, 'review-stale', expected=1)
                assert json.loads(rejected.stderr)['status'] == 'failed'
                assert database_digest(database) == before and ledger.read_bytes() == events
                results['decisions_tested'] = decisions
                results['checks'].append('Review exports preserve human edits; validate and previews preserve logical database and ledger; approvals change exact stored fields; repeat adds no events; supersession restores originals; stale evidence rejects safely.')
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

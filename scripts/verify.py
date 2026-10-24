from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from house_account.storage import connect_readonly

ROOT = Path(__file__).resolve().parents[1]


def run_import(database: Path) -> dict:
    command = [sys.executable, '-m', 'house_account.cli', 'ingest', '--data', str(ROOT / 'data'), '--database', str(database)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(f'CLI import failed: {result.stderr}')
    report = json.loads(result.stdout)
    assert report['status'] == 'success'
    return report


def verify(lane: int, directory: Path) -> dict:
    database = directory / 'snapshot.sqlite'
    report = run_import(database)
    checks = []
    with connect_readonly(database) as db:
        if lane == 1:
            assert set(report['sources']) == {'jobber', 'housecall_pro', 'workiz', 'spreadsheet', 'calendars', 'profiles', 'reference'}
            expected = {
                'jobber:provider': 15, 'jobber:customer': 2964, 'jobber:property': 2964,
                'jobber:job': 4267, 'jobber:visit': 7658,
                'housecall_pro:provider': 15, 'housecall_pro:customer': 3551,
                'housecall_pro:job': 4633, 'housecall_pro:estimate': 689,
                'workiz:provider': 11, 'workiz:job': 2657,
                'spreadsheet:job': 206, 'calendars:calendar_block': 91,
                'profiles:profile': 40, 'reference:street_segment': 354,
            }
            for group, raw_count in expected.items():
                assert report['by_source_kind'][group]['seen'] == raw_count, group

            for counts in report['sources'].values():
                assert counts['seen'] == sum(counts[k] for k in ('accepted', 'duplicate', 'unresolved', 'rejected'))
            assert db.execute("SELECT count(*) FROM input_files WHERE role='validated_empty_page'").fetchone()[0] == 6
            assert db.execute('SELECT count(*) FROM input_files').fetchone()[0] >= 174
            checks.append('Six sources and street reference accounted, including six valid empty pages; baseline has no implementation.')
        elif lane == 2:
            assert db.execute('SELECT count(*) FROM (SELECT job_id FROM visits GROUP BY job_id HAVING count(*)=2)').fetchone()[0] > 0
            assert report['by_source_kind']['jobber:visit']['seen'] == 7658
            assert report['by_source_kind']['jobber:job']['seen'] == 4267
            checks.append('Jobber 4,267 jobs and 7,658 visits retained with relational parents.')
        elif lane == 3:
            assert db.execute('SELECT count(*) FROM estimates').fetchone()[0] == 689
            assert db.execute("SELECT count(*) FROM visits WHERE appointment_kind='estimate' AND status='scheduled'").fetchone()[0] == 131
            assert db.execute('SELECT count(*) FROM jobs JOIN estimates USING(id)').fetchone()[0] == 0
            checks.append('689 estimates separate from jobs; 131 scheduled estimate visits retained.')
        elif lane == 4:
            assert report['by_source_kind']['housecall_pro:job']['duplicate'] == 3
            assert db.execute("SELECT count(*) FROM source_records WHERE source='housecall_pro' AND kind='job'").fetchone()[0] == 4630
            checks.append('4,633 job occurrences resolve to 4,630 source jobs without lost duplicate evidence.')
        elif lane == 5:
            assert report['by_source_kind']['spreadsheet:job']['seen'] == 206
            assert report['by_source_kind']['spreadsheet:job']['duplicate'] == 8
            assert report['issues']['date_requires_review'] > 0
            assert report['issues']['duration_unknown'] == 198
            checks.append('206 physical rows accounted; ambiguous dates and durations remain explicit.')
        elif lane == 6:
            rows = db.execute("SELECT source_status FROM jobs WHERE status='cancelled'").fetchall()
            assert rows and all(row[0] for row in rows)
            checks.append('Cancelled work retains raw status and canonical cancellation.')
        elif lane == 7:
            rows = db.execute("SELECT j.amount_minor,r.raw_json FROM jobs j JOIN source_records r USING(id) WHERE r.source='housecall_pro'").fetchall()
            assert rows and all(amount == json.loads(raw)['total_amount'] for amount, raw in rows)
            checks.append('Every HCP job amount equals its integer-cent source value.')
        elif lane == 8:
            before = db.execute('SELECT id,content_hash FROM source_records ORDER BY id').fetchall()
            next_report = run_import(database)
            assert next_report['entities'] == report['entities']
            assert next_report['sources'] == report['sources']
            with connect_readonly(database) as fresh:
                assert fresh.execute('SELECT id,content_hash FROM source_records ORDER BY id').fetchall() == before
            checks.append('Full repeat import preserves entity counts, source IDs, content hashes, and occurrence accounting.')
        elif lane == 9:
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            script = 'from pathlib import Path; from house_account.cli import ingest; ingest(Path("data"), Path(__import__("sys").argv[1]), fail_after=23000)'
            result = subprocess.run([sys.executable, '-c', script, str(database)], cwd=ROOT, capture_output=True, text=True, check=False)
            assert result.returncode != 0 and 'injected import failure' in result.stderr
            assert hashlib.sha256(database.read_bytes()).hexdigest() == before
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            checks.append('Injected failure after 23,000 observations preserves previous database byte-for-byte.')
        elif lane == 10:
            row = db.execute("SELECT r.source_key,r.ingested_at,e.rule,e.confidence FROM source_records r JOIN entity_evidence e ON e.record_id=r.id JOIN occurrences o ON o.record_id=r.id WHERE o.disposition='duplicate' LIMIT 1").fetchone()
            assert row and all(row)
            checks.append('Exact duplicate evidence includes source key, ingestion timestamp, normalization rule, and confidence; cross-source merges deferred to P2.')
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    return {'stage': 'P1', 'lane': lane, 'status': 'pass', 'checks': checks,
            'fixture_manifest_hash': report['manifest_hash'], 'entities': report['entities'],
            'source_records': report['source_records'], 'occurrences': report['occurrences'],
            'baseline': 'unavailable: pre-implementation repository has no importer',
            'isolation': 'fresh temporary database and subprocess; shared uncommitted source checkout'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['P1'], default='P1')
    parser.add_argument('--lane', type=int, choices=range(1, 11))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='house-account-verification-') as temporary:
        lanes = [args.lane] if args.lane else range(1, 11)
        results = [verify(lane, Path(temporary)) for lane in lanes]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results[0] if args.lane else results, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'lanes': [item['lane'] for item in results]}))


if __name__ == '__main__':
    main()

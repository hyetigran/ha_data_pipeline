#!/usr/bin/env python3
"""Retain historical P3 receipts and verify P4's additive schedule fields."""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_p3 import assert_private, logical, manifest, overlap, spans


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.database, args.data, args.parent, args.output = (
        path.resolve() for path in (args.database, args.data, args.parent, args.output))
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {'status': 'fail', 'legacy_summary': 'legacy/live-summary.json'}
    receipts = []
    scratch = None
    before_data, before_database = manifest(args.data), logical(args.database)
    try:
        legacy_output = args.output / 'legacy'
        command = [sys.executable, str(ROOT / 'scripts/verify_p3.py'),
                   '--database', str(args.database), '--data', str(args.data),
                   '--parent', str(args.parent), '--output', str(legacy_output)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        (args.output / 'legacy.stdout').write_text(result.stdout)
        (args.output / 'legacy.stderr').write_text(result.stderr)
        summary['legacy_command'] = command
        summary['legacy_exit_code'] = result.returncode
        legacy = json.loads((legacy_output / 'live-summary.json').read_text())
        summary['legacy_status'] = legacy['status']
        lanes = legacy['lanes']
        assert len(lanes) == 10 and [lane['lane'] for lane in lanes] == list(range(1, 11))
        assert all(lane['status'] == 'pass' for lane in lanes[1:]), 'P3 lanes 2-10 failed'
        assert legacy['scratch_removed'] and legacy['database_logically_unchanged']
        assert legacy['source_files_unchanged'] == len(before_data)
        if lanes[0]['status'] == 'fail':
            assert result.returncode == 1 and legacy['status'] == 'fail'
            assert lanes[0]['error'] == "AssertionError('schedule regression or vacuous fixture')"
        else:
            assert lanes[0]['status'] == 'pass' and result.returncode == 0 and legacy['status'] == 'pass'
        with tempfile.TemporaryDirectory(prefix='availability-maintained-') as temporary:
            scratch = Path(temporary)
            database = scratch / 'snapshot.sqlite'
            with (closing(sqlite3.connect(args.database.as_uri() + '?mode=ro', uri=True)) as source,
                  closing(sqlite3.connect(database)) as target):
                source.backup(target)
            before_copy = logical(database)

            def cli(kind, value, *, parent=False, **flags):
                command = [sys.executable, '-m', 'house_account.cli', 'query', kind, value,
                           '--database', str(database)]
                for key, flag_value in flags.items():
                    command.extend(['--' + key.replace('_', '-'), str(flag_value)])
                source = args.parent / 'src' if parent else ROOT / 'src'
                env = {**os.environ, 'PYTHONPATH': str(source), 'TMPDIR': str(scratch)}
                process = subprocess.run(command, capture_output=True, text=True, cwd=scratch,
                                         env=env, check=False)
                receipt = {'command': command, 'parent': parent, 'exit_code': process.returncode,
                           'stdout': process.stdout, 'stderr': process.stderr}
                receipts.append(receipt)
                assert process.returncode == 0, receipt
                response = json.loads(process.stdout)
                assert 'PRIVATE_SENTINEL' not in process.stdout
                assert_private(response)
                return response['results']

            old = cli('block', '4501 Gaston Ave, Dallas, TX 75246', parent=True)
            new = cli('block', '4501 Gaston Ave, Dallas, TX 75246')
            assert old and len(new) == len(old), 'changed or vacuous schedule rows'
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
                connection.row_factory = sqlite3.Row
                for original, current in zip(old, new, strict=True):
                    assert set(current) == set(original) | {'business_name', 'services'}
                    assert {key: current[key] for key in original} == original, 'changed baseline schedule facts or order'
                    provider = connection.execute('SELECT display_name FROM canonical_providers WHERE id=?',
                                                  (current['provider_id'],)).fetchone()
                    assert provider and current['business_name'] == provider[0]
                    kind = 'job' if current['job_id'] else 'estimate'
                    services = connection.execute(
                        f'SELECT trade_code,service_code FROM {kind}_services WHERE {kind}_id=? ORDER BY id',
                        (current[kind + '_id'],)).fetchall()
                    assert current['services'] == [dict(row) for row in services]
                openings = cli('openings', 'Lone Star Plumbing Co.', limit=100)
                assert openings['openings']
                occupied = connection.execute(
                    "SELECT v.scheduled_start_utc,v.scheduled_end_utc FROM canonical_visits v "
                    "JOIN canonical_jobs j ON j.id=v.job_id WHERE j.provider_id=? "
                    "AND v.scheduling_state NOT IN ('completed','cancelled','superseded') "
                    "AND v.scheduled_start_utc IS NOT NULL AND v.scheduled_end_utc IS NOT NULL",
                    (openings['provider_id'],)).fetchall()
                assert occupied, 'no active visits to check'
                assert all(not overlap(opening, busy) for opening in spans(openings) for busy in occupied)
            assert logical(database) == before_copy
            maintained = {'lane': 1, 'status': 'pass', 'checks': {
                'same_scheduled_visits': len(new), 'original_keys_values_and_order_preserved': True,
                'only_business_name_and_services_added': True, 'additions_match_database': True,
                'openings_avoid_active_visits': True}}
            (args.output / 'maintained-lane-1.json').write_text(json.dumps(maintained, indent=2) + '\n')
        assert manifest(args.data) == before_data and logical(args.database) == before_database
        summary.update(status='pass', lanes=[maintained, *lanes[1:]],
                       source_files_unchanged=len(before_data), database_logically_unchanged=True)
    except Exception as exc:
        summary['error'] = repr(exc)
        raise
    finally:
        summary['scratch_removed'] = scratch is None or not scratch.exists()
        (args.output / 'maintained-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
        (args.output / 'maintained-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary))


if __name__ == '__main__':
    main()

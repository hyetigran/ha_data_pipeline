"""Verify unit boundaries through real CLI queries on a sanitized snapshot."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from math import degrees
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from p2_fixture import build, fixture


def main() -> None:
    receipts = []
    with tempfile.TemporaryDirectory(prefix='p2-query-cli-') as directory:
        root = Path(directory)
        database = root / 'snapshot.sqlite'
        observations = fixture()
        segment = next(o for o in observations if o.kind == 'street_segment')
        segment.normalized.attributes.update(from_number=4500, to_number=4501,
                                            start_lat=0.0, start_lon=0.0,
                                            end_lat=degrees(0.5 / 3958.7613), end_lon=0.0)
        build(database, root/'ledger.jsonl', observations)

        def query(kind: str, value: str) -> dict:
            command = [sys.executable, '-m', 'house_account.cli', 'query', kind, value, '--database', str(database)]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            parsed = json.loads(result.stdout)
            receipts.append({'command': command, 'exit_code': result.returncode, 'response': parsed})
            return parsed['results']

        a = query('property', '4501 Example St Apt 4, Dallas, TX 75214')
        b = query('property', '4501 Example Street #4, Dallas, TX 75214')
        c = query('property', '4501 Example St Unit 5, Dallas, TX 75214')
        assert a == b and a['distinct_jobs'] == 2 and c['distinct_jobs'] == 1
        assert set(a['property_ids']).isdisjoint(c['property_ids'])
        assert sum(r['distinct_jobs'] for r in query('radius', '4500 Example St, Dallas, TX 75214')) == 3
        segment.normalized.attributes['end_lat'] = degrees(0.50001 / 3958.7613)
        build(database, root/'ledger.jsonl', observations)
        assert query('radius', '4500 Example St, Dallas, TX 75214') == []
    output = Path('artifacts/P2/query-cli.json')
    output.write_text(json.dumps({'status': 'pass', 'fixture': 'sanitized', 'unit_aliases_equal': True,
                                  'unit_histories_distinct': True, 'exact_half_mile_included': True,
                                  'outside_half_mile_excluded': True, 'receipts': receipts}, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'receipt': str(output)}))


if __name__ == '__main__':
    main()

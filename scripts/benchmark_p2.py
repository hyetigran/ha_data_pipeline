from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def worker(data: Path, database: Path) -> dict:
    from house_account.cli import ingest
    from house_account.storage import connect_readonly
    start = time.perf_counter()
    result = ingest(data, database, ledger=database.with_suffix('.jsonl'))
    elapsed = time.perf_counter() - start
    with connect_readonly(database) as db:
        assert db.execute('SELECT count(*) FROM source_records').fetchone()[0] == 46092
        assert db.execute('SELECT count(*) FROM canonical_jobs').fetchone()[0] > 0
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    return {'seconds': elapsed, 'peak_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024),
            'manifest_hash': result['manifest_hash'], 'canonical_counts': result['reconciliation'], 'errors': 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--database', type=Path)
    parser.add_argument('--output', type=Path, default=Path('artifacts/P2R/benchmark.json'))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.data, args.database)))
        return
    from house_account.queries import (
        block_schedule,
        history_radius,
        property_history,
        provider_summary,
    )
    from house_account.storage import connect_readonly
    results = []
    with tempfile.TemporaryDirectory(prefix='house-account-p2-perf-') as directory:
        database = Path(directory) / 'snapshot.sqlite'
        for iteration in range(6):
            start = time.perf_counter()
            proc = subprocess.run([sys.executable, __file__, '--worker', '--data', str(args.data.resolve()), '--database', str(database)], text=True, capture_output=True, check=True)
            run = json.loads(proc.stdout)
            run['process_seconds'] = time.perf_counter() - start
            if iteration:
                results.append(run)
        with connect_readonly(database) as db:
            provider_id = db.execute("SELECT id FROM canonical_providers WHERE display_name = 'Lone Star Plumbing Co.' LIMIT 1").fetchone()[0]
        queries = {
            'radius_history': lambda: history_radius(database, '4512 Live Oak St, Dallas, TX 75204'),
            'block_schedule': lambda: block_schedule(database, '4512 Live Oak St, Dallas, TX 75204'),
            'property_history': lambda: property_history(database, '5823 Belmont Ave, Dallas, TX 75206'),
            'provider_summary': lambda: provider_summary(database, provider_id),
        }
        measurements = {}
        for name, call in queries.items():
            assert call()['results']
            times = []
            for _ in range(30):
                start = time.perf_counter()
                answer = call()
                assert answer['results']
                json.dumps(answer)
                times.append((time.perf_counter() - start) * 1000)
            measurements[name] = {'samples': 30, 'median_ms': statistics.median(times), 'range_ms': [min(times), max(times)], 'p95_ms': sorted(times)[28], 'errors': 0}
    process = [r['process_seconds'] for r in results]
    report = {'stage': 'P2R', 'claim': 'Complete import and four public query functions fit the planned budgets on this machine.',
              'baseline': 'Frozen P2 implementation measured separately in artifacts/P2R/baseline/benchmark.json; changed completion semantics prevent an identical-work speedup claim.',
              'platform': platform.platform(), 'python': platform.python_version(), 'cpus': os.cpu_count(), 'load_average': os.getloadavg(),
              'conditions': 'One warmup then five fresh-process imports. Thirty warm requests per query, each opens a read-only connection and serializes the full result.',
              'imports': results, 'median_seconds': statistics.median(process), 'range_seconds': [min(process), max(process)],
              'peak_mib': max(r['peak_mib'] for r in results), 'queries': measurements,
              'status': 'pass' if max(process) <= 60 and max(r['peak_mib'] for r in results) <= 512 and all(q['p95_ms'] <= 500 for q in measurements.values()) else 'fail'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'imports'}))
    if report['status'] != 'pass':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

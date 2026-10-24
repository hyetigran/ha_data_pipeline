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


def worker(data: Path, database: Path) -> None:
    from house_account.cli import ingest
    from house_account.storage import connect_readonly
    start = time.perf_counter()
    report = ingest(data, database)
    seconds = time.perf_counter() - start
    with connect_readonly(database) as connection:
        assert connection.execute('SELECT count(*) FROM source_records').fetchone()[0] == 46092
        assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'seconds': seconds, 'peak_rss_mib': rss / (1024**2 if sys.platform == 'darwin' else 1024),
                      'records': report['source_records'], 'manifest_hash': report['manifest_hash'], 'errors': 0}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['P1'], default='P1')
    parser.add_argument('--output', type=Path, default=Path('artifacts/P1/benchmark.json'))
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--database', type=Path)
    parser.add_argument('--data', type=Path, default=Path('data'))
    args = parser.parse_args()
    if args.worker:
        worker(args.data, args.database)
        return
    results = []
    with tempfile.TemporaryDirectory(prefix='house-account-benchmark-') as directory:
        for iteration in range(6):
            command = [sys.executable, __file__, '--worker', '--data', str(args.data), '--database', str(Path(directory) / f'{iteration}.sqlite')]
            start = time.perf_counter()
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            measurement = json.loads(result.stdout)
            measurement['process_wall_seconds'] = time.perf_counter() - start
            if iteration:
                results.append(measurement)
    times = [r['process_wall_seconds'] for r in results]
    report = {'claim': 'Full-pack import fits the P1 60-second and 512-MiB target budgets on this machine.',
              'stage': 'P1', 'runs': results, 'warmup_runs': 1, 'median_seconds': statistics.median(times),
              'range_seconds': [min(times), max(times)], 'p95_seconds_nearest_rank': max(times),
              'peak_rss_mib': max(r['peak_rss_mib'] for r in results), 'platform': platform.platform(),
              'python': platform.python_version(), 'cpu_count': os.cpu_count(), 'load_average': os.getloadavg(),
              'baseline': 'unavailable: parent has no import operation; no speedup claimed',
              'conditions': 'Fresh subprocess and database each run. OS filesystem cache warmed. End-to-end process wall includes startup and validation.',
              'status': 'pass' if max(times) <= 60 and max(r['peak_rss_mib'] for r in results) <= 512 else 'fail'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'runs'}))
    if report['status'] != 'pass':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

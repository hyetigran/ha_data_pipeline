from __future__ import annotations

import argparse
import cProfile
import hashlib
import json
import math
import os
import platform
import pstats
import resource
import statistics
import sys
import time
from pathlib import Path

from house_account.storage import connect_readonly


def main() -> None:
    parser = argparse.ArgumentParser(description='Measure complete P3 queries on a supplied disposable snapshot.')
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('artifacts/P3/benchmark.json'))
    parser.add_argument('--samples', type=int, default=30)
    args = parser.parse_args()
    if args.samples < 30:
        parser.error('at least 30 samples are required')
    from house_account.availability import available_providers, next_openings
    from house_account.ranking import recommend_providers

    with connect_readonly(args.database) as connection:
        providers = [r[0] for r in connection.execute('SELECT id FROM canonical_providers ORDER BY id')]
        manifest = connection.execute('SELECT manifest_hash FROM snapshot').fetchone()[0]
        snapshot = connection.execute('SELECT id FROM snapshot').fetchone()[0]
        profiles = connection.execute('SELECT count(*) FROM profiles').fetchone()[0]
    start, end = '2026-11-02T06:00:00+00:00', '2026-12-02T06:00:00+00:00'
    source_paths = sorted((Path(__file__).resolve().parents[1] / 'src/house_account').rglob('*.py'))
    source_hashes = {str(p.relative_to(Path(__file__).resolve().parents[1])): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    calls = {f'openings:{pid}': lambda pid=pid: next_openings(args.database, pid, start=start, end=end) for pid in providers}
    calls['available_handymen'] = lambda: available_providers(args.database, '75214', start=start, end=end)
    calls['water_heater_ranking'] = lambda: recommend_providers(args.database, '75206', start=start, end=end)
    samples: dict[str, list[float]] = {key: [] for key in calls}
    response_hashes: dict[str, str] = {}
    counts: dict[str, int] = {}

    def run(name: str) -> None:
        begun = time.perf_counter()
        result = calls[name]()
        encoded = json.dumps(result, sort_keys=True).encode()
        elapsed = time.perf_counter() - begun
        assert result['snapshot_id'] == snapshot
        assert 'results' in result
        digest = hashlib.sha256(encoded).hexdigest()
        if name in response_hashes:
            assert response_hashes[name] == digest, f'nondeterministic response: {name}'
        response_hashes[name] = digest
        counts[name] = len(encoded)
        samples[name].append(elapsed * 1000)

    for name in calls:
        run(name)
        samples[name].clear()
    for iteration in range(args.samples):
        for name in (list(calls) if iteration % 2 == 0 else list(reversed(calls))):
            run(name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    profiler = cProfile.Profile()
    profiler.runcall(calls['water_heater_ranking'])
    with args.output.with_suffix('.profile.txt').open('w') as handle:
        pstats.Stats(profiler, stream=handle).strip_dirs().sort_stats('cumulative').print_stats(25)
    measurements = {name: {'samples': len(values), 'median_ms': statistics.median(values), 'range_ms': [min(values), max(values)], 'p95_ms': sorted(values)[math.ceil(.95 * len(values)) - 1], 'response_bytes': counts[name], 'response_sha256': response_hashes[name], 'errors': 0} for name, values in samples.items()}
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024)
    report = {'stage': 'P3', 'claim': 'Warm complete P3 queries fit the one-second p95 and 512 MiB process budgets on this pack.', 'baseline': 'Unavailable: parent c6c151e has no availability or ranking operation. No speedup ratio claimed.', 'manifest_hash': manifest, 'snapshot_id': snapshot, 'canonical_providers': len(providers), 'profiles': profiles, 'window': {'start': start, 'end': end}, 'platform': platform.platform(), 'python': platform.python_version(), 'cpus': os.cpu_count(), 'load_average': os.getloadavg(), 'method': 'One warmup per operation; 30 or more interleaved rounds across every canonical provider plus availability search and ranking. Each timed request opens its read transaction and fully serializes the response. Profiling is separate and excluded. Deterministic response hashes are checked.', 'peak_mib': peak, 'measurements': measurements, 'status': 'pass' if peak <= 512 and all(m['p95_ms'] <= 1000 for m in measurements.values()) else 'fail'}
    assert source_hashes == {str(p.relative_to(Path(__file__).resolve().parents[1])): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}, 'source changed during benchmark'
    report['source_hashes'] = source_hashes
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'measurements'}, sort_keys=True))
    if report['status'] != 'pass':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

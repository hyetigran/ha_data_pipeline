"""Exercise the local MCP protocol against an isolated supplied-pack snapshot."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import platform
import resource
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
CALLS = [
    ('search_service_history', {'address': '4512 Live Oak St, Dallas, TX 75204', 'limit': 100}),
    ('find_available_providers', {'trade': 'handyman', 'history_postal_code': '75214'}),
    ('get_block_schedule', {'street': 'Live Oak St', 'city': 'Dallas', 'state': 'TX', 'hundred_block': 4500}),
    ('get_provider_profile', {'provider': 'Lone Star Plumbing', 'history_limit': 100}),
    ('get_property_history', {'address': '5823 Belmont Ave, Dallas, TX 75206'}),
    ('recommend_provider', {'trade': 'plumbing', 'service_type': 'water_heater', 'postal_code': '75206'}),
]


def manifest(data: Path) -> dict[str, str]:
    return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob('*')) if p.is_file()}


def logical(database: Path) -> str:
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.execute('BEGIN')
        return hashlib.sha256('\n'.join(connection.iterdump()).encode()).hexdigest()


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def public_check(value: object) -> None:
    forbidden = {'email', 'phone', 'customer_name', 'customer_email', 'customer_phone', 'raw_json',
                 'raw_notes', 'notes', 'ical', 'file_path', 'source_path', 'calendar_title'}
    if isinstance(value, dict):
        assert not forbidden.intersection(value)
        for child in value.values():
            public_check(child)
    elif isinstance(value, list):
        for child in value:
            public_check(child)
    elif isinstance(value, str):
        assert 'sources/' not in value and '/Users/' not in value and 'PRIVATE_SENTINEL' not in value


async def run(args: argparse.Namespace, scratch: Path, evidence: Path, summary: dict) -> None:
    database = scratch / 'snapshot.sqlite'
    if args.database:
        with closing(sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(database)) as target:
            source.backup(target)
        database.chmod(0o600)
    params = StdioServerParameters(command=sys.executable, args=['-m', 'house_account.cli', '--data', str(args.data.resolve()),
                                  '--database', str(database), '--ledger', str(scratch / 'decisions.jsonl'), '--as-of', '2026-11-02'],
                                  cwd=scratch, env={'PYTHONPATH': str(ROOT / 'src'), 'TMPDIR': str(scratch)})
    if args.fresh_checkout:
        archive = scratch / 'checkout.tar'
        await asyncio.to_thread(subprocess.run, ['git', '-C', str(ROOT), 'archive', '--output', str(archive), 'HEAD'], check=True, timeout=30)
        checkout = scratch / 'checkout'
        checkout.mkdir()
        with tarfile.open(archive) as source:
            source.extractall(checkout, filter='data')
        shutil.copytree(args.data, checkout / 'data')
        params.command = shutil.which('uv') or 'uv'
        params.args = ['--directory', str(checkout), 'run', '--locked', 'house-account', '--data', 'data',
                       '--database', str(database), '--ledger', str(scratch / 'decisions.jsonl'), '--as-of', '2026-11-02']
        params.cwd = checkout
        params.env = {'PYTHONPATH': str(checkout / 'src'), 'UV_CACHE_DIR': '/tmp/house-account-uv-cache', 'TMPDIR': str(scratch)}
        summary['fresh_checkout_commit'] = (await asyncio.to_thread(subprocess.check_output, ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True)).strip()
        summary['fresh_checkout_source_sha256'] = {str(path.relative_to(checkout)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((checkout / 'src/house_account').rglob('*.py'))}
    if args.profile:
        params.args = ['-m', 'cProfile', '-o', str((evidence / 'server.pstats').resolve()), *params.args]
    started = time.perf_counter()
    with (evidence / 'server.stderr').open('w') as stderr:
        async with stdio_client(params, errlog=stderr) as streams, ClientSession(*streams, read_timeout_seconds=timedelta(seconds=120)) as client:
            initialized = await client.initialize()
            summary['startup_seconds'] = time.perf_counter() - started
            (evidence / 'initialize.json').write_text(initialized.model_dump_json(indent=2))
            tools = await client.list_tools()
            (evidence / 'tools.json').write_text(tools.model_dump_json(indent=2))
            assert {tool.name for tool in tools.tools} == {name for name, _ in CALLS}
            assert all(tool.outputSchema and tool.annotations and tool.annotations.readOnlyHint for tool in tools.tools)
            before = logical(database)
            answers = {}
            for name, arguments in CALLS:
                result = await client.call_tool(name, arguments)
                (evidence / (name + '.json')).write_text(result.model_dump_json(indent=2))
                assert not result.isError, name
                answer = result.structuredContent
                assert answer and answer.get('snapshot_id') and answer.get('limitations')
                public_check(answer)
                answers[name] = answer
            assert len({answer['snapshot_id'] for answer in answers.values()}) == 1
            from house_account import queries
            from house_account.availability import available_providers, next_openings
            from house_account.ranking import recommend_providers
            groups = answers['search_service_history']['results']['groups']
            assert not groups['truncated']
            assert sum(group['distinct_jobs'] for group in groups['items']) == 969
            assert {(g['provider_id'], g['trade'], g['distinct_jobs']) for g in groups['items']} == {
                (g['provider_id'], g['trade'], g['distinct_jobs']) for g in queries.history_radius(database, CALLS[0][1]['address'])['results']}
            available = answers['find_available_providers']['results']['providers']
            assert available['total'] == 3
            assert {p['business_name'] for p in available['items']} == {'White Rock Handyman', 'Peak Home Services', 'M Streets Handyman'}
            assert {p['provider_id'] for p in available['items']} == {p['provider_id'] for p in available_providers(database, '75214')['results']['providers']}
            visits = answers['get_block_schedule']['results']['visits']
            assert visits['total'] == 4 and all(visit['business_name'] for visit in visits['items'])
            assert {v['visit_id'] for v in visits['items']} == {v['visit_id'] for v in queries.block_schedule(database, CALLS[0][1]['address'])['results']}
            profile = answers['get_provider_profile']['results']
            assert profile['completed_distinct_jobs'] == 262
            openings = profile['availability']['openings']['items']
            assert [o['start_utc'] for o in openings] == ['2026-11-17T16:30:00+00:00', '2026-11-18T16:30:00+00:00', '2026-11-20T16:00:00+00:00']
            assert [(o['start_utc'], o['end_utc']) for o in openings] == [(o['start_utc'], o['end_utc']) for o in next_openings(database, 'Lone Star Plumbing Co.')['results']['openings']]
            home = answers['get_property_history']['results']
            assert home['distinct_jobs'] == 4 and all(job['business_name'] and job['services']['items'] for job in home['jobs']['items'])
            assert {j['job_id'] for j in home['jobs']['items']} == {j['id'] for j in queries.property_history(database, CALLS[4][1]['address'])['results']['jobs']}
            assert answers['recommend_provider']['results']['providers']['total'] == 0
            assert recommend_providers(database, '75206')['results']['total'] == 0
            explicit = await client.call_tool('recommend_provider', {**CALLS[5][1], 'duration_minutes': 120})
            assert not explicit.isError and explicit.structuredContent['results']['providers']['total'] == 2
            (evidence / 'recommend-explicit-duration.json').write_text(explicit.model_dump_json(indent=2))
            summary['direct_query_parity'] = 'Six real-pack answers match direct queries and independent fixed expectations.'
            summary['tools_called'] = list(answers)
            summary['answer_sha256'] = {name: digest(answer) for name, answer in answers.items()}
            invalid = [
                ('get_property_history', {'address': 'PRIVATE_SENTINEL', 'limit': 10000}),
                ('find_available_providers', {'trade': 'handyman', 'history_postal_code': '75214', 'start': 'PRIVATE_SENTINEL'}),
                ('get_provider_profile', {'provider': 'PRIVATE_SENTINEL', 'opening_count': -1}),
                ('recommend_provider', {'trade': 'electrical', 'service_type': 'water_heater', 'postal_code': '75206'}),
                ('get_property_history', {'address': '5823 Belmont Ave, Dallas, TX 75206', 'sql': 'PRIVATE_SENTINEL'}),
            ]
            for number, (name, arguments) in enumerate(invalid):
                result = await client.call_tool(name, arguments)
                (evidence / f'error-{number}.json').write_text(result.model_dump_json(indent=2))
                assert result.isError, (name, arguments)
                assert 'PRIVATE_SENTINEL' not in result.model_dump_json()
                public_check(result.model_dump(mode='json'))
            summary['invalid_requests_rejected'] = len(invalid)
            if args.rounds:
                samples: dict[str, list[float]] = {name: [] for name, _ in CALLS}
                for _ in range(args.rounds):
                    for name, arguments in CALLS:
                        tick = time.perf_counter()
                        result = await client.call_tool(name, arguments)
                        elapsed = time.perf_counter() - tick
                        assert not result.isError and digest(result.structuredContent) == summary['answer_sha256'][name]
                        samples[name].append(elapsed * 1000)
                summary['benchmark'] = {name: {'calls': len(values), 'median_ms': statistics.median(values),
                    'p95_ms': sorted(values)[math.ceil(.95 * len(values)) - 1], 'min_ms': min(values), 'max_ms': max(values),
                    'samples_ms': values} for name, values in samples.items()}
                summary['benchmark_errors'] = 0
            assert logical(database) == before
            summary['database_logically_unchanged'] = True
    assert 'PRIVATE_SENTINEL' not in (evidence / 'server.stderr').read_text()
    summary['clean_shutdown'] = True
    summary['peak_child_memory_mib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / (1024 ** 2 if sys.platform == 'darwin' else 1024)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    parser.add_argument('--database', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=0)
    parser.add_argument('--fresh-checkout', action='store_true', help='Archive HEAD and start through locked uv in a fresh checkout')
    parser.add_argument('--profile', action='store_true', help='Separate diagnostic run; do not report its timings')
    args = parser.parse_args()
    if not 0 <= args.rounds <= 100:
        parser.error('rounds must be 0 through 100')
    if args.fresh_checkout and (args.database or args.profile):
        parser.error('fresh checkout must create its own database without profiling')
    args.output.mkdir(parents=True, exist_ok=False)
    args.output.chmod(0o700)
    before = manifest(args.data)
    summary = {'status': 'running', 'platform': platform.platform(), 'python': sys.version,
               'source_count': len(before), 'source_manifest_sha256': digest(before), 'rounds': args.rounds,
               'baseline': 'P3 has no MCP transport; no parent MCP speed ratio is meaningful.'}
    try:
        with tempfile.TemporaryDirectory(prefix='house-account-p4-') as directory:
            scratch = Path(directory)
            summary['scratch'] = directory
            asyncio.run(run(args, scratch, args.output, summary))
        assert manifest(args.data) == before
        summary['source_files_unchanged'] = True
        summary['status'] = 'pass'
    finally:
        summary['scratch_removed'] = 'scratch' not in summary or not Path(summary['scratch']).exists()
        if summary['status'] == 'running':
            summary['status'] = 'failed'
        (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps({'evidence': str(args.output.resolve()), 'status': summary['status'], 'scratch_removed': summary['scratch_removed']}))


if __name__ == '__main__':
    main()

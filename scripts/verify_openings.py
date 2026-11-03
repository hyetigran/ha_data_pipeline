"""Bounded exhaustive check that candidate openings never cover busy or unknown time.

Runs the real `union`, `subtract`, and `openings` on every input up to a bound on a
one-minute grid, and compares each answer with a cell-by-cell reference.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from itertools import combinations, product
from unittest import mock

from house_account import availability
from house_account.availability import ScheduleEvidence, openings
from house_account.time_policy import Interval, subtract, union

BASE = datetime(2026, 11, 10, tzinfo=UTC)
PID = 'provider-under-check'


def at(minute: int) -> datetime:
    return BASE + timedelta(minutes=minute)


def minute(stamp: datetime) -> int:
    return int((stamp.astimezone(UTC) - BASE).total_seconds() // 60)


def grid(lo: int, hi: int) -> list[Interval]:
    return [Interval(at(a), at(b)) for a, b in combinations(range(lo, hi + 1), 2)]


def lists(items: list[Interval], size: int) -> list[tuple[Interval, ...]]:
    return [combo for n in range(size + 1) for combo in product(items, repeat=n)]


def cells(intervals) -> set[int]:
    return {m for i in intervals for m in range(minute(i.start), minute(i.end))}


def segments(free: set[int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for m in sorted(free):
        if result and result[-1][1] == m:
            result[-1] = (result[-1][0], m + 1)
        else:
            result.append((m, m + 1))
    return result


def show(intervals) -> str:
    return '[' + ', '.join(f'[{minute(i.start)},{minute(i.end)})' for i in intervals) + ']'


def check_union(span: int, size: int) -> tuple[int, str | None]:
    count = 0
    for items in lists(grid(0, span), size + 1):
        count += 1
        got = union(list(items))
        if [(minute(i.start), minute(i.end)) for i in got] != segments(cells(items)):
            return count, f'union({show(items)}) returned {show(got)}; expected the maximal segments {segments(cells(items))}'
    return count, None


def check_subtract(span: int, size: int) -> tuple[int, str | None]:
    count = 0
    intervals = grid(0, span)
    for working, occupied in product(lists(intervals, size), lists(intervals, size + 1)):
        count += 1
        got = subtract(list(working), list(occupied))
        expected = segments(cells(working) - cells(occupied))
        if [(minute(i.start), minute(i.end)) for i in got] != expected:
            return count, (f'subtract(working={show(working)}, occupied={show(occupied)}) returned {show(got)}; '
                           f'expected the free segments {expected}')
    return count, None


def check_openings(span: int, size: int) -> tuple[int, str | None]:
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE canonical_providers (id TEXT, display_name TEXT)')
    connection.execute('INSERT INTO canonical_providers VALUES (?, ?)', (PID, 'Provider'))
    window = Interval(at(1), at(span - 1))
    inside = grid(1, span - 1)
    anywhere = grid(0, span)
    count = 0
    with mock.patch.object(availability, 'load_evidence') as loader:
        for working, busy, unknown in product(lists(inside, size), lists(anywhere, size), lists(anywhere, 1)):
            loader.return_value = ScheduleEvidence(working=list(working), busy=list(busy), unknown=list(unknown))
            for duration, limit in product(range(1, span - 1), (1, 3)):
                count += 1
                result = openings(connection, PID, window, duration, limit)
                case = (f'window={show([window])} working={show(working)} busy={show(busy)} unknown={show(unknown)} '
                        f'duration={duration} limit={limit}')
                relevant = cells(i for i in unknown if i.overlaps(window))
                covered = cells([window]) <= relevant
                status = 'unknown' if covered else 'partial' if relevant else 'known'
                if result['status'] != status:
                    return count, f'{case}: status {result["status"]!r}, expected {status!r}'
                if status == 'unknown':
                    if result['openings'] is not None:
                        return count, f'{case}: openings offered while the whole window is unknown'
                    continue
                offered = [(minute(datetime.fromisoformat(o['start_utc'])), minute(datetime.fromisoformat(o['end_utc'])))
                           for o in result['openings']]
                blocked = cells(busy) | cells(unknown)
                for start, end in offered:
                    bad = set(range(start, end)) - (cells(working) - blocked)
                    if bad:
                        return count, f'{case}: opening [{start},{end}) covers minutes {sorted(bad)} that are busy, unknown, or outside working hours'
                    if end - start < duration:
                        return count, f'{case}: opening [{start},{end}) is shorter than {duration} minutes'
                expected = [s for s in segments(cells(working) - blocked) if s[1] - s[0] >= duration]
                if offered != expected[:limit] or result['total_openings'] != len(expected):
                    return count, (f'{case}: offered {offered} of {result["total_openings"]}; '
                                   f'expected {expected[:limit]} of {len(expected)}')
    return count, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--span', type=int, default=5, help='grid length in minutes (default 5)')
    parser.add_argument('--size', type=int, default=2, help='intervals per input list; union and occupied lists get one more (default 2)')
    arguments = parser.parse_args()
    failed = False
    span, size = arguments.span, arguments.size
    bounds = {'union': f'up to {size + 1} intervals',
              'subtract': f'up to {size} working and {size + 1} occupied intervals',
              'openings': f'up to {size} working, {size} busy, and 1 unknown interval'}
    for name, check in (('union', check_union), ('subtract', check_subtract), ('openings', check_openings)):
        count, failure = check(span, size)
        if failure:
            failed = True
            print(f'FAIL {name} after {count} cases: {failure}')
        else:
            print(f'PASS {name}: {count} cases on a {span}-minute grid, {bounds[name]}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

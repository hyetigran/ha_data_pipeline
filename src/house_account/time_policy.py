from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/Chicago')
REFERENCE = '2026-11-02T00:00:00-06:00'
THREE_DAYS = '2026-11-05T00:00:00-06:00'
WEEK_END = '2026-11-09T00:00:00-06:00'
DEFAULT_END = '2026-12-03T00:00:00-06:00'


@dataclass(frozen=True, order=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None or self.start.astimezone(UTC) >= self.end.astimezone(UTC):
            raise ValueError('interval requires increasing aware endpoints')
        object.__setattr__(self, 'start', self.start.astimezone(UTC))
        object.__setattr__(self, 'end', self.end.astimezone(UTC))

    def overlaps(self, other: Interval) -> bool:
        return self.start < other.end and other.start < self.end

    def clip(self, other: Interval) -> Interval | None:
        return Interval(max(self.start, other.start), min(self.end, other.end)) if self.overlaps(other) else None

    def public(self) -> dict:
        return {'start_utc': self.start.isoformat(), 'end_utc': self.end.isoformat(), 'start_local': self.start.astimezone(ZONE).isoformat(), 'end_local': self.end.astimezone(ZONE).isoformat(),
                'duration_minutes': (self.end-self.start).total_seconds()/60}


def local_instant(value: datetime, zone: ZoneInfo = ZONE) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC)
    candidates = {value.replace(tzinfo=zone, fold=fold).astimezone(UTC) for fold in (0, 1)
                  if value.replace(tzinfo=zone, fold=fold).astimezone(UTC).astimezone(zone).replace(tzinfo=None) == value}
    if len(candidates) != 1:
        raise ValueError('ambiguous or nonexistent local time')
    return candidates.pop()


def day_interval(day: date, zone: ZoneInfo = ZONE) -> Interval:
    return Interval(local_instant(datetime.combine(day, time()), zone),
                    local_instant(datetime.combine(day+timedelta(days=1), time()), zone))


def request_window(start: str, end: str, duration_minutes: int) -> Interval:
    if isinstance(duration_minutes, bool) or not isinstance(duration_minutes, int) or not 1 <= duration_minutes <= 1440:
        raise ValueError('duration must be 1 through 1440 whole minutes')
    window = Interval(datetime.fromisoformat(start), datetime.fromisoformat(end))
    if window.end-window.start > timedelta(days=31):
        raise ValueError('availability horizon must not exceed 31 days')
    return window


def union(intervals: list[Interval]) -> list[Interval]:
    result: list[Interval] = []
    for item in sorted(intervals):
        if result and item.start <= result[-1].end:
            result[-1] = Interval(result[-1].start, max(item.end, result[-1].end))
        else:
            result.append(item)
    return result


def subtract(working: list[Interval], occupied: list[Interval]) -> list[Interval]:
    result = []
    for work in union(working):
        cursor = work.start
        for busy in union(occupied):
            if busy.end <= cursor or busy.start >= work.end:
                continue
            if cursor < busy.start:
                result.append(Interval(cursor, busy.start))
            cursor = max(cursor, busy.end)
            if cursor >= work.end:
                break
        if cursor < work.end:
            result.append(Interval(cursor, work.end))
    return result

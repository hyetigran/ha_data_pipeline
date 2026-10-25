"""Pack-derived DST regression; boundary probes below are explicitly synthetic."""

import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from house_account.adapters.crm import _housecall_pro
from house_account.model import instant


def test_seeded_november_first_dst_job_is_preserved_without_guessing() -> None:
    path = Path("data/sources/housecall_pro/dallas_drain_pros/jobs_page_2.json")
    raw = json.loads(path.read_text())["jobs"][42]
    assert raw["id"] == "job_ff1d934b288cafe44328e65ac5b42d15"
    assert raw["schedule"]["scheduled_start"] == "2026-11-01T01:30:00"
    local = datetime.fromisoformat(raw["schedule"]["scheduled_start"])
    possibilities = [
        local.replace(tzinfo=ZoneInfo("America/Chicago"), fold=f)
        .astimezone(UTC)
        .isoformat()
        for f in (0, 1)
    ]
    assert possibilities == ["2026-11-01T06:30:00+00:00", "2026-11-01T07:30:00+00:00"]
    with pytest.raises(ValueError, match="ambiguous"):
        instant(raw["schedule"]["scheduled_start"])
    rows = list(_housecall_pro(Path("data")))
    visit = next(o for o in rows if o.kind == "visit" and o.key == "job:" + raw["id"])
    assert visit.raw == raw["schedule"]
    assert visit.normalized.start_utc is None
    assert visit.normalized.end_utc == "2026-11-01T09:00:00+00:00"
    assert {i.code for i in visit.issues} == {
        "invalid_or_ambiguous_time",
        "incomplete_interval",
    }
    assert (
        instant(raw["work_timestamps"]["completed_at"]) == "2026-11-01T08:45:00+00:00"
    )


@pytest.mark.parametrize(
    ("local", "utc"),
    [
        ("2026-10-31T10:00:00", "2026-10-31T15:00:00+00:00"),
        ("2026-11-01T00:30:00", "2026-11-01T05:30:00+00:00"),
        ("2026-11-01T02:30:00", "2026-11-01T08:30:00+00:00"),
        ("2026-11-02T10:00:00", "2026-11-02T16:00:00+00:00"),
        ("2026-11-01T01:30:00-05:00", "2026-11-01T06:30:00+00:00"),
        ("2026-11-01T01:30:00-06:00", "2026-11-01T07:30:00+00:00"),
    ],
)
def test_synthetic_dst_boundary_and_explicit_offsets(local: str, utc: str) -> None:
    assert instant(local) == utc


def test_pack_recurrence_library_keeps_wall_clock_across_dst() -> None:
    """Oracle probe only: the production adapter still defers expansion to P3."""
    import recurring_ical_events
    from icalendar import Calendar

    path = Path("data/sources/calendars/abrams_plumbing_google_calendar.ics")
    cal = Calendar.from_ical(path.read_bytes())
    zone = ZoneInfo("America/Chicago")
    events = recurring_ical_events.of(cal).between(
        datetime(2026, 10, 30, tzinfo=zone), datetime(2026, 11, 7, tzinfo=zone)
    )
    starts = sorted(
        e.decoded("DTSTART")
        for e in events
        if str(e["UID"]) == "gv5ruhbae00nusuus5qkg12p37@google.com"
    )
    assert [d.isoformat() for d in starts] == [
        "2026-10-30T07:00:00-05:00",
        "2026-11-06T07:00:00-06:00",
    ]
    assert [d.astimezone(UTC).isoformat() for d in starts] == [
        "2026-10-30T12:00:00+00:00",
        "2026-11-06T13:00:00+00:00",
    ]

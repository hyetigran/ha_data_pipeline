from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from house_account.adapters.other import (
    _calendar_instant,
    _calendars,
    _hours,
    _spreadsheet,
)
from house_account.model import Issue


def test_calendar_semantics_from_pack() -> None:
    blocks = [o for o in _calendars(Path("data")) if o.kind == "calendar_block"]
    assert len(blocks) == 91
    assert sum(bool(o.normalized.attributes["rrule"]) for o in blocks) == 3
    absence = next(o for o in blocks if o.normalized.attributes["all_day"])
    assert absence.normalized.attributes["start_local"] == "2026-11-04"
    assert absence.normalized.attributes["end_local"] == "2026-11-09"
    assert absence.normalized.attributes["end_exclusive"]
    assert absence.normalized.start_utc is None
    assert any(
        o.normalized.attributes["tentative"] and o.normalized.attributes["blocking"]
        for o in blocks
    )
    assert any(
        o.normalized.attributes["transparency"] == "TRANSPARENT"
        and not o.normalized.attributes["blocking"]
        for o in blocks
    )
    assert all(o.snapshot_at == "2026-11-02" for o in blocks)
    assert all("dtstamp" in o.normalized.attributes for o in blocks)


def test_uncertain_calendar_times_are_not_guessed() -> None:
    issues: list[Issue] = []
    assert _calendar_instant(datetime(2026, 11, 1, 1, 30), "DTSTART", issues) is None
    assert issues[-1].code == "floating_calendar_time"
    assert (
        _calendar_instant(
            datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/Chicago")),
            "DTSTART",
            issues,
        )
        is None
    )
    assert issues[-1].code == "ambiguous_calendar_time"
    assert (
        _calendar_instant(
            datetime(2026, 3, 8, 2, 30, tzinfo=ZoneInfo("America/Chicago")),
            "DTSTART",
            issues,
        )
        is None
    )
    assert (
        _calendar_instant(
            datetime(2026, 11, 3, 10, tzinfo=ZoneInfo("America/Chicago")),
            "DTSTART",
            issues,
        )
        == "2026-11-03T16:00:00+00:00"
    )


def test_spreadsheet_ambiguity_and_optional_invalid_money(tmp_path: Path) -> None:
    directory = tmp_path / "sources/spreadsheet"
    directory.mkdir(parents=True)
    (directory / "rays_fixit_job_log.csv").write_text(
        "Ray's Fix-It - JOB LOG,,,,,,,,\nexported 10/30/2026 from Google Sheets,,,,,,,,\n"
        "Date,Time,Customer,Phone,Address,Job,$,Paid?,Notes\n"
        "next tues,8am,Example,,123 Example St,repair,not money,Y,\n"
    )
    job = list(_spreadsheet(tmp_path))[-1]
    assert job.normalized.amount_minor is None
    assert job.normalized.status == "unknown"
    assert job.normalized.attributes["start_utc"] is None
    assert {issue.code for issue in job.issues} >= {
        "invalid_money",
        "date_requires_review",
        "duration_unknown",
        "completion_not_established",
    }
    assert job.snapshot_at == "2026-10-30"


def test_hours_preserve_emergency_qualifier_and_ambiguity() -> None:
    hours, issues = _hours("24/7 emergency service")
    assert hours["emergency_only"]
    assert not hours["weekdays"]
    assert issues[0].code == "routine_hours_unknown"
    hours, issues = _hours("M-F 8-5")
    assert not hours["weekdays"]
    assert issues[0].code == "ambiguous_working_hours"
    hours, issues = _hours("Mon-Fri 8am-5pm, Sat 9am-1pm")
    assert hours["weekdays"]["mon"] == [["08:00", "17:00"]]
    assert hours["weekdays"]["sat"] == [["09:00", "13:00"]]
    assert "sun" not in hours["weekdays"]
    assert not issues

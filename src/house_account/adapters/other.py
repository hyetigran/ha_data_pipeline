from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

from icalendar import Calendar

from house_account.model import (
    Entity,
    Issue,
    Observation,
    digest,
    identity,
    instant,
    money,
)

ZONE = "America/Chicago"
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _hours(value: Any) -> tuple[dict[str, Any], list[Issue]]:
    result: dict[str, Any] = {"raw": value, "timezone": ZONE, "weekdays": {}}
    issues: list[Issue] = []
    if isinstance(value, dict):
        for day, span in value.items():
            if day not in DAYS or not isinstance(span, str):
                raise ValueError("invalid working hours dictionary")
            if span == "closed":
                result["weekdays"][day] = []
            elif re.fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", span):
                start, end = span.split("-")
                datetime.strptime(start, "%H:%M")
                datetime.strptime(end, "%H:%M")
                if start >= end:
                    raise ValueError("invalid hours interval")
                result["weekdays"][day] = [[start, end]]
            else:
                issues.append(Issue(code="unparsed_working_hours", field=day))
        return result, issues
    if not isinstance(value, str):
        return result, [Issue(code="missing_working_hours", field="hours")]
    if "emergency" in value.lower():
        result["emergency_only"] = True
        return result, [Issue(code="routine_hours_unknown", field="hours")]
    for label, start, end in re.findall(
        r"(Weekdays|Mon-Fri|Saturday|Sat)\s+(\d{2}:\d{2}|\d{1,2}(?:am|pm))-(\d{2}:\d{2}|\d{1,2}(?:am|pm))",
        value,
    ):

        def clock(raw: str) -> str:
            return datetime.strptime(raw, "%H:%M" if ":" in raw else "%I%p").strftime(
                "%H:%M"
            )

        span = [clock(start), clock(end)]
        if span[0] >= span[1]:
            raise ValueError("invalid working hours interval")
        for day in DAYS[:5] if label in ("Weekdays", "Mon-Fri") else ("sat",):
            result["weekdays"][day] = [span]
    if "closed weekends" in value:
        result["weekdays"].update(sat=[], sun=[])
    if not result["weekdays"]:
        issues.append(Issue(code="ambiguous_working_hours", field="hours"))
    return result, issues


def _spreadsheet(root: Path) -> Iterator[Observation]:
    path = root / "sources/spreadsheet/rays_fixit_job_log.csv"
    source, account = "spreadsheet", "rays_fixit"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        title, export = next(handle), next(handle)
        match = re.search(r"exported (\d{2}/\d{2}/\d{4})", export)
        if not match:
            raise ValueError("missing spreadsheet export date")
        snapshot = datetime.strptime(match[1], "%m/%d/%Y").date().isoformat()
        provider_id = identity(source, account, "provider", account)
        yield Observation(
            source=source,
            account=account,
            kind="provider",
            key=account,
            file=str(path.relative_to(root)),
            locator="preamble:1-2",
            raw={"title": title.strip(), "export": export.strip()},
            snapshot_at=snapshot,
            issues=[Issue(code="unlinked_provider", field="account")],
            normalized=Entity(kind="provider", display_name="Ray's Fix-It"),
        )
        reader = csv.DictReader(handle)
        if reader.fieldnames != [
            "Date",
            "Time",
            "Customer",
            "Phone",
            "Address",
            "Job",
            "$",
            "Paid?",
            "Notes",
        ]:
            raise ValueError("unexpected spreadsheet columns")
        for rownum, row in enumerate(reader, 4):
            if None in row or any(v is None for v in row.values()):
                raise ValueError("malformed spreadsheet row")
            issues = [Issue(code="duration_unknown", field="Time")]
            parsed_date = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
                try:
                    parsed_date = datetime.strptime(row["Date"].strip(), fmt).date()
                    break
                except ValueError:
                    pass
            parsed_time = None
            for fmt in ("%H:%M", "%I:%M%p", "%I%p"):
                try:
                    parsed_time = datetime.strptime(row["Time"].strip(), fmt).time()
                    break
                except ValueError:
                    pass
            if parsed_date is None:
                issues.append(Issue(code="date_requires_review", field="Date"))
            if parsed_time is None:
                issues.append(Issue(code="time_requires_review", field="Time"))
            start = (
                instant(datetime.combine(parsed_date, parsed_time))
                if parsed_date and parsed_time
                else None
            )
            note = row["Notes"].strip().lower()
            status = (
                "cancelled"
                if note in ("cust cancelled", "cancelled", "cxl")
                else "unknown"
            )
            if status == "unknown":
                issues.append(Issue(code="completion_not_established", field="Paid?"))
            # Content identity deduplicates exact repeated rows without guessing that similar rows are identical.
            key = digest(row)
            try:
                amount = money(row["$"])
            except ValueError:
                amount = None
                issues.append(Issue(code="invalid_money", field="$"))
            yield Observation(
                source=source,
                account=account,
                kind="job",
                key=key,
                file=str(path.relative_to(root)),
                locator=f"row:{rownum}",
                raw=dict(row),
                snapshot_at=snapshot,
                issues=issues,
                normalized=Entity(
                    kind="job",
                    provider_id=provider_id,
                    service=row["Job"],
                    status=status,
                    source_status=row["Notes"],
                    amount_minor=amount,
                    currency="USD",
                    attributes={
                        "address_raw": row["Address"],
                        "date": parsed_date.isoformat() if parsed_date else None,
                        "start_utc": start,
                        "timezone_origin": ZONE,
                        "end_utc": None,
                        "duration_unknown": True,
                    },
                ),
            )


def _calendar_instant(value: Any, field: str, issues: list[Issue]) -> str | None:
    if value is None or type(value) is date:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        issues.append(Issue(code="floating_calendar_time", field=field))
        return None
    try:
        zone = getattr(value.tzinfo, "key", None)
        if zone:
            return instant(value.replace(tzinfo=None), local_zone=zone)
        return instant(value)
    except ValueError:
        issues.append(Issue(code="ambiguous_calendar_time", field=field))
        return None


def _calendars(root: Path) -> Iterator[Observation]:
    for path in sorted((root / "sources/calendars").glob("*.ics")):
        text = path.read_text()
        calendar = Calendar.from_ical(text)
        source, account = "calendars", path.stem
        provider_id = identity(source, account, "provider", account)
        filename = str(path.relative_to(root))
        yield Observation(
            source=source,
            account=account,
            kind="provider",
            key=account,
            file=filename,
            locator="VCALENDAR",
            raw={"name": str(calendar.get("X-WR-CALNAME", account))},
            issues=[Issue(code="unlinked_provider", field="account")],
            snapshot_at="2026-11-02",
            normalized=Entity(
                kind="provider", display_name=str(calendar.get("X-WR-CALNAME", account))
            ),
        )
        for index, event in enumerate(calendar.walk("VEVENT")):
            if not event.get("UID") or not event.get("DTSTART"):
                raise ValueError("calendar event missing identity or start")
            start = event.decoded("DTSTART")
            end = event.decoded("DTEND") if event.get("DTEND") else None
            all_day = isinstance(start, date) and not isinstance(start, datetime)
            issues: list[Issue] = []
            start_utc = _calendar_instant(start, "DTSTART", issues)
            end_utc = _calendar_instant(end, "DTEND", issues)
            if start_utc and end_utc and start_utc >= end_utc:
                issues.append(Issue(code="invalid_interval", field="DTEND"))
                start_utc = end_utc = None
            if all_day and end is not None and (type(end) is not date or end <= start):
                issues.append(Issue(code="invalid_interval", field="DTEND"))
            if end is None:
                issues.append(Issue(code="calendar_end_unknown", field="DTEND"))
            status, transparency = (
                str(event.get("STATUS", "CONFIRMED")),
                str(event.get("TRANSP", "OPAQUE")),
            )
            attrs = {
                "all_day": all_day,
                "end_exclusive": True,
                "start_local": start.isoformat(),
                "end_local": end.isoformat() if end else None,
                "transparency": transparency,
                "blocking": status != "CANCELLED" and transparency != "TRANSPARENT",
                "tentative": status == "TENTATIVE",
                "rrule": cast(bytes, event["RRULE"].to_ical()).decode()
                if event.get("RRULE")
                else None,
                "recurrence_expanded": False,
                "recurrence_id": str(event.get("RECURRENCE-ID", "")),
                "location_raw": str(event.get("LOCATION", "")),
                "dtstamp": str(event.decoded("DTSTAMP"))
                if event.get("DTSTAMP")
                else None,
                "snapshot_evidence": "README.md: Snapshot times",
            }
            if event.get("RRULE"):
                issues.append(Issue(code="recurrence_pending_p3", field="RRULE"))
            yield Observation(
                source=source,
                account=account,
                kind="calendar_block",
                key=str(event["UID"]) + ":" + attrs["recurrence_id"],
                file=filename,
                locator=f"VEVENT:{index}",
                raw={
                    "ical": event.to_ical().decode(),
                    "calendar_timezone": str(calendar.get("X-WR-TIMEZONE", "")),
                },
                snapshot_at="2026-11-02",
                issues=issues,
                normalized=Entity(
                    kind="calendar_block",
                    provider_id=provider_id,
                    status=status.lower(),
                    source_status=status,
                    start_utc=start_utc,
                    end_utc=end_utc,
                    timezone_origin=str(
                        event["DTSTART"].params.get(
                            "TZID",
                            "UTC" if getattr(start, "tzinfo", None) else "floating",
                        )
                    ),
                    attributes=attrs,
                ),
            )


def _profiles(root: Path) -> Iterator[Observation]:
    path = root / "sources/profiles/providers.json"
    document = json.loads(path.read_text())
    for index, row in enumerate(document["providers"]):
        hours, issues = _hours(row.get("hours"))
        provider_id = identity("profiles", "directory", "provider", row["profile_id"])
        yield Observation(
            source="profiles",
            account="directory",
            kind="provider",
            key=row["profile_id"],
            file=str(path.relative_to(root)),
            locator=f"providers:{index}:provider",
            raw=row,
            snapshot_at=document.get("exported_at"),
            issues=[Issue(code="unlinked_provider", field="profile_id")],
            normalized=Entity(
                kind="provider",
                display_name=row["business_name"],
                attributes={"profile_id": row["profile_id"]},
            ),
        )
        yield Observation(
            source="profiles",
            account="directory",
            kind="profile",
            key=row["profile_id"],
            file=str(path.relative_to(root)),
            locator=f"providers:{index}",
            raw=row,
            snapshot_at=document.get("exported_at"),
            issues=issues,
            normalized=Entity(
                kind="profile",
                provider_id=provider_id,
                display_name=row["business_name"],
                attributes={**row, "working_hours": hours},
            ),
        )


def _reference(root: Path) -> Iterator[Observation]:
    path = root / "reference/street_segments.csv"
    with path.open(newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), 2):
            parsed: dict[str, Any] = dict(row)
            for name in ("from_number", "to_number"):
                parsed[name] = int(row[name])
            for name in ("start_lat", "start_lon", "end_lat", "end_lon"):
                parsed[name] = float(row[name])
            if parsed["from_number"] > parsed["to_number"]:
                raise ValueError("invalid street segment range")
            yield Observation(
                source="reference",
                account="streets",
                kind="street_segment",
                key=digest(row),
                file=str(path.relative_to(root)),
                locator=f"row:{line}",
                raw=row,
                normalized=Entity(kind="street_segment", attributes=parsed),
            )


def load(root: Path) -> Iterator[Observation]:
    yield from _spreadsheet(root)
    yield from _calendars(root)
    yield from _profiles(root)
    yield from _reference(root)

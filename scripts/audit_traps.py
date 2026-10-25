"""Read-only pack audit. Evidence locators exclude homeowner payloads.

Candidate families are not a reconstruction of the hidden 22-item answer key.
Run from the repository root; JSON goes to stdout, no database writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from house_account import privacy
from house_account.adapters import crm, other
from house_account.addresses import normalize
from house_account.identity import phone
from house_account.model import digest, instant


def audit(root: Path) -> dict:
    observations = list(crm.load(root)) + list(other.load(root))
    unique = {o.id: o for o in observations}
    groups: dict[str, list[dict]] = defaultdict(list)

    def add(category, o, **facts):
        groups[category].append(
            dict(file=o.file, locator=o.locator, key=o.key, kind=o.kind, **facts)
        )

    segments = [
        o.normalized.attributes for o in unique.values() if o.kind == "street_segment"
    ]
    phones = defaultdict(list)
    address_groups = defaultdict(list)
    properties = {o.id: o for o in unique.values() if o.kind == "property"}
    target_zips = {
        "75204",
        "75206",
        "75214",
        "75218",
        "75219",
        "75223",
        "75230",
        "75080",
        "75041",
    }
    seen = {}
    multi_visits = Counter(
        o.normalized.job_id for o in unique.values() if o.kind == "visit"
    )
    for o in observations:
        if o.id in seen:
            assert digest(o.raw) == digest(seen[o.id].raw)
            add(
                "repeated_source_identity",
                o,
                first_file=seen[o.id].file,
                first_locator=seen[o.id].locator,
            )
        seen[o.id] = o
    for o in unique.values():
        e, raw = o.normalized, o.raw
        for issue in o.issues:
            add("issue:" + issue.code, o, field=issue.field)
        if o.kind == "provider":
            p = phone(raw)
            if p:
                phones[p].append(o)
        if o.kind == "job" and multi_visits[o.id] > 1:
            add("multiple_visits", o, visits=multi_visits[o.id])
        if o.kind in {"visit", "job", "estimate"}:
            if e.status in {
                "cancelled",
                "pending_approval",
                "unscheduled",
                "overdue",
                "action_required",
                "submitted",
            }:
                add("status:" + e.status, o, source_status=e.source_status)
            if o.kind == "estimate":
                add("estimate:" + str(e.status), o)
            if e.amount_minor is not None:
                add("money:" + o.source, o, minor=e.amount_minor)
        address = None
        if o.kind == "property":
            address = e.attributes.get("address_raw", e.attributes.get("address"))
        if o.source == "spreadsheet" and o.kind == "job":
            address = raw["Address"]
            if "reschedul" in raw["Notes"].lower():
                add("spreadsheet_reschedule", o)
            if raw["Paid?"].strip():
                add("spreadsheet_payment_not_completion", o)
        if (
            o.kind == "visit"
            and e.status == "scheduled"
            and e.property_id in properties
        ):
            prop = properties[e.property_id]
            a = normalize(prop.normalized.attributes["address"], segments)
            if a.postal_code and a.postal_code not in target_zips:
                add("out_of_area_scheduled", o, postal_code=a.postal_code)
        if o.kind == "customer" and any(
            k.lower()
            in {"phones", "emails", "phone", "email", "firstname", "first_name"}
            for k in raw
        ):
            add("homeowner_pii", o)
        if address:
            a = normalize(address, segments)
            if a.key:
                address_groups[a.key].append(o)
            if re.search(r"siwss|merceeds", str(address), re.IGNORECASE):
                add("street_typo", o)
            if a.precision == "missing":
                add("address_unresolved", o)
            if a.unit:
                add("address_units", o, unit=a.unit)
        if o.kind == "calendar_block":
            a = e.attributes
            for category, condition in {
                "calendar_all_day": a["all_day"],
                "calendar_recurring": bool(a["rrule"]),
                "calendar_tentative": a["tentative"],
                "calendar_transparent": not a["blocking"],
                "calendar_no_location": not a["location_raw"],
                "calendar_utc": e.timezone_origin == "UTC",
            }.items():
                if condition:
                    add(
                        category,
                        o,
                        start=a["start_local"],
                        end=a["end_local"],
                        rrule=a["rrule"],
                    )
        if o.kind == "profile":
            if raw["does_not_do"]:
                add("negative_capability", o, excluded=raw["does_not_do"])
            if raw["crew_size"] > 1:
                add("multiple_crew", o, crew=raw["crew_size"])
            if "emergency" in str(raw["hours"]).lower():
                add("emergency_hours", o)
    for members in address_groups.values():
        if (
            len(
                {
                    digest(m.normalized.attributes.get("address", m.raw.get("Address")))
                    for m in members
                }
            )
            > 1
        ):
            for o in members:
                add("equivalent_address_variants", o)
    # Broad deterministic candidate search; absence is not proof against fuzzy duplicates.
    visit_signatures = defaultdict(list)
    for o in unique.values():
        e = o.normalized
        if (
            o.kind != "visit"
            or not e.job_id
            or not e.start_utc
            or e.property_id not in properties
        ):
            continue
        provider = unique[e.provider_id]
        number = phone(provider.raw)
        address = normalize(
            properties[e.property_id].normalized.attributes["address"], segments
        )
        if number and address.key:
            job = unique[e.job_id]
            visit_signatures[
                (
                    number,
                    address.key,
                    e.start_utc,
                    privacy.service(job.normalized.service),
                )
            ].append(job)
    for members in visit_signatures.values():
        if len({(o.source, o.account) for o in members}) > 1:
            for o in {o.id: o for o in members}.values():
                add("cross_account_job_candidate", o)
    provider_groups = [
        [
            {"file": o.file, "locator": o.locator, "name": o.normalized.display_name}
            for o in members
        ]
        for members in phones.values()
        if len(members) > 1
    ]

    path = root / "sources/housecall_pro/dallas_drain_pros/jobs_page_2.json"
    job = json.loads(path.read_text())["jobs"][42]
    assert job["id"] == "job_ff1d934b288cafe44328e65ac5b42d15"
    start = job["schedule"]["scheduled_start"]
    assert start == "2026-11-01T01:30:00"
    local = datetime.fromisoformat(start)
    zone = ZoneInfo("America/Chicago")
    possibilities = [
        local.replace(tzinfo=zone, fold=f).astimezone(UTC).isoformat() for f in (0, 1)
    ]
    assert possibilities == ["2026-11-01T06:30:00+00:00", "2026-11-01T07:30:00+00:00"]
    try:
        instant(start)
    except ValueError:
        pass
    else:
        raise AssertionError("Ambiguous time was silently accepted")
    visit = next(
        o for o in unique.values() if o.kind == "visit" and o.key == "job:" + job["id"]
    )
    assert visit.normalized.start_utc is None
    assert visit.normalized.end_utc == "2026-11-01T09:00:00+00:00"
    assert {"invalid_or_ambiguous_time", "incomplete_interval"} <= {
        i.code for i in visit.issues
    }
    assert (
        instant(job["work_timestamps"]["completed_at"]) == "2026-11-01T08:45:00+00:00"
    )
    # Boundary probes are synthetic; the ambiguous job above is pack-derived.
    probes = {
        "2026-10-31T10:00:00": "2026-10-31T15:00:00+00:00",
        "2026-11-01T00:30:00": "2026-11-01T05:30:00+00:00",
        "2026-11-01T02:30:00": "2026-11-01T08:30:00+00:00",
        "2026-11-02T10:00:00": "2026-11-02T16:00:00+00:00",
    }
    for value, expected in probes.items():
        assert instant(value) == expected
    return {
        "files": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        },
        "observations": len(observations),
        "unique_observations": len(unique),
        "counts": {k: len(v) for k, v in sorted(groups.items())},
        "evidence": dict(sorted(groups.items())),
        "provider_phone_groups": provider_groups,
        "dst": {
            "file": str(path.relative_to(root)),
            "locator": "/jobs/42",
            "job_id": job["id"],
            "local_start": start,
            "possible_utc_starts": possibilities,
            "normalized_start": None,
            "normalized_end": visit.normalized.end_utc,
            "completion_utc": instant(job["work_timestamps"]["completed_at"]),
            "synthetic_boundary_probes": probes,
            "verified": True,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Retain three sample locators per category",
    )
    args = parser.parse_args()
    result = audit(Path("data"))
    if args.summary:
        result["evidence"] = {
            key: values[:3] for key, values in result["evidence"].items()
        }
        result["evidence_is_sampled"] = True
    print(json.dumps(result, indent=2))

"""Broaden the trap audit; stdout is private evidence, never a hidden-seed count.

Run from the repository root. Reads the pack without changing it or approving
corrections. Raw timestamp checks are independent of production instant().
Address/service comparisons deliberately exercise the current normalizers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from difflib import get_close_matches
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar

from house_account import privacy
from house_account.adapters import crm, other
from house_account.addresses import normalize, street_name
from house_account.identity import phone as business_phone

ZONE = ZoneInfo("America/Chicago")


def raw_time(value):
    if not isinstance(value, str) or not re.match(r"^20\d\d-\d\d-\d\d[T ]", value):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(UTC)
    candidates = {
        parsed.replace(tzinfo=ZONE, fold=fold).astimezone(UTC)
        for fold in (0, 1)
        if parsed.replace(tzinfo=ZONE, fold=fold).astimezone(UTC)
        .astimezone(ZONE).replace(tzinfo=None) == parsed
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def investigate(root: Path):
    findings = defaultdict(list)
    checks = Counter()

    def add(category, file, locator, **facts):
        findings[category].append(dict(file=file, locator=locator, **facts))

    def walk(value, file, locator=""):
        if isinstance(value, dict):
            if value.get("FirstName") and value.get("FirstName") == value.get("LastName"):
                add("repeated_first_last_name_token", file, locator)
            for key, child in value.items():
                walk(child, file, locator + "/" + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, file, locator + "/" + str(index))
        elif isinstance(value, str):
            if re.match(r"^20\d\d-\d\d-\d\d[T ]", value):
                checks["json_timestamp_strings"] += 1
                if raw_time(value) is None:
                    add("invalid_or_ambiguous_raw_timestamp", file, locator, raw=value)
            if re.search(r"reschedul", value, re.IGNORECASE):
                add("reschedule_text", file, locator)

    for path in sorted((root / "sources").rglob("*.json")):
        checks["json_files"] += 1
        walk(json.loads(path.read_text()), str(path.relative_to(root)))

    observations = list(crm.load(root)) + list(other.load(root))
    unique = {o.id: o for o in observations}
    segments = [o.normalized.attributes for o in unique.values() if o.kind == "street_segment"]
    streets = sorted({street_name(s["street_name"] + " " + s["street_type"]) for s in segments})
    target_zips = {s["zip"] for s in segments}
    props, jobs = {}, {}
    services = defaultdict(list)
    customers = defaultdict(list)
    for o in unique.values():
        e = o.normalized
        if o.kind == "customer" and o.source == "workiz":
            customers[(o.account, o.raw["ClientId"])].append(o)
        if o.kind == "job":
            jobs[o.id] = o
            services[e.service or ""].append(o)
            amount = o.raw.get({"jobber":"total", "housecall_pro":"total_amount",
                                "workiz":"JobTotalPrice", "spreadsheet":"$"}[o.source])
            if amount not in (None, ""):
                cleaned = str(amount).replace("$", "").replace(",", "").strip()
                expected = Decimal(cleaned) * (1 if o.source == "housecall_pro" else 100)
                checks["independent_job_money_comparisons"] += 1
                if expected != e.amount_minor:
                    add("money_normalization_disagreement", o.file, o.locator)
        if o.kind == "property":
            props[o.id] = normalize(e.attributes.get("address"), segments)
        address = None
        if o.kind == "property":
            address = e.attributes.get("address")
        elif o.source == "spreadsheet" and o.kind == "job":
            address = o.raw["Address"]
        elif o.kind == "calendar_block":
            address = e.attributes.get("location_raw")
        if address:
            a = normalize(address, segments)
            checks["address_assertions_including_calendar_locations"] += 1
            if isinstance(address,str) and address.lower().endswith(" dallas"):
                add("street_with_unseparated_city", o.file, o.locator,
                    geocoded=a.precision!="missing")
            if o.kind=="calendar_block" and len(str(address).split(","))==4:
                add("four_part_calendar_address", o.file, o.locator,
                    geocoded=a.precision!="missing")
            if a.precision == "missing":
                in_reference = a.street in streets
                candidates = get_close_matches(a.street, streets, n=3, cutoff=0.75)
                if not in_reference and candidates:
                    add("street_spelling_or_parsing_candidate", o.file, o.locator,
                        street=a.street, candidates=candidates, source=o.source,
                        supplied_postal=a.postal_code)
                elif in_reference and a.postal_code in target_zips:
                    add("reference_street_but_unresolved_target_address", o.file, o.locator)
                elif not a.postal_code or a.postal_code in target_zips:
                    add("unresolved_address_without_close_street", o.file, o.locator,
                        street=a.street, supplied_postal=a.postal_code)

    for (account, key), members in customers.items():
        raw_phones = {o.raw.get("Phone") for o in members}
        phones = {re.sub(r"\D", "", p or "")[-10:] for p in raw_phones} - {""}
        names = {(o.raw.get("FirstName"), o.raw.get("LastName")) for o in members}
        emails = {str(o.raw.get("Email") or "").strip().lower() for o in members} - {""}
        if len(members) > 1:
            add("workiz_contact_variants", members[0].file, members[0].locator,
                account=account, client_id=key, versions=len(members),
                normalized_phones=len(phones), names=len(names), normalized_emails=len(emails),
                differing_values_after_phone_email_normalization=
                len(phones)>1 or len(names)>1 or len(emails)>1)

    by_contact = defaultdict(dict)
    for o in jobs.values():
        e = o.normalized
        if o.source == "spreadsheet":
            address = normalize(o.raw["Address"], segments)
            raw_customer = o.raw
        else:
            address = props.get(e.property_id)
            raw_customer = unique[e.customer_id].raw if e.customer_id in unique else {}
        numbers = [raw_customer.get("Phone", raw_customer.get("phone", ""))]
        numbers += [p.get("number", "") for p in raw_customer.get("phones", [])]
        for value in numbers:
            number = business_phone({"phone":value})
            if number and address and address.number:
                signature = (address.number, address.street, address.unit, address.postal_code)
                by_contact[number].setdefault(signature, (o,address))
    for members in by_contact.values():
        values = list(members.values())
        for i,(left,a) in enumerate(values):
            for right,b in values[i+1:]:
                if a.unit != b.unit:
                    continue
                a_num,b_num = str(a.number),str(b.number)
                swapped = (len(a_num)==len(b_num) and sorted(a_num)==sorted(b_num)
                           and sum(x!=y for x,y in zip(a_num,b_num,strict=True))==2)
                if a.street==b.street and swapped:
                    add("shared_contact_transposed_house_number_candidate", left.file,
                        left.locator, other_file=right.file, other_locator=right.locator,
                        numbers=[a.number,b.number], street=a.street)
                elif a.number==b.number and a.street!=b.street and get_close_matches(
                        a.street,[b.street],cutoff=0.85):
                    add("shared_contact_street_variant_candidate", left.file, left.locator,
                        other_file=right.file,other_locator=right.locator,
                        streets=[a.street,b.street])

    for label, members in sorted(services.items()):
        mapped = sorted(privacy.service_codes(label))
        if "other" in mapped:
            add("unmapped_service_label", members[0].file, members[0].locator,
                label=label, jobs=len(members), mapped=mapped)
        # Deliberately narrow semantic contradictions, not fuzzy guesses.
        if (("gutter" in label.lower() and "cleaning" in mapped)
                or ("pressure wash" in label.lower() and "appliance_repair" in mapped)):
            add("service_classification_conflict", members[0].file, members[0].locator,
                label=label, jobs=len(members), mapped=mapped)

    visit_groups = defaultdict(list)
    snapshot = datetime(2026, 11, 2, 6, tzinfo=UTC)
    for o in unique.values():
        e = o.normalized
        if o.kind != "visit" or not e.job_id:
            continue
        job = jobs[e.job_id]
        if o.source == "jobber":
            start, end, completed = (o.raw.get(k) for k in ("startAt", "endAt", "completedAt"))
        elif o.source == "housecall_pro":
            start, end = (o.raw.get(k) for k in ("scheduled_start", "scheduled_end"))
            completed = job.raw.get("work_timestamps", {}).get("completed_at")
        else:
            start, end = (o.raw.get(k) for k in ("JobDateTime", "JobEndDateTime"))
            completed = None
        s, t, c = raw_time(start), raw_time(end), raw_time(completed)
        checks["job_visit_intervals"] += 1
        if s and t and t <= s:
            add("nonpositive_raw_interval", o.file, o.locator)
        if c and s and c < s:
            add("completion_before_scheduled_start", o.file, o.locator,
                scheduled=start, completed=completed)
        if c and c > snapshot:
            add("completion_after_snapshot", o.file, o.locator, completed=completed)
        if e.status == "completed" and s and s > snapshot:
            add("completed_visit_after_snapshot", o.file, o.locator, scheduled=start)
        if e.status == "cancelled" and completed:
            add("cancelled_visit_with_completion_timestamp", o.file, o.locator)
        if c and s and c.date() != s.date():
            add("completion_and_schedule_different_utc_date", o.file, o.locator)
        if o.source == "workiz":
            update = raw_time(job.raw.get("LastStatusUpdate"))
            if e.status == "completed" and s and update and update < s:
                add("done_status_updated_before_appointment", o.file, o.locator,
                    scheduled=start, updated=job.raw["LastStatusUpdate"])
        if s and e.property_id in props:
            a = props[e.property_id]
            provider = unique[e.provider_id]
            phone = business_phone(provider.raw)
            if phone and a.key:
                visit_groups[(phone, a.key, s.date().isoformat())].append(o)
    for members in visit_groups.values():
        distinct_jobs = {o.normalized.job_id for o in members}
        if len(distinct_jobs) > 1:
            add("same_business_property_day_multiple_jobs", members[0].file, members[0].locator,
                jobs=len(distinct_jobs), cross_account=len({(o.source,o.account) for o in members})>1,
                members=[{"file": o.file,"locator": o.locator,"job": o.normalized.job_id,
                              "start": o.normalized.start_utc} for o in members])

    for path in sorted((root / "sources/housecall_pro").glob("*/jobs_page_*.json")):
        for index, job in enumerate(json.loads(path.read_text())["jobs"]):
            if job.get("original_estimate_id"):
                add("job_linked_to_estimate", str(path.relative_to(root)), f"/jobs/{index}",
                    estimate_id=job["original_estimate_id"])
    for path in sorted((root / "sources/jobber").glob("*.json")):
        for index, job in enumerate(json.loads(path.read_text())["data"]["jobs"]["nodes"]):
            states = Counter(v["visitStatus"] for v in job["visits"]["nodes"])
            if len(states) > 1:
                add("job_with_mixed_visit_states", str(path.relative_to(root)),
                    f"/data/jobs/nodes/{index}", job_status=job["jobStatus"], states=dict(states))
            if job.get("recurrence"):
                visits = job["visits"]["nodes"]
                add("crm_recurrence_with_explicit_visits", str(path.relative_to(root)),
                    f"/data/jobs/nodes/{index}", visits=len(visits),
                    recurring_until=job["recurrence"].get("endDate"))

    # A discovery aid: correlate calendar occurrences with CSV month/day.
    # A yearless date is never resolved or approved by this comparison.
    csvpath = root / "sources/spreadsheet/rays_fixit_job_log.csv"
    with csvpath.open(newline="") as handle:
        physical = list(csv.reader(handle))
    csvrows = []
    for rownum, fields in enumerate(physical[3:], 4):
        row = dict(zip(physical[2], fields, strict=True))
        date = None
        yearless = False
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m/%d", "%b %d"):
            try:
                yearless = fmt in ("%m/%d", "%b %d")
                date = datetime.strptime(row["Date"] + (";2000" if yearless else ""),
                                         fmt + (";%Y" if yearless else ""))
                break
            except ValueError:
                continue
        csvrows.append((rownum,row,date,yearless,normalize(row["Address"],segments)))
    for path in sorted((root / "sources/calendars").glob("*.ics")):
        calendar = Calendar.from_ical(path.read_bytes())
        for index, event in enumerate(calendar.walk("VEVENT")):
            start = event.decoded("DTSTART")
            if not isinstance(start, datetime) or event.get("RRULE"):
                continue
            start = start.astimezone(ZONE)
            location = normalize(str(event.get("LOCATION", "")), segments)
            summary = str(event.get("SUMMARY", ""))
            if "rays" not in path.name:
                for o in unique.values():
                    e = o.normalized
                    if (o.kind != "visit" or "abrams_plumbing/" not in o.file
                            or not e.start_utc or e.appointment_kind != "job"):
                        continue
                    if datetime.fromisoformat(e.start_utc) != start:
                        continue
                    a = props.get(e.property_id)
                    add("abrams_calendar_crm_same_start", str(path.relative_to(root)),
                        f"VEVENT:{index}", uid=str(event["UID"]), crm_file=o.file,
                        crm_locator=o.locator, same_end=raw_time(e.end_utc)==event.decoded("DTEND"),
                        same_property=bool(a and a.key and a.key==location.key),
                        differing_address_fields=[k for k in
                            ("number","street","unit","city","state","postal_code")
                            if a and getattr(a,k)!=getattr(location,k)],
                        calendar_has_location=bool(event.get("LOCATION")))
                continue
            candidates = []
            for rownum, row, day, yearless, address in csvrows:
                if day is None or (day.month,day.day)!=(start.month,start.day):
                    continue
                if not yearless and day.year != start.year:
                    continue
                surname = row["Customer"].lower().replace("mrs.", "").strip().split()
                contact_hint = any(len(w)>2 and w in summary.lower() for w in surname)
                address_hint = bool(location.number and location.number == address.number)
                if contact_hint or address_hint:
                    candidates.append({"row": rownum, "date": row["Date"], "time": row["Time"],
                        "csv_service": row["Job"], "calendar_service": privacy.service(summary),
                        "same_street": location.street==address.street,
                        "same_unit": location.unit==address.unit,
                        "contact_label_hint": contact_hint, "same_house_number": address_hint})
            if candidates:
                add("ray_calendar_csv_candidates", str(path.relative_to(root)), f"VEVENT:{index}",
                    uid=str(event["UID"]), start_local=start.isoformat(),
                    end_local=event.decoded("DTEND").astimezone(ZONE).isoformat(), candidates=candidates)

    return {
        "scope": "candidate families, not grader seed identities; no corrections applied",
        "files": {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(root.rglob("*")) if p.is_file()},
        "checks": dict(checks),
        "counts": {k:len(v) for k,v in sorted(findings.items())},
        "findings": dict(sorted(findings.items())),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, help="Optional existing scratch snapshot; read only")
    args = parser.parse_args()
    report = investigate(Path("data"))
    if args.database:
        connection = sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            queries = {
                "jobs_with_unknown_component": "SELECT count(DISTINCT job_id) FROM job_services WHERE service_code='unknown'",
                "jobs_with_only_unknown_services": "SELECT count(*) FROM (SELECT job_id FROM job_services GROUP BY job_id HAVING sum(service_code!='unknown')=0)",
                "completed_jobs_with_only_unknown_services": "SELECT count(*) FROM (SELECT j.job_id FROM job_services j WHERE EXISTS(SELECT 1 FROM service_completions c WHERE c.job_id=j.job_id) GROUP BY j.job_id HAVING sum(service_code!='unknown')=0)",
                "gutter_provider_completed_jobs_classified_cleaning": "SELECT count(DISTINCT j.job_id) FROM job_services j JOIN service_completions s ON s.job_id=j.job_id JOIN canonical_jobs k ON k.id=j.job_id JOIN canonical_providers p ON p.id=k.provider_id WHERE p.display_name LIKE '%Gutter%' AND j.service_code='cleaning'",
            }
            report["projection_checks"] = {
                name:connection.execute(sql).fetchone()[0] for name,sql in queries.items()}
            report["projection_checks"]["review_proposals_by_kind"] = dict(Counter(
                json.loads(r[0])["kind"] for r in connection.execute(
                    "SELECT document FROM reconciliation_proposals")))
        finally:
            connection.close()
    print(json.dumps(report, indent=2))

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from house_account.model import (
    Entity,
    Issue,
    Observation,
    digest,
    identity,
    instant,
    money,
)

STATUS = {
    "jobber_job": {
        "archived": "archived",
        "upcoming": "scheduled",
        "today": "scheduled",
        "action_required": "action_required",
        "active": "active",
        "requires_invoicing": "requires_invoicing",
        "unscheduled": "unscheduled",
    },
    "jobber_visit": {
        "COMPLETED": "completed",
        "UPCOMING": "scheduled",
        "CANCELLED": "cancelled",
        "TODAY": "scheduled",
        "OVERDUE": "overdue",
        "UNSCHEDULED": "unscheduled",
    },
    "housecall_pro": {
        "complete rated": "completed",
        "complete unrated": "completed",
        "scheduled": "scheduled",
        "user canceled": "cancelled",
        "pro canceled": "cancelled",
        "in progress": "in_progress",
        "unscheduled": "unscheduled",
        "needs scheduling": "unscheduled",
    },
    "workiz": {
        "Done": "completed",
        "Pending": "scheduled",
        "Canceled": "cancelled",
        "Submitted": "submitted",
        "Done Pending Approval": "pending_approval",
    },
}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"Expected JSON object: {path.name}")
    return value


def _status(raw: Any, mapping: str, issues: list[Issue]) -> str:
    value = STATUS[mapping].get(str(raw))
    if value is None:
        issues.append(Issue(code="unknown_status", field="status", detail=str(raw)))
        return "unknown"
    return value


def _times(
    start: Any, end: Any, issues: list[Issue], zone: str = "America/Chicago"
) -> dict[str, Any]:
    result: dict[str, Any] = {"timezone_origin": zone}
    for field, value in [("start_utc", start), ("end_utc", end)]:
        try:
            result[field] = instant(value, local_zone=zone)
        except (ValueError, TypeError):
            result[field] = None
            issues.append(Issue(code="invalid_or_ambiguous_time", field=field))
    if not result["start_utc"] or not result["end_utc"]:
        issues.append(Issue(code="incomplete_interval"))
    elif result["end_utc"] <= result["start_utc"]:
        issues.append(Issue(code="invalid_interval_order"))
        result["start_utc"] = result["end_utc"] = None
    return result


def _amount(value: Any, issues: list[Issue], *, cents: bool = False) -> int | None:
    try:
        return money(value, cents=cents)
    except (ValueError, TypeError):
        issues.append(Issue(code="invalid_money", field="amount"))
        return None


class _Context:
    def __init__(
        self,
        root: Path,
        path: Path,
        source: str,
        account: str,
        snapshot: str | None = None,
    ):
        self.root, self.path, self.source, self.account = root, path, source, account
        self.snapshot = snapshot
        self.provider = self.ref("provider", account)

    def ref(self, kind: str, key: Any) -> str:
        return identity(self.source, self.account, kind, str(key))

    def observation(
        self,
        kind: Any,
        key: Any,
        locator: str,
        raw: dict[str, Any],
        *,
        issues: list[Issue] | None = None,
        **fields: Any,
    ) -> Observation:
        if self.source in {"workiz", "housecall_pro"}:
            fields.setdefault("attributes", {})["snapshot_basis"] = (
                "README.md: CRM exports"
            )
        return Observation(
            source=self.source,
            account=self.account,
            kind=kind,
            key=str(key),
            file=self.path.relative_to(self.root).as_posix(),
            locator=locator,
            raw=raw,
            normalized=Entity(kind=kind, **fields),
            issues=issues or [],
            snapshot_at=self.snapshot,
        )


def _jobber(root: Path) -> Iterator[Observation]:
    for path in sorted((root / "sources/jobber").glob("*.json")):
        document = _read(path)
        data = document["data"]
        account = data["account"]
        ctx = _Context(
            root,
            path,
            "jobber",
            account["id"],
            document.get("extensions", {}).get("exportedAt"),
        )
        yield ctx.observation(
            "provider",
            account["id"],
            "/data/account",
            account,
            display_name=account["name"],
            trade=account.get("industry"),
        )
        for collection in ["clients", "jobs"]:
            if data[collection]["pageInfo"]["hasNextPage"]:
                raise ValueError(
                    f"Incomplete Jobber pagination: {path.name}/{collection}"
                )
        clients, properties = set(), set()
        for i, client in enumerate(data["clients"]["nodes"]):
            clients.add(client["id"])
            location = f"/data/clients/nodes/{i}"
            yield ctx.observation(
                "customer", client["id"], location, client, provider_id=ctx.provider
            )
            for j, prop in enumerate(client["properties"]["nodes"]):
                properties.add(prop["id"])
                yield ctx.observation(
                    "property",
                    prop["id"],
                    f"{location}/properties/nodes/{j}",
                    prop,
                    provider_id=ctx.provider,
                    customer_id=ctx.ref("customer", client["id"]),
                    attributes={"address": prop["address"]},
                )
        for i, job in enumerate(data["jobs"]["nodes"]):
            customer, prop = job["client"]["id"], job["property"]["id"]
            if customer not in clients or prop not in properties:
                raise ValueError(f"Missing Jobber job reference: {path.name}")
            base = {
                "provider_id": ctx.provider,
                "customer_id": ctx.ref("customer", customer),
                "property_id": ctx.ref("property", prop),
            }
            issues: list[Issue] = []
            status = _status(job["jobStatus"], "jobber_job", issues)
            amount = _amount(job.get("total"), issues)
            location = f"/data/jobs/nodes/{i}"
            yield ctx.observation(
                "job",
                job["id"],
                location,
                job,
                **base,
                issues=issues,
                service=job.get("title"),
                status=status,
                source_status=job["jobStatus"],
                amount_minor=amount,
                currency="USD",
                attributes={
                    "recurrence": job.get("recurrence"),
                    "job_type": job.get("jobType"),
                    "amount_source_unit": "dollars",
                },
            )
            for j, visit in enumerate(job["visits"]["nodes"]):
                visit_issues: list[Issue] = []
                visit_status = _status(
                    visit["visitStatus"], "jobber_visit", visit_issues
                )
                times = _times(
                    visit.get("startAt"), visit.get("endAt"), visit_issues, "UTC"
                )
                yield ctx.observation(
                    "visit",
                    visit["id"],
                    f"{location}/visits/nodes/{j}",
                    visit,
                    **base,
                    **times,
                    issues=visit_issues,
                    job_id=ctx.ref("job", job["id"]),
                    appointment_kind="job",
                    status=visit_status,
                    source_status=visit["visitStatus"],
                    attributes={
                        "completed_at": visit.get("completedAt"),
                        "assigned_users": visit.get("assignedUsers"),
                    },
                )


def _pages(folder: Path, collection: str) -> list[tuple[Path, int, dict[str, Any]]]:
    files = sorted(folder.glob(f"{collection}_page_*.json"))
    if not files:
        raise ValueError(
            f"Missing Housecall Pro collection: {folder.name}/{collection}"
        )
    pages = [_read(path) for path in files]
    expected = pages[0]["total_pages"]
    total = pages[0]["total_items"]
    if sorted(page["page"] for page in pages) != list(range(1, expected + 1)):
        raise ValueError(f"Incomplete Housecall Pro pages: {folder.name}/{collection}")
    if any(
        page["total_pages"] != expected or page["total_items"] != total
        for page in pages
    ):
        raise ValueError(
            f"Conflicting Housecall Pro pagination: {folder.name}/{collection}"
        )
    rows = [
        (path, index, row)
        for path, page in zip(files, pages, strict=True)
        for index, row in enumerate(page[collection])
    ]
    if len({row["id"] for _, _, row in rows}) != total:
        raise ValueError(
            f"Housecall Pro item count mismatch: {folder.name}/{collection}"
        )
    return rows


def _housecall_pro(root: Path) -> Iterator[Observation]:
    for folder in sorted((root / "sources/housecall_pro").iterdir()):
        if not folder.is_dir():
            continue
        path = folder / "company.json"
        company = _read(path)
        ctx = _Context(
            root, path, "housecall_pro", company["id"], "2026-11-02T06:00:00Z"
        )
        yield ctx.observation(
            "provider", company["id"], "/", company, display_name=company["name"]
        )
        customers: set[str] = set()
        addresses: dict[str, dict[str, Any]] = {}
        for path, i, customer in _pages(folder, "customers"):
            ctx.path = path
            customers.add(customer["id"])
            location = f"/customers/{i}"
            yield ctx.observation(
                "customer", customer["id"], location, customer, provider_id=ctx.provider
            )
            for j, address in enumerate(customer["addresses"]):
                addresses[address["id"]] = address
                yield ctx.observation(
                    "property",
                    address["id"],
                    f"{location}/addresses/{j}",
                    address,
                    provider_id=ctx.provider,
                    customer_id=ctx.ref("customer", customer["id"]),
                    attributes={"address": address},
                )
        for collection, kind in [("jobs", "job"), ("estimates", "estimate")]:
            for path, i, record in _pages(folder, collection):
                ctx.path = path
                customer, address = record["customer"]["id"], record["address"]["id"]
                if customer not in customers or address not in addresses:
                    raise ValueError(
                        f"Missing Housecall Pro reference: {folder.name}/{collection}"
                    )
                base = {
                    "provider_id": ctx.provider,
                    "customer_id": ctx.ref("customer", customer),
                    "property_id": ctx.ref("property", address),
                }
                issues: list[Issue] = []
                status = _status(record["work_status"], "housecall_pro", issues)
                if any(
                    value != addresses[address].get(key)
                    for key, value in record["address"].items()
                ):
                    issues.append(
                        Issue(code="embedded_address_disagreement", field="address")
                    )
                amount = _amount(record.get("total_amount"), issues, cents=True)
                location = f"/{collection}/{i}"
                yield ctx.observation(
                    kind,
                    record["id"],
                    location,
                    record,
                    **base,
                    issues=issues,
                    service=record.get("description"),
                    status=status,
                    source_status=record["work_status"],
                    amount_minor=amount,
                    currency="USD",
                    attributes={
                        "amount_source_unit": "cents",
                        "original_estimate_id": record.get("original_estimate_id"),
                        "options": record.get("options"),
                    },
                )
                schedule = record.get("schedule")
                if schedule is not None:
                    visit_issues = [
                        issue for issue in issues if issue.code == "unknown_status"
                    ]
                    times = _times(
                        schedule.get("scheduled_start"),
                        schedule.get("scheduled_end"),
                        visit_issues,
                    )
                    yield ctx.observation(
                        "visit",
                        f"{kind}:{record['id']}",
                        location + "/schedule",
                        schedule,
                        **base,
                        **times,
                        **{f"{kind}_id": ctx.ref(kind, record["id"])},
                        issues=visit_issues,
                        appointment_kind=kind,
                        status=status,
                        source_status=record["work_status"],
                        attributes={
                            "assigned_employees": record.get("assigned_employees"),
                            "work_timestamps": record.get("work_timestamps"),
                        },
                    )


def _workiz(root: Path) -> Iterator[Observation]:
    customer_fields = ["ClientId", "FirstName", "LastName", "Company", "Phone", "Email"]
    address_fields = ["Address", "Unit", "City", "State", "PostalCode", "Country"]
    for folder in sorted((root / "sources/workiz").iterdir()):
        if not folder.is_dir():
            continue
        account = _read(folder / "account.json")
        ctx = _Context(
            root,
            folder / "account.json",
            "workiz",
            account["account_id"],
            "2026-11-02T06:00:00Z",
        )
        yield ctx.observation(
            "provider",
            account["account_id"],
            "/",
            account,
            display_name=account["company_name"],
            attributes={"timezone": account["timezone"]},
        )
        ctx.path = folder / "jobs.json"
        document = _read(ctx.path)
        rows = document["data"]
        if (
            not document["flag"]
            or document["has_more"]
            or document["found"] != len(rows)
        ):
            raise ValueError(f"Incomplete Workiz export: {folder.name}")
        customer_versions: dict[str, set[str]] = {}
        for row in rows:
            customer = {key: row.get(key) for key in customer_fields}
            customer_versions.setdefault(str(row["ClientId"]), set()).add(
                digest(customer)
            )
        for i, row in enumerate(rows):
            location = f"/data/{i}"
            customer = {key: row.get(key) for key in customer_fields}
            address = {key: row.get(key) for key in address_fields}
            customer_key = f"{row['ClientId']}:{digest(customer)}"
            address_key = digest(address)
            customer_issues = (
                [Issue(code="conflicting_customer_assertions", field="ClientId")]
                if len(customer_versions[str(row["ClientId"])]) > 1
                else []
            )
            yield ctx.observation(
                "customer",
                customer_key,
                location,
                customer,
                provider_id=ctx.provider,
                issues=customer_issues,
                attributes={"source_customer_id": str(row["ClientId"])},
            )
            yield ctx.observation(
                "property",
                address_key,
                location,
                address,
                provider_id=ctx.provider,
                attributes={
                    "address": address,
                    "identity_basis": "exact_source_address_payload",
                },
            )
            base = {
                "provider_id": ctx.provider,
                "customer_id": ctx.ref("customer", customer_key),
                "property_id": ctx.ref("property", address_key),
            }
            issues: list[Issue] = []
            status = _status(row["Status"], "workiz", issues)
            if status == "completed":
                try:
                    scheduled = instant(
                        row.get("JobDateTime"), local_zone=account["timezone"]
                    )
                    updated = instant(
                        row.get("LastStatusUpdate"), local_zone=account["timezone"]
                    )
                    if (
                        scheduled
                        and scheduled > "2026-11-02T06:00:00+00:00"
                        and updated
                        and updated < scheduled
                    ):
                        issues.append(
                            Issue(
                                code="temporal_inconsistency",
                                field="JobDateTime",
                                detail="Completed job scheduled after export and last status update; original retained",
                            )
                        )
                except (ValueError, TypeError):
                    issues.append(
                        Issue(code="invalid_status_timestamp", field="LastStatusUpdate")
                    )
            amount = _amount(row.get("JobTotalPrice"), issues)
            yield ctx.observation(
                "job",
                row["UUID"],
                location,
                row,
                **base,
                issues=issues,
                service=row.get("JobType"),
                status=status,
                source_status=row["Status"],
                amount_minor=amount,
                currency=account["currency"],
                attributes={
                    "amount_source_unit": "dollars",
                    "created_at": row.get("CreatedDate"),
                    "last_status_update": row.get("LastStatusUpdate"),
                },
            )
            visit_issues = [
                issue
                for issue in issues
                if issue.code in {"unknown_status", "temporal_inconsistency"}
            ]
            times = _times(
                row.get("JobDateTime"),
                row.get("JobEndDateTime"),
                visit_issues,
                account["timezone"],
            )
            yield ctx.observation(
                "visit",
                row["UUID"],
                location,
                {
                    "JobDateTime": row.get("JobDateTime"),
                    "JobEndDateTime": row.get("JobEndDateTime"),
                    "Status": row["Status"],
                    "Team": row.get("Team"),
                },
                **base,
                **times,
                issues=visit_issues,
                job_id=ctx.ref("job", row["UUID"]),
                appointment_kind="job",
                status=status,
                source_status=row["Status"],
                attributes={"team": row.get("Team")},
            )


def load(root: Path) -> Iterator[Observation]:
    yield from _jobber(root)
    yield from _housecall_pro(root)
    yield from _workiz(root)

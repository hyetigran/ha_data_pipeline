import json
from pathlib import Path
from typing import Any

import pytest

from house_account.adapters.crm import _housecall_pro, _jobber, _pages, _workiz


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def jobber_fixture(root: Path) -> tuple[Path, dict[str, Any]]:
    value = {
        "data": {
            "account": {"id": "account", "name": "Example"},
            "clients": {
                "pageInfo": {"hasNextPage": False},
                "nodes": [
                    {
                        "id": "client",
                        "properties": {
                            "nodes": [
                                {
                                    "id": "property",
                                    "address": {"street1": "100 Main St"},
                                }
                            ]
                        },
                    }
                ],
            },
            "jobs": {
                "pageInfo": {"hasNextPage": False},
                "nodes": [
                    {
                        "id": "job",
                        "client": {"id": "client"},
                        "property": {"id": "property"},
                        "jobStatus": "archived",
                        "total": "123.45",
                        "visits": {
                            "nodes": [
                                {
                                    "id": "visit1",
                                    "visitStatus": "COMPLETED",
                                    "startAt": "2026-10-01T12:00:00Z",
                                    "endAt": "2026-10-01T13:00:00Z",
                                },
                                {
                                    "id": "visit2",
                                    "visitStatus": "UPCOMING",
                                    "startAt": "2026-11-01T12:00:00Z",
                                    "endAt": "2026-11-01T13:00:00Z",
                                },
                            ]
                        },
                    }
                ],
            },
        }
    }
    path = root / "sources/jobber/example.json"
    write(path, value)
    return path, value


def test_jobber_keeps_job_and_multiple_visits_separate(tmp_path: Path) -> None:
    jobber_fixture(tmp_path)
    rows = list(_jobber(tmp_path))
    jobs = [row for row in rows if row.kind == "job"]
    visits = [row for row in rows if row.kind == "visit"]
    assert len(jobs) == 1
    assert len(visits) == 2
    assert jobs[0].normalized.amount_minor == 12345
    assert jobs[0].normalized.status == "archived"
    assert {v.normalized.status for v in visits} == {"completed", "scheduled"}
    assert all(v.normalized.job_id == jobs[0].id for v in visits)


def test_missing_jobber_reference_fails_import(tmp_path: Path) -> None:
    path, value = jobber_fixture(tmp_path)
    value["data"]["jobs"]["nodes"][0]["property"]["id"] = "missing"
    write(path, value)
    with pytest.raises(ValueError, match="Missing Jobber job reference"):
        list(_jobber(tmp_path))


def test_jobber_partial_export_fails_import(tmp_path: Path) -> None:
    path, value = jobber_fixture(tmp_path)
    value["data"]["jobs"]["pageInfo"]["hasNextPage"] = True
    write(path, value)
    with pytest.raises(ValueError, match="Incomplete Jobber pagination"):
        list(_jobber(tmp_path))


def page(path: Path, name: str, rows: list[dict[str, Any]], **metadata: Any) -> None:
    write(
        path,
        {"page": 1, "total_pages": 1, "total_items": len(rows), name: rows, **metadata},
    )


def test_paged_overlap_counts_unique_ids_but_retains_evidence(tmp_path: Path) -> None:
    record = {"id": "same"}
    page(tmp_path / "jobs_page_1.json", "jobs", [record], total_pages=2, total_items=1)
    page(
        tmp_path / "jobs_page_2.json",
        "jobs",
        [record],
        page=2,
        total_pages=2,
        total_items=1,
    )
    assert len(_pages(tmp_path, "jobs")) == 2
    (tmp_path / "jobs_page_2.json").unlink()
    with pytest.raises(ValueError, match="Incomplete Housecall Pro pages"):
        _pages(tmp_path, "jobs")


def test_hcp_cents_unknown_status_and_empty_interval(tmp_path: Path) -> None:
    folder = tmp_path / "sources/housecall_pro/example"
    address = {"id": "address", "street": "100 Main St"}
    write(folder / "company.json", {"id": "account", "name": "Example"})
    page(
        folder / "customers_page_1.json",
        "customers",
        [{"id": "customer", "addresses": [address]}],
    )
    record = {
        "id": "job",
        "customer": {"id": "customer"},
        "address": address,
        "work_status": "new status",
        "total_amount": 12345,
        "schedule": {"scheduled_start": None, "scheduled_end": None},
    }
    page(folder / "jobs_page_1.json", "jobs", [record])
    page(folder / "estimates_page_1.json", "estimates", [])
    rows = list(_housecall_pro(tmp_path))
    job = next(row for row in rows if row.kind == "job")
    visit = next(row for row in rows if row.kind == "visit")
    assert job.normalized.amount_minor == 12345
    assert job.normalized.status == "unknown"
    assert visit.normalized.start_utc is None
    assert {issue.code for issue in visit.issues} == {
        "unknown_status",
        "incomplete_interval",
    }
    assert job.snapshot_at == "2026-11-02T06:00:00Z"


def test_workiz_assertion_variants_and_year_conflict_are_preserved(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "sources/workiz/example"
    write(
        folder / "account.json",
        {
            "account_id": "account",
            "company_name": "Example",
            "timezone": "US/Central",
            "currency": "USD",
        },
    )
    base = {
        "ClientId": 1,
        "FirstName": "Sample",
        "Phone": "111",
        "Address": "100 Main St",
        "Status": "Done",
        "JobTotalPrice": "$123.45",
        "JobDateTime": "2026-11-10 10:00:00",
        "JobEndDateTime": "2026-11-10 12:00:00",
        "LastStatusUpdate": "2025-11-11 10:00:00",
    }
    write(
        folder / "jobs.json",
        {
            "flag": True,
            "found": 2,
            "has_more": False,
            "data": [{**base, "UUID": "one"}, {**base, "UUID": "two", "Phone": "222"}],
        },
    )
    rows = list(_workiz(tmp_path))
    customers = [row for row in rows if row.kind == "customer"]
    jobs = [row for row in rows if row.kind == "job"]
    assert len({row.id for row in customers}) == 2
    assert all(
        "conflicting_customer_assertions" in {i.code for i in row.issues}
        for row in customers
    )
    assert all("temporal_inconsistency" in {i.code for i in row.issues} for row in jobs)
    assert all(row.raw["JobDateTime"].startswith("2026") for row in jobs)
    assert jobs[0].normalized.amount_minor == 12345

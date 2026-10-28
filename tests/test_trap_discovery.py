"""Tests for investigation evidence, not a reconstruction of the grader key."""

import runpy
from pathlib import Path

import pytest

AUDIT = runpy.run_path("scripts/investigate_traps.py")


@pytest.fixture(scope="module")
def findings():
    return AUDIT["investigate"](Path("data"))


def test_raw_timestamp_audit_rejects_fold_and_gap_without_production_parser():
    parse = AUDIT["raw_time"]
    assert parse("2026-11-01 01:00:00") is None
    assert parse("2026-03-08 02:30:00") is None
    assert parse("2026-11-01T01:00:00-05:00").isoformat() == "2026-11-01T06:00:00+00:00"
    assert parse("2026-11-01T01:00:00-06:00").isoformat() == "2026-11-01T07:00:00+00:00"


def test_broad_discovery_recovers_known_anomalies_and_additional_dst_fields(findings):
    raw = findings["findings"]
    assert len(raw["invalid_or_ambiguous_raw_timestamp"]) == 9
    assert sum("workiz" in r["file"] for r in raw["invalid_or_ambiguous_raw_timestamp"]) == 6
    assert len(raw["completed_visit_after_snapshot"]) == 1
    assert raw["completed_visit_after_snapshot"][0]["locator"] == "/data/101"
    swap = raw["shared_contact_transposed_house_number_candidate"]
    assert len(swap) == 1 and swap[0]["numbers"] == [5823, 5832]
    assert swap[0]["other_locator"] == "row:175"


def test_discovery_checks_money_and_keeps_calendar_matches_as_candidates(findings):
    assert findings["checks"]["independent_job_money_comparisons"] == 11616
    assert not findings["findings"].get("money_normalization_disagreement")
    abrams = findings["findings"]["abrams_calendar_crm_same_start"]
    assert len(abrams) == 36 and all(r["same_end"] for r in abrams)
    assert sum(r["same_property"] for r in abrams) == 10
    assert next(r for r in abrams if r["locator"]=="VEVENT:2")["same_property"]
    assert len(findings["findings"]["ray_calendar_csv_candidates"]) == 16
    assert len(findings["files"]) == 176

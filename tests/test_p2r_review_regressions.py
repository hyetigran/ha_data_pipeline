import json
import sqlite3
from pathlib import Path

import pytest
from p2_fixture import build, fixture

from house_account import cli
from house_account.review import apply_review, export_review, read_ledger
from house_account.storage import connect_readonly


def test_distinct_visits_with_same_completion_timestamp_remain_distinct(tmp_path):
    observations = fixture()
    original = next(
        item for item in observations
        if item.kind == 'visit' and item.normalized.status == 'completed'
    )
    additional = original.model_copy(deep=True)
    additional.key = 'independent-visit-with-coincident-completion'
    additional.locator = 'separate-visit'
    observations.append(additional)
    database = tmp_path / 'database.sqlite'
    build(database, tmp_path / 'ledger.jsonl', observations)
    with connect_readonly(database) as connection:
        completed = connection.execute(
            "SELECT count(*) FROM service_completions WHERE visit_id IS NOT NULL"
        ).fetchone()[0]
        assert completed == 4
        for source_id in (original.id, additional.id):
            assert connection.execute(
                "SELECT count(*) FROM service_completions c "
                "JOIN canonical_crosswalk x ON x.canonical_id=c.visit_id "
                "WHERE x.kind='visit' AND x.source_id=?", (source_id,),
            ).fetchone()[0] == 1


@pytest.mark.parametrize('table', ['service_completions', 'job_services'])
def test_existing_service_attribution_cannot_move_to_another_job(tmp_path, table):
    database = tmp_path / 'database.sqlite'
    build(database, tmp_path / 'ledger.jsonl')
    with sqlite3.connect(database) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        service_id, job_id = connection.execute(
            'SELECT id,job_id FROM job_services ORDER BY id LIMIT 1'
        ).fetchone()
        other_job = connection.execute(
            'SELECT id FROM canonical_jobs WHERE id<>? LIMIT 1', (job_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO service_completions VALUES "
            "('job-level-evidence',?,NULL,'job_completed_status',NULL,'missing',"
            "'unknown',NULL,'missing')", (job_id,),
        )
        connection.execute(
            "INSERT INTO completion_services VALUES ('job-level-evidence',?)",
            (service_id,),
        )
        row_id = 'job-level-evidence' if table == 'service_completions' else service_id
        with pytest.raises(sqlite3.IntegrityError, match='another job'):
            connection.execute(
                f'UPDATE {table} SET job_id=? WHERE id=?', (other_job, row_id),
            )
        assert connection.execute(
            f'SELECT job_id FROM {table} WHERE id=?', (row_id,),
        ).fetchone()[0] == job_id


def test_reviewed_endpoints_trace_to_their_own_approval(tmp_path, monkeypatch):
    database = tmp_path / 'database.sqlite'
    ledger = tmp_path / 'ledger.jsonl'
    review = tmp_path / 'review.json'
    build(database, ledger)
    export_review(database, review, ledger)
    document = json.loads(review.read_text())
    for proposal in document['proposals']:
        if proposal['kind'] == 'field_correction':
            proposal['human'] = {
                'decision': 'approve', 'reviewer': 'Fixture reviewer',
                'reason': 'Synthetic year correction only',
                'decided_at': '2026-10-24T12:00:00Z',
            }
    review.write_text(json.dumps(document))
    monkeypatch.setattr(
        cli, 'ingest',
        lambda data, database, ledger, **kwargs: build(database, ledger),
    )
    apply_review(Path('unused'), database, review, ledger)
    decisions = {
        event['proposal']['proposed_action']['field']: event['decision_id']
        for event in read_ledger(ledger)
    }
    assert decisions['start_utc'] != decisions['end_utc']
    with connect_readonly(database) as connection:
        for field, source_field in (
            ('scheduled_start', 'start_utc'), ('scheduled_end', 'end_utc'),
        ):
            rows = connection.execute(
                'SELECT l.decision_id FROM field_lineage l '
                'JOIN canonical_visits v ON v.id=l.entity_id '
                "JOIN canonical_crosswalk x ON x.canonical_id=v.job_id AND x.kind='job' "
                'JOIN source_records r ON r.id=x.source_id '
                "WHERE r.source_key='J8OMKP' AND l.field=?", (field,),
            ).fetchall()
            assert rows
            assert {row[0] for row in rows} == {decisions[source_field]}

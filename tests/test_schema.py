import sqlite3

import pytest
from p2_fixture import build

from house_account.storage import connect_readonly


def test_relational_schema_rejects_invalid_domain_states(tmp_path):
    database=tmp_path/'schema.sqlite'
    build(database,tmp_path/'ledger')
    connection=sqlite3.connect(database)
    connection.execute('PRAGMA foreign_keys=ON')
    job=connection.execute('SELECT id FROM canonical_jobs LIMIT 1').fetchone()[0]
    provider=connection.execute('SELECT id FROM canonical_providers LIMIT 1').fetchone()[0]
    statements=[
        ("INSERT INTO canonical_providers VALUES(?,'Invalid provider')",(job,)),
        ("INSERT INTO lineage_entities VALUES('missing','job')",()),
        ("DELETE FROM canonical_jobs WHERE id=?",(job,)),
        ("UPDATE lineage_entities SET id='missing' WHERE id=?",(provider,)),
        ("UPDATE canonical_jobs SET lifecycle='banana' WHERE id=?",(job,)),
        ("UPDATE canonical_jobs SET amount_state='known',amount_minor=0,currency=NULL WHERE id=?",(job,)),
        ("UPDATE canonical_jobs SET property_link_state='missing' WHERE id=?",(job,)),
        ("UPDATE canonical_jobs SET provider_id='nonexistent' WHERE id=?",(job,)),
        ("UPDATE canonical_visits SET appointment_kind='estimate',estimate_id=NULL",()),
        ("UPDATE canonical_visits SET scheduled_start_state='ambiguous' WHERE scheduled_start_utc IS NOT NULL",()),
        ("UPDATE service_completions SET job_id='nonexistent'",()),
        ("UPDATE service_completions SET service_date=NULL,service_date_state='known'",()),
        ("UPDATE field_lineage SET field='banana'",()),
        ("UPDATE canonical_crosswalk SET canonical_id='nonexistent'",()),
    ]
    for statement,parameters in statements:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(statement,parameters)
        connection.rollback()
    connection.close()
    with connect_readonly(database) as reader:
        for table in ('canonical_providers','canonical_properties','canonical_jobs','canonical_visits'):
            assert 'document' not in {r[1] for r in reader.execute(f'PRAGMA table_info({table})')}
        assert 'amount_minor' not in {r[1] for r in reader.execute('PRAGMA table_info(providers)')}


def test_mapped_multiple_services_and_unknown_classification(tmp_path):
    from house_account import privacy
    assert privacy.service('gate fix')=='gate_repair'
    assert privacy.service('TV mounting')=='tv_mounting'
    assert privacy.service('furniture assembly')=='furniture_assembly'
    assert privacy.service('unrecognized words')=='other'


def test_active_job_and_distinct_coincident_visits(tmp_path):
    from p2_fixture import fixture

    observations=fixture()
    job=next(o for o in observations if o.kind=='job' and o.key=='0')
    job.normalized.source_status='active'
    job.normalized.status='active'
    visit=next(o for o in observations if o.kind=='visit' and o.key=='0-completed')
    copy=visit.model_copy(deep=True)
    copy.key='second-completed'
    copy.locator='second-completed'
    observations.append(copy)
    database=tmp_path/'active.sqlite'
    build(database,tmp_path/'ledger',observations)
    with connect_readonly(database) as connection:
        canonical=connection.execute("SELECT canonical_id FROM canonical_crosswalk WHERE source_id=? AND kind='job'",(job.id,)).fetchone()[0]
        assert connection.execute('SELECT lifecycle FROM canonical_jobs WHERE id=?',(canonical,)).fetchone()[0]=='active'
        assert connection.execute('SELECT count(DISTINCT visit_id) FROM service_completions WHERE job_id=?',(canonical,)).fetchone()[0]==2
        assert connection.execute("SELECT count(*) FROM canonical_visits WHERE job_id=? AND scheduling_state='scheduled'",(canonical,)).fetchone()[0]==2


def test_combined_services_do_not_invent_attribution(tmp_path):
    from p2_fixture import fixture

    observations=fixture()
    job=next(o for o in observations if o.kind=='job' and o.key=='0')
    job.normalized.service='TV mounting and furniture assembly'
    database=tmp_path/'multiple.sqlite'
    build(database,tmp_path/'ledger',observations)
    with connect_readonly(database) as connection:
        canonical=connection.execute("SELECT canonical_id FROM canonical_crosswalk WHERE source_id=? AND kind='job'",(job.id,)).fetchone()[0]
        assert {r[0] for r in connection.execute('SELECT service_code FROM job_services WHERE job_id=?',(canonical,))}=={'tv_mounting','furniture_assembly'}
        assert connection.execute('SELECT count(*) FROM service_completions WHERE job_id=?',(canonical,)).fetchone()[0]==1
        assert connection.execute('SELECT count(*) FROM completion_services cs JOIN service_completions c ON c.id=cs.completion_id WHERE c.job_id=?',(canonical,)).fetchone()[0]==0


def test_history_window_requires_local_midnight(tmp_path):
    from house_account.queries import history_radius

    with pytest.raises(ValueError,match='midnight'):
        history_radius(tmp_path/'unused.sqlite','4501 Example St',start='2026-10-01T12:00:00-05:00',end='2026-11-01T00:00:00-05:00')

import sqlite3

import pytest
from test_availability import schedule_database

from house_account.availability import available_providers
from house_account.ranking import recommend_providers


def test_ranking_evidence_duration_and_exclusions(tmp_path):
    db,pid=schedule_database(tmp_path)
    result=recommend_providers(db,'75214',service='drain')['results']
    provider=result['providers'][0]
    assert provider['provider_id']==pid
    assert provider['completed_relevant_jobs']==3
    assert provider['duration']=={'minutes':60,'basis':'median_scheduled_duration_of_single_service_completed_visits','historical_visit_sample':3}
    assert provider['score_breakdown']['relevant_completed_work']==12
    assert provider['score_breakdown']['area_evidence']==15
    assert provider['availability']['openings'][0]['duration_minutes']>=60
    assert recommend_providers(db,'75214',service='drain')==recommend_providers(db,'75214',service='drain')
    with sqlite3.connect(db) as c:
        c.execute("INSERT INTO provider_exclusions VALUES(?,'plumbing')",(pid,))
    assert recommend_providers(db,'75214',service='drain')['results']['providers']==[]


def test_service_duration_fallback_and_area_independent_of_service(tmp_path):
    db,_pid=schedule_database(tmp_path)
    result=recommend_providers(db,'75214')['results']['providers'][0]
    assert result['completed_relevant_jobs']==0
    assert result['area_evidence']['completed_work'] is True
    assert result['duration']['minutes']==240
    assert result['duration']['basis']=='disclosed_four_hour_demo_assumption'
    explicit=recommend_providers(db,'75214',duration_minutes=90)['results']['providers'][0]
    assert explicit['duration']['basis']=='explicit_request'
    assert explicit['duration']['minutes']==90
    assert recommend_providers(db,'99999')['results']['providers']==[]


def test_available_requires_relevant_completed_postal_work_and_valid_inputs(tmp_path):
    db,pid=schedule_database(tmp_path)
    result=available_providers(db,'75214',trade='plumbing')['results']
    assert [v['provider_id'] for v in result['providers']]==[pid]
    for kwargs in ({'duration_minutes':False},{'limit':False},{'service':'mystery'}):
        with pytest.raises(ValueError):
            recommend_providers(db,'75214',**kwargs)
    with pytest.raises(ValueError):
        available_providers(db,'75214',trade='plumbing',limit=True)


def test_ties_have_stable_identity_order(tmp_path):
    db,pid=schedule_database(tmp_path)
    with sqlite3.connect(db) as c:
        other=c.execute('SELECT id FROM canonical_providers WHERE id<>? LIMIT 1',(pid,)).fetchone()[0]
        c.execute("INSERT OR IGNORE INTO provider_trades VALUES(?,'plumbing')",(other,))
        c.executemany('INSERT OR IGNORE INTO provider_declared_service_areas VALUES(?,?)',[(p,'99999') for p in (pid,other)])
        source=c.execute("SELECT source_id FROM canonical_crosswalk WHERE canonical_id=? AND kind='provider' LIMIT 1",(other,)).fetchone()[0]
        for row in c.execute('SELECT * FROM provider_hour_declarations').fetchall():
            copied=list(row);copied[0]='copy-'+row[0];copied[2]=source
            c.execute('INSERT INTO provider_hour_declarations VALUES(?,?,?,?,?,?,?,?,?,?,?)',copied)
    result=recommend_providers(db,'99999',start='2026-11-02T00:00:00-06:00',end='2026-11-03T00:00:00-06:00')['results']['providers']
    assert len(result)==2
    assert result[0]['score']==result[1]['score']
    assert [r['provider_id'] for r in result]==sorted([pid,other])


def test_no_fitting_opening_discloses_duration_assumption(tmp_path):
    db,pid=schedule_database(tmp_path)
    result=recommend_providers(db,'75214',start='2026-11-02T08:00:00-06:00',end='2026-11-02T10:00:00-06:00')['results']
    assert result['providers']==[]
    excluded=next(p for p in result['excluded'] if p['provider_id']==pid)
    assert excluded['duration']=={'minutes':240,'basis':'disclosed_four_hour_demo_assumption','historical_visit_sample':0}

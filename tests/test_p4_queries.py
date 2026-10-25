import asyncio
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import date

import pytest
from p2_fixture import build, fixture
from test_availability import schedule_database
from test_mcp import ADDRESS, ROOT, protocol, successful

from house_account.model import Entity, Observation
from house_account.queries import property_history_on, provider_summary_on
from house_account.responses import Window, response
from house_account.server import ServerSettings, create_server
from house_account.storage import connect_readonly


def test_completion_date_filter_excludes_other_visits_of_same_job(tmp_path):
    observations=fixture()
    parent=next(o for o in observations if o.kind=='job' and o.key=='0')
    observations.append(Observation(source='jobber',account='example',kind='visit',key='earlier',file='fixture.json',locator='earlier',raw={'visitStatus':'COMPLETED','completedAt':'2024-11-10T15:00:00Z'},normalized=Entity(kind='visit',provider_id=parent.normalized.provider_id,property_id=parent.normalized.property_id,job_id=parent.id,appointment_kind='job',status='completed',start_utc='2024-11-10T14:00:00+00:00',end_utc='2024-11-10T15:00:00+00:00')))
    database=tmp_path/'history.db'
    build(database,tmp_path/'ledger',observations)
    async def run():
        async with protocol(database,tmp_path) as session:
            result=await successful(session,'get_property_history',{'address':ADDRESS,'start_date':'2025-11-10','end_date':'2025-11-11'})
            assert result['results']['completed_visits']==2
            for job in result['results']['jobs']['items']:
                assert all(c['service_date']=='2025-11-10' for c in job['completions']['items'])
                assert all(stamp.startswith('2025-11-10') for stamp in job['completed_at']['items'])
    asyncio.run(run())


def test_chicago_date_boundary_uses_utc_instants(tmp_path):
    database,_=schedule_database(tmp_path)
    with closing(sqlite3.connect(database)) as writer:
        writer.execute("UPDATE service_completions SET completed_at_utc='2025-11-11T05:30:00+00:00',service_date='2025-11-10' WHERE service_date='2025-11-10'")
        writer.commit()
    with closing(connect_readonly(database)) as reader:
        result=property_history_on(reader,ADDRESS,'2025-11-10T00:00:00-06:00','2025-11-11T00:00:00-06:00')['results']
        assert result['completed_visits']==2
        assert all(t=='2025-11-11T05:30:00+00:00' for job in result['jobs'] for t in job['completed_at'])


def test_pinned_connection_survives_transactional_publication(tmp_path):
    database,pid=schedule_database(tmp_path)
    with closing(connect_readonly(database)) as reader:
        old=provider_summary_on(reader,pid)['results']
        old_snapshot=reader.execute('SELECT id FROM snapshot').fetchone()[0]
        observations=fixture()
        for row in observations:
            if row.kind=='provider':
                row.normalized.display_name='Renamed business'
        build(database,tmp_path/'ledger',observations)
        still_old=provider_summary_on(reader,pid)['results']
        packaged=response(reader,date(2026,11,2),Window(start=None,end_exclusive=None),still_old['business_name'])
        assert still_old==old
        assert packaged.snapshot_id==old_snapshot and packaged.results==old['business_name']
    with closing(connect_readonly(database)) as reader:
        assert provider_summary_on(reader,pid)['results']['business_name']=='Renamed business'
        assert reader.execute('SELECT id FROM snapshot').fetchone()[0]!=old_snapshot


def test_tool_calls_open_one_connection_and_close_it_on_success_and_failure(tmp_path):
    database,pid=schedule_database(tmp_path)
    server=create_server(ServerSettings(database))
    captured=[]
    active=True
    def observe(event,arguments):
        if active and event=='sqlite3.connect/handle':
            captured.append(arguments[0])
    sys.addaudithook(observe)
    async def run():
        from mcp.server.fastmcp.exceptions import ToolError
        for arguments in ({'provider':pid},{'provider':'not a provider'}):
            before=len(captured)
            try:
                await server.call_tool('get_provider_profile',arguments)
            except ToolError:
                assert arguments['provider']=='not a provider'
            assert len(captured)==before+1
            with pytest.raises(sqlite3.ProgrammingError,match='closed'):
                captured[-1].execute('SELECT 1')
    try:
        asyncio.run(run())
    finally:
        active=False


def test_existing_invalid_snapshot_is_preserved_and_startup_is_safe(tmp_path):
    database=tmp_path/'invalid.db'
    database.write_bytes(b'private invalid snapshot')
    result=subprocess.run([sys.executable,'-m','house_account.cli','--database',str(database),'--data',str(tmp_path/'missing')],cwd=ROOT,capture_output=True,text=True,timeout=10,check=False)
    assert result.returncode==1 and not result.stdout
    assert database.read_bytes()==b'private invalid snapshot'
    assert 'Startup failed' in result.stderr and str(database) not in result.stderr


@pytest.mark.parametrize('attribution', ['unlinked', 'outside_window', 'unattributed'])
def test_property_history_services_follow_retained_completion_evidence(tmp_path, attribution):
    database=tmp_path/'history.db'
    build(database,tmp_path/'ledger')
    with closing(connect_readonly(database)) as reader:
        original=property_history_on(reader,ADDRESS)['results']['jobs'][0]
    job_id=original['id']
    with closing(sqlite3.connect(database)) as writer:
        writer.execute("INSERT INTO job_services VALUES ('additional-service',?,'electrical','electrical','Electrical work','mapped')",(job_id,))
        if attribution=='outside_window':
            writer.execute("INSERT INTO service_completions VALUES ('earlier-completion',?,NULL,'job_completion_timestamp','2024-11-10','known','completion_timestamp','2024-11-10T15:00:00+00:00','known')",(job_id,))
            writer.execute("INSERT INTO completion_services VALUES ('earlier-completion','additional-service')")
        elif attribution=='unattributed':
            writer.execute('DELETE FROM completion_services WHERE completion_id IN (SELECT id FROM service_completions WHERE job_id=?)',(job_id,))
        writer.commit()
    with closing(connect_readonly(database)) as reader:
        raw=next(j for j in property_history_on(reader,ADDRESS)['results']['jobs'] if j['id']==job_id)
        assert raw['evidence_refs']==original['evidence_refs']
        assert raw['completion_evidence_refs']
    async def run():
        async with protocol(database,tmp_path) as session:
            result=await successful(session,'get_property_history',{'address':ADDRESS,'start_date':'2025-11-10','end_date':'2025-11-11'})
            job=next(j for j in result['results']['jobs']['items'] if j['job_id']==job_id)
            assert result['results']['completed_visits']==2
            assert {s['service'] for s in job['job_scope_services']['items']}=={'drain','electrical'}
            expected=[] if attribution=='unattributed' else ['drain']
            assert [s['service'] for s in job['services']['items']]==expected
            assert len(job['completions']['items'])==1
            completion=job['completions']['items'][0]
            assert completion['service_date']=='2025-11-10'
            assert [s['service'] for s in completion['supported_services']['items']]==expected
            assert completion['service_attribution']==('unattributed' if attribution=='unattributed' else 'supported')
            assert 'Job scope does not establish performed services' in job['evidence']['interpretation']
            profile=await successful(session,'get_provider_profile',{'provider':original['provider_id']})
            history_job=next(j for j in profile['results']['history']['items'] if j['job_id']==job_id)
            expected_history={'drain','electrical'} if attribution=='outside_window' else set(expected)
            assert {s['service'] for s in history_job['services']['items']}==expected_history
    asyncio.run(run())


def test_evidence_projects_real_adapter_source_categories(tmp_path):
    from house_account.responses import evidence
    database=tmp_path/'evidence.db'
    build(database,tmp_path/'ledger')
    with closing(sqlite3.connect(database)) as connection:
        source_id=connection.execute('SELECT id FROM source_records LIMIT 1').fetchone()[0]
        for source,category in [('jobber','jobber'),('housecallpro','housecallpro'),('workiz','workiz'),('profiles','profiles'),('spreadsheet','spreadsheet'),('calendars','calendar'),('reference','street_reference'),('hostile source text','other_supplied_source')]:
            connection.execute('UPDATE source_records SET source=? WHERE id=?',(source,source_id))
            assert evidence(connection,[source_id],'test').source_categories.items==[category]

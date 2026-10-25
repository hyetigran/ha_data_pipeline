import asyncio
import json
import os
import sqlite3
import sys
from contextlib import asynccontextmanager, closing
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_availability import schedule_database

from house_account.queries import history_radius, property_history, provider_summary

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'search_service_history', 'find_available_providers', 'get_block_schedule', 'get_provider_profile', 'get_property_history', 'recommend_provider'}
ADDRESS = '4501 Example Street Apt 4, Dallas, TX 75214'


@asynccontextmanager
async def protocol(database, tmp_path, *, as_of='2026-11-02'):
    parameters = StdioServerParameters(command=sys.executable, args=['-m','house_account.cli','--database',str(database),'--as-of',as_of], cwd=str(tmp_path), env={**os.environ,'PYTHONPATH':str(ROOT/'src')})
    with (tmp_path/'stderr.log').open('w') as log:
        async with stdio_client(parameters, errlog=log) as (read,write), ClientSession(read,write) as session:
            await session.initialize()
            yield session


def logical(database):
    with closing(sqlite3.connect(database)) as connection:
        return '\n'.join(connection.iterdump())


async def successful(session, name, arguments):
    response = await session.call_tool(name,arguments)
    assert not response.isError, response
    assert response.structuredContent is not None
    return response.structuredContent


def test_stdio_discovery_six_calls_parity_limits_and_readonly(tmp_path):
    database,pid=schedule_database(tmp_path)
    before=logical(database)
    async def run():
        async with protocol(database,tmp_path) as session:
            tools=(await session.list_tools()).tools
            assert {tool.name for tool in tools} == TOOLS
            for tool in tools:
                assert tool.outputSchema and tool.inputSchema['additionalProperties'] is False
                assert tool.annotations.readOnlyHint and tool.annotations.idempotentHint
                assert not tool.annotations.destructiveHint and not tool.annotations.openWorldHint
            history=await successful(session,'search_service_history',{'address':ADDRESS,'trade':'plumbing','limit':1})
            direct=history_radius(database,ADDRESS)
            group=history['results']['groups']
            assert group['total']==len(direct['results']) and group['limit']==1
            assert group['items'][0]['distinct_jobs']==direct['results'][0]['distinct_jobs']
            assert group['items'][0]['evidence']['source_categories']['items']
            assert 'property_id' not in json.dumps(history)
            available=await successful(session,'find_available_providers',{'trade':'plumbing','history_postal_code':'75214'})
            assert available['results']['providers']['items'][0]['provider_id']==pid
            block=await successful(session,'get_block_schedule',{'street':'Example Street','city':'Dallas','state':'TX','hundred_block':4500,'limit':1})
            assert block['results']['visits']['total']==4
            assert block['results']['visits']['truncated'] is True
            visit=block['results']['visits']['items'][0]
            assert visit['business_name']=='Example Pipes' and visit['services']['items'][0]['service']=='drain'
            profile=await successful(session,'get_provider_profile',{'provider':pid,'opening_count':1,'opening_duration_minutes':180,'history_limit':1})
            assert profile['results']['completed_distinct_jobs']==provider_summary(database,pid)['results']['completed_distinct_jobs']
            assert profile['results']['history']['truncated']
            assert profile['results']['availability']['duration_minutes']==180
            assert len(profile['results']['availability']['openings']['items'])==1
            home=await successful(session,'get_property_history',{'address':ADDRESS,'limit':1})
            assert home['results']['distinct_jobs']==property_history(database,ADDRESS)['results']['distinct_jobs']
            assert home['results']['jobs']['items'][0]['business_name']=='Example Pipes'
            recommended=await successful(session,'recommend_provider',{'trade':'plumbing','service_type':'drain','postal_code':'75214','duration_minutes':120})
            candidate=recommended['results']['providers']['items'][0]
            assert candidate['provider_id']==pid and candidate['duration']['basis']=='explicit_request'
            assert len({r['snapshot_id'] for r in (history,available,block,profile,home,recommended)})==1
    asyncio.run(run())
    assert logical(database)==before
    assert 'Traceback' not in (tmp_path/'stderr.log').read_text()


def test_reference_changes_defaults_without_extending_coverage(tmp_path):
    database,pid=schedule_database(tmp_path)
    async def run():
        async with protocol(database,tmp_path,as_of='2026-12-10') as session:
            profile=await successful(session,'get_provider_profile',{'provider':pid})
            assert profile['as_of']=='2026-12-10'
            assert profile['window']['start'].startswith('2026-12-10')
            assert profile['coverage']['schedule_end_exclusive'].startswith('2026-12-03')
            assert profile['results']['availability']['status']=='unknown'
            assert profile['results']['availability']['openings'] is None
    asyncio.run(run())


def test_optional_history_dates_and_trade_filter_before_totals(tmp_path):
    database,_=schedule_database(tmp_path)
    async def run():
        async with protocol(database,tmp_path) as session:
            history=await successful(session,'search_service_history',{'address':ADDRESS,'trade':'electrical','limit':1})
            assert history['results']['groups']['total']==0
            home=await successful(session,'get_property_history',{'address':ADDRESS,'start_date':'2026-01-01','end_date':'2026-02-01'})
            assert home['results']['distinct_jobs']==0 and home['results']['completed_visits']==0
            home=await successful(session,'get_property_history',{'address':ADDRESS,'start_date':'2025-11-10','end_date':'2025-11-11'})
            assert home['results']['distinct_jobs']==2 and home['results']['completed_visits']==2
            assert home['results']['jobs']['items'][0]['completions']['items'][0]['service_date']=='2025-11-10'
    asyncio.run(run())

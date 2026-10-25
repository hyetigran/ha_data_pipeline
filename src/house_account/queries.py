from __future__ import annotations

import json
import math
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

from .addresses import distance_miles, normalize
from .model import instant
from .storage import connect_readonly

START = '2024-11-02T05:00:00+00:00'
END = '2026-11-02T06:00:00+00:00'


def records(connection: sqlite3.Connection, sql: str, parameters: Any = ()) -> list[dict[str,Any]]:
    cursor=connection.execute(sql,parameters)
    names=[column[0] for column in cursor.description]
    return [dict(zip(names,row,strict=True)) for row in cursor]


def _address(connection: sqlite3.Connection, address: Any):
    segments=[dict(id=r[0],**json.loads(r[1])) for r in connection.execute('SELECT id,attributes_json FROM street_segments')]
    return normalize(address,segments)


def _envelope(connection: sqlite3.Connection, results: Any) -> dict[str,Any]:
    return {'results':results,'coverage':{'properties_missing_coordinates':connection.execute('SELECT count(*) FROM canonical_properties WHERE latitude IS NULL').fetchone()[0],'source_scope':'nine target postal codes; absence is not evidence of no experience','completed_visit_count_basis':'Independent visit completion evidence; job-level completion and projected schedules do not establish performed visits','unknown_spreadsheet_intervals':connection.execute("SELECT count(*) FROM source_records WHERE source='spreadsheet' AND kind='job'").fetchone()[0]},'limitations':['Coordinates are approximate street-segment interpolation.','Uncertain identities remain separate.','Travel is not modeled; candidate availability uses a separate bounded query.','Date-only completions count only when their entire local date lies in the requested window.','Trade groups can overlap; their distinct job counts are not additive.'],'snapshot_id':connection.execute('SELECT id FROM snapshot').fetchone()[0]}


def _provider_label(connection: sqlite3.Connection, pid: str | None) -> str:
    row=connection.execute('SELECT display_name FROM canonical_providers WHERE id=?',(pid,)).fetchone()
    return row[0] if row else 'Unknown provider'


def _job(connection: sqlite3.Connection, row: dict[str,Any], start: str | None = None, end: str | None = None) -> dict[str,Any]:
    services=records(connection,'SELECT trade_code,service_code,safe_description,classification_state FROM job_services WHERE job_id=? ORDER BY id',(row['id'],))
    completion=records(connection,'SELECT * FROM service_completions WHERE job_id=?',(row['id'],))
    if start or end:
        from .projection import local_date
        completion=[c for c in completion if c['service_date_state']!='known' or ((not start or (c['completed_at_utc']>=start if c['completed_at_utc'] else c['service_date']>=local_date(start))) and (not end or (c['completed_at_utc']<end if c['completed_at_utc'] else c['service_date']<local_date(end))))]
    attributed=records(connection,'SELECT cs.completion_id,s.id,s.trade_code,s.service_code,s.safe_description,s.classification_state FROM completion_services cs JOIN job_services s ON s.id=cs.job_service_id WHERE s.job_id=? ORDER BY s.id',(row['id'],))
    retained={c['id'] for c in completion}
    supported={s['id']:{k:v for k,v in s.items() if k not in ('id','completion_id')} for s in attributed if s['completion_id'] in retained}
    for c in completion:
        c['supported_services']=[{k:v for k,v in s.items() if k not in ('id','completion_id')} for s in attributed if s['completion_id']==c['id']]
        c['service_attribution']='supported' if c['supported_services'] else 'unattributed'
    refs=[r[0] for r in connection.execute("SELECT source_id FROM canonical_crosswalk WHERE canonical_id=? AND kind='job' ORDER BY source_id",(row['id'],))]
    completion_refs=sorted({ref for cid,ref in connection.execute('SELECT ce.completion_id,ce.source_id FROM completion_evidence ce JOIN service_completions c ON c.id=ce.completion_id WHERE c.job_id=?',(row['id'],)) if cid in retained})
    reviewed=any(json.loads(r[0]).get('decisions') for r in connection.execute("SELECT evidence FROM canonical_crosswalk WHERE canonical_id=? AND kind='job'",(row['id'],)))
    return {'id':row['id'],'provider_id':row['provider_id'],'business_name':_provider_label(connection,row['provider_id']),'property_id':row['property_id'],'trade':services[0]['trade_code'] if services else 'unknown','service':services[0]['service_code'] if services else 'unknown','services':services,'completion_supported_services':list(supported.values()),'status':row['lifecycle'],'lifecycle':row['lifecycle'],'completed_at':sorted({c['completed_at_utc'] for c in completion if c['completed_at_utc']}),'service_completions':[{k:c[k] for k in ('service_date','service_date_state','service_date_basis','completed_at_state','evidence_basis','supported_services','service_attribution')} for c in completion],'completed_visits':len({c['visit_id'] for c in completion if c['visit_id'] and (not (start or end) or c['service_date_state']=='known')}),'uncertain_dates':any(c['service_date_state']!='known' for c in completion),'reviewed':reviewed,'evidence_refs':refs,'completion_evidence_refs':completion_refs,'completion_precision':'status_confirmed_scheduled_date' if any(c['service_date_basis']=='completed_job_schedule' for c in completion) else 'completion_timestamp' if completion and all(c['service_date_basis']=='completion_timestamp' for c in completion) else 'completed_visit_schedule' if completion and all(c['service_date_basis']=='completed_visit_schedule' for c in completion) else 'mixed_or_unknown'}


def property_history(database: Path,address: Any) -> dict[str,Any]:
    with closing(connect_readonly(database)) as connection:
        return property_history_on(connection,address)


def property_history_on(connection: sqlite3.Connection,address: Any,start: str | None = None,end: str | None = None) -> dict[str,Any]:
    start,end=instant(start),instant(end)
    target=_address(connection,address)
    matches=[r[0] for r in connection.execute("SELECT id FROM canonical_properties WHERE house_number=? AND street=? AND coalesce(unit,'')=? AND city=? AND state=? AND coalesce(postal_code,'')=?",target.key or (None,)*6)]
    slots=','.join('?' for _ in matches) or 'NULL'
    rows=records(connection,f'SELECT * FROM canonical_jobs WHERE property_id IN ({slots}) ORDER BY id',matches)
    jobs=[_job(connection,r,start,end) for r in rows]
    if start or end:
        jobs=[j for j in jobs if j["service_completions"]]
    complete=[j for j in jobs if any(c['service_date_state']=='known' for c in j['service_completions'])]
    return _envelope(connection,{'property_ids':matches,'jobs':complete,'other_or_uncertain_jobs':[j for j in jobs if j not in complete],'distinct_jobs':len(complete),'completed_visits':sum(j['completed_visits'] for j in complete),'observed_jobs':len(jobs)})


def _history_window(start: str,end: str,radius_miles: float) -> tuple[str,str]:
    start,end=str(instant(start)),str(instant(end))
    if not 0<radius_miles<=10 or start>=end:
        raise ValueError('invalid radius or time window')
    boundaries=[datetime.fromisoformat(t).astimezone(ZoneInfo('America/Chicago')) for t in (start,end)]
    if any(t.hour or t.minute or t.second or t.microsecond for t in boundaries):
        raise ValueError('history windows require America/Chicago midnight boundaries because some service dates have day precision')
    return start,end


def history_radius(database: Path,address: Any,radius_miles: float=.5,start: str=START,end: str=END) -> dict[str,Any]:
    start,end=_history_window(start,end,radius_miles)
    with closing(connect_readonly(database)) as connection:
        return history_radius_on(connection,address,radius_miles,start,end)


def history_radius_on(connection: sqlite3.Connection,address: Any,radius_miles: float=.5,start: str=START,end: str=END,trade: str | None = None) -> dict[str,Any]:
    start,end=_history_window(start,end,radius_miles)
    target=_address(connection,address)
    if target.latitude is None or target.longitude is None:
        raise ValueError('address has no unambiguous supported coordinates')
    delta=math.degrees(radius_miles/3958.7613)
    longitude_delta=delta/max(.01,math.cos(math.radians(target.latitude+delta)))
    properties=records(connection,'SELECT id,latitude,longitude FROM canonical_properties WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?',(target.latitude-delta,target.latitude+delta,target.longitude-longitude_delta,target.longitude+longitude_delta))
    nearby={p['id']:distance_miles(target.latitude,target.longitude,p['latitude'],p['longitude']) for p in properties}
    nearby={key:value for key,value in nearby.items() if value<=radius_miles+1e-12}
    placeholders=','.join('?' for _ in nearby) or 'NULL'
    from .projection import local_date
    start_local=datetime.fromisoformat(start).astimezone(ZoneInfo('America/Chicago'))
    date_start=(start_local.date()+timedelta(days=bool(start_local.hour or start_local.minute or start_local.second or start_local.microsecond))).isoformat()
    selected=records(connection,f"SELECT DISTINCT j.id,j.provider_id,j.property_id,s.trade_code,p.display_name FROM canonical_jobs j JOIN canonical_providers p ON p.id=j.provider_id JOIN job_services s ON s.job_id=j.id JOIN completion_services cs ON cs.job_service_id=s.id JOIN service_completions c ON c.id=cs.completion_id WHERE j.property_id IN ({placeholders}) AND c.service_date_state='known' AND ((c.completed_at_utc IS NOT NULL AND c.completed_at_utc>=? AND c.completed_at_utc<?) OR (c.completed_at_utc IS NULL AND c.service_date>=? AND c.service_date<?))",[*nearby,start,end,date_start,local_date(end)])
    groups: dict[tuple,list[dict]]={}
    for job in selected:
        if trade is not None and job['trade_code'] != trade:
            continue
        groups.setdefault((job['provider_id'],job['trade_code']),[]).append(job)
    results=[]
    for (pid,group_trade),jobs in sorted(groups.items()):
        ids=[j['id'] for j in jobs]; slots=','.join('?' for _ in ids)
        refs=[r[0] for r in connection.execute(f"SELECT source_id FROM canonical_crosswalk WHERE kind='job' AND canonical_id IN ({slots}) ORDER BY source_id",ids)]
        count=connection.execute(f"SELECT count(DISTINCT c.visit_id) FROM service_completions c JOIN completion_services cs ON cs.completion_id=c.id JOIN job_services s ON s.id=cs.job_service_id WHERE c.job_id IN ({slots}) AND s.trade_code=? AND c.service_date_state='known' AND ((c.completed_at_utc>=? AND c.completed_at_utc<?) OR (c.completed_at_utc IS NULL AND c.service_date>=? AND c.service_date<?))",[*ids,group_trade,start,end,date_start,local_date(end)]).fetchone()[0]
        results.append({'provider_id':pid,'business_name':jobs[0]['display_name'],'trade':group_trade,'distinct_jobs':len(ids),'completed_visits':count,'evidence_refs':refs,'maximum_distance_miles':max(nearby[j['property_id']] for j in jobs)})
    return _envelope(connection,results)


def block_schedule(database: Path,address: Any,start: str='2026-11-02T06:00:00+00:00',end: str='2026-11-16T06:00:00+00:00') -> dict[str,Any]:
    with closing(connect_readonly(database)) as connection:
        return block_schedule_on(connection,address,start,end)


def block_schedule_on(connection: sqlite3.Connection,address: Any,start: str='2026-11-02T06:00:00+00:00',end: str='2026-11-16T06:00:00+00:00') -> dict[str,Any]:
    start,end=str(instant(start)),str(instant(end))
    if start>=end:
        raise ValueError('invalid time window')
    target=_address(connection,address)
    if target.number is None:
        raise ValueError('block needs a house number')
    return block_schedule_block_on(connection,target.street,target.city,target.state,target.number//100*100,start,end)


def block_schedule_block_on(connection: sqlite3.Connection,street: str,city: str,state: str,hundred_block: int,start: str,end: str) -> dict[str,Any]:
    from .addresses import street_name, words
    street,city,state=street_name(street),words(city),words(state)
    if hundred_block % 100 or not connection.execute('SELECT 1 FROM canonical_properties WHERE street=? AND city=? AND state=? LIMIT 1',(street,city,state)).fetchone():
        raise ValueError('unsupported block')
    clause='p.house_number BETWEEN ? AND ? AND p.street=? AND p.city=? AND p.state=?'
    args=[hundred_block,hundred_block+99,street,city,state]
    result=records(connection,f"SELECT v.id AS visit_id,coalesce(j.provider_id,e.provider_id) AS provider_id,coalesce(j.property_id,e.property_id) AS property_id,v.job_id,v.estimate_id,v.appointment_kind,v.scheduled_start_utc AS start_utc,v.scheduled_end_utc AS end_utc,v.scheduling_state AS status FROM canonical_visits v LEFT JOIN canonical_jobs j ON j.id=v.job_id LEFT JOIN canonical_estimates e ON e.id=v.estimate_id JOIN canonical_properties p ON p.id=coalesce(j.property_id,e.property_id) WHERE {clause} AND v.scheduled_start_utc<? AND v.scheduled_end_utc>? AND v.scheduling_state NOT IN ('cancelled','completed','superseded') ORDER BY v.scheduled_start_utc,v.id",[*args,end,start])
    for row in result:
        row['business_name']=_provider_label(connection,row['provider_id'])
        kind='job' if row['job_id'] else 'estimate'
        row['services']=records(connection,f'SELECT trade_code,service_code FROM {kind}_services WHERE {kind}_id=? ORDER BY id',(row[kind+'_id'],))
        row['evidence_refs']=[r[0] for r in connection.execute("SELECT source_id FROM canonical_crosswalk WHERE kind='visit' AND canonical_id=?",(row['visit_id'],))]
    response=_envelope(connection,result)
    uncertain=records(connection,f"SELECT j.* FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id WHERE {clause} AND j.lifecycle='unknown'",args)
    response['uncertain_candidates']=[_job(connection,j) for j in uncertain]
    response['block']={'street':street,'city':city,'state':state,'hundred_block':hundred_block}
    return response


def provider_summary(database: Path,provider_id: str) -> dict[str,Any]:
    with closing(connect_readonly(database)) as connection:
        return provider_summary_on(connection,provider_id)


def provider_summary_on(connection: sqlite3.Connection,provider_id: str,start: str='2026-11-02T00:00:00-06:00',end: str='2026-12-03T00:00:00-06:00',duration_minutes: int=120,opening_limit: int=3) -> dict[str,Any]:
    from .availability import openings
    from .availability import provider_id as find_provider
    from .registry import resolve_identity
    from .time_policy import request_window
    resolved=resolve_identity(connection,provider_id,'provider')
    if resolved['status']=='ambiguous':
        return _envelope(connection,{'identity_status':'ambiguous','requested_id':provider_id,'candidate_ids':resolved['ids']})
    if resolved['status']=='resolved':
        provider_id=cast(list[str],resolved['ids'])[0]
    provider_id=find_provider(connection,provider_id)
    schedule=openings(connection,provider_id,request_window(start,end,duration_minutes),duration_minutes,opening_limit)
    provider=connection.execute('SELECT display_name FROM canonical_providers WHERE id=?',(provider_id,)).fetchone()
    if not provider:
        raise ValueError('unknown or retired canonical provider')
    rows=records(connection,'SELECT * FROM canonical_jobs WHERE provider_id=? ORDER BY id',(provider_id,))
    completed_ids={r[0] for r in connection.execute("SELECT DISTINCT c.job_id FROM service_completions c JOIN canonical_jobs j ON j.id=c.job_id WHERE j.provider_id=? AND c.service_date_state='known'",(provider_id,))}
    uncertain_ids={r[0] for r in connection.execute("SELECT DISTINCT c.job_id FROM service_completions c JOIN canonical_jobs j ON j.id=c.job_id WHERE j.provider_id=? AND c.service_date_state<>'known'",(provider_id,))}
    history=[_job(connection,row) for row in rows if row['id'] in completed_ids]
    uncertain_history=[_job(connection,row) for row in rows if row['id'] in uncertain_ids-completed_ids]
    refs=[r[0] for r in connection.execute("SELECT source_id FROM canonical_crosswalk WHERE kind='provider' AND canonical_id=?",(provider_id,))]
    zips=[r[0] for r in connection.execute('SELECT postal_code FROM provider_declared_service_areas WHERE provider_id=? ORDER BY postal_code',(provider_id,))]
    observed=[r[0] for r in connection.execute("SELECT DISTINCT p.postal_code FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id JOIN service_completions c ON c.job_id=j.id WHERE j.provider_id=? AND c.service_date_state='known' AND p.postal_code IS NOT NULL ORDER BY p.postal_code",(provider_id,))]
    return _envelope(connection,{'provider_id':provider_id,'business_name':provider[0],'service_zips':zips,'observed_service_zips':observed,'history':history,'uncertain_date_history':uncertain_history,'trades':[r[0] for r in connection.execute('SELECT trade_code FROM provider_trades WHERE provider_id=?',(provider_id,))],'distinct_jobs':len(rows),'completed_distinct_jobs':len(history),'completed_visits':sum(j['completed_visits'] for j in history),'source_count':len(refs),'evidence_refs':refs,'openings':schedule['openings'],'opening_status':schedule['status'],'availability':schedule})

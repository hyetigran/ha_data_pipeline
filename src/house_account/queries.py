from __future__ import annotations

import json
import math
import sqlite3
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
    return {'results':results,'coverage':{'properties_missing_coordinates':connection.execute('SELECT count(*) FROM canonical_properties WHERE latitude IS NULL').fetchone()[0],'source_scope':'nine target postal codes; absence is not evidence of no experience','completed_visit_count_basis':'Independent visit completion evidence; job-level completion and projected schedules do not establish performed visits','unknown_spreadsheet_intervals':connection.execute("SELECT count(*) FROM source_records WHERE source='spreadsheet' AND kind='job'").fetchone()[0]},'limitations':['Coordinates are approximate street-segment interpolation.','Uncertain identities remain separate.','Travel and availability are not modeled in P2.','Date-only completions count only when their entire local date lies in the requested window.','Trade groups can overlap; their distinct job counts are not additive.'],'snapshot_id':connection.execute('SELECT id FROM snapshot').fetchone()[0]}


def _job(connection: sqlite3.Connection, row: dict[str,Any]) -> dict[str,Any]:
    services=records(connection,'SELECT trade_code,service_code,safe_description,classification_state FROM job_services WHERE job_id=? ORDER BY id',(row['id'],))
    completion=records(connection,'SELECT * FROM service_completions WHERE job_id=?',(row['id'],))
    refs=[r[0] for r in connection.execute("SELECT source_id FROM canonical_crosswalk WHERE canonical_id=? AND kind='job' ORDER BY source_id",(row['id'],))]
    reviewed=any(json.loads(r[0]).get('decisions') for r in connection.execute("SELECT evidence FROM canonical_crosswalk WHERE canonical_id=? AND kind='job'",(row['id'],)))
    return {'id':row['id'],'provider_id':row['provider_id'],'property_id':row['property_id'],'trade':services[0]['trade_code'] if services else 'unknown','service':services[0]['service_code'] if services else 'unknown','services':services,'status':row['lifecycle'],'lifecycle':row['lifecycle'],'completed_at':sorted({c['completed_at_utc'] for c in completion if c['completed_at_utc']}),'service_completions':[{k:c[k] for k in ('service_date','service_date_state','service_date_basis','completed_at_state','evidence_basis')} for c in completion],'completed_visits':len({c['visit_id'] for c in completion if c['visit_id']}),'uncertain_dates':any(c['service_date_state']!='known' for c in completion),'reviewed':reviewed,'evidence_refs':refs,'completion_precision':'status_confirmed_scheduled_date' if any(c['service_date_basis']=='completed_job_schedule' for c in completion) else 'completion_timestamp' if completion and all(c['service_date_basis']=='completion_timestamp' for c in completion) else 'completed_visit_schedule' if completion and all(c['service_date_basis']=='completed_visit_schedule' for c in completion) else 'mixed_or_unknown'}


def property_history(database: Path,address: Any) -> dict[str,Any]:
    with connect_readonly(database) as connection:
        target=_address(connection,address)
        matches=[r[0] for r in connection.execute("SELECT id FROM canonical_properties WHERE house_number=? AND street=? AND coalesce(unit,'')=? AND city=? AND state=? AND coalesce(postal_code,'')=?",target.key or (None,)*6)]
        slots=','.join('?' for _ in matches) or 'NULL'
        rows=records(connection,f'SELECT * FROM canonical_jobs WHERE property_id IN ({slots}) ORDER BY id',matches)
        jobs=[_job(connection,r) for r in rows]
        complete=[j for j in jobs if any(c['service_date_state']=='known' for c in j['service_completions'])]
        return _envelope(connection,{'property_ids':matches,'jobs':complete,'other_or_uncertain_jobs':[j for j in jobs if j not in complete],'distinct_jobs':len(complete),'completed_visits':sum(j['completed_visits'] for j in complete),'observed_jobs':len(jobs)})


def history_radius(database: Path,address: Any,radius_miles: float=.5,start: str=START,end: str=END) -> dict[str,Any]:
    start,end=str(instant(start)),str(instant(end))
    if not 0<radius_miles<=10 or start>=end:
        raise ValueError('invalid radius or time window')
    boundaries=[datetime.fromisoformat(t).astimezone(ZoneInfo('America/Chicago')) for t in (start,end)]
    if any(t.hour or t.minute or t.second or t.microsecond for t in boundaries):
        raise ValueError('history windows require America/Chicago midnight boundaries because some service dates have day precision')
    with connect_readonly(database) as connection:
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
            groups.setdefault((job['provider_id'],job['trade_code']),[]).append(job)
        results=[]
        for (pid,trade),jobs in sorted(groups.items()):
            ids=[j['id'] for j in jobs]; slots=','.join('?' for _ in ids)
            refs=[r[0] for r in connection.execute(f"SELECT source_id FROM canonical_crosswalk WHERE kind='job' AND canonical_id IN ({slots}) ORDER BY source_id",ids)]
            count=connection.execute(f"SELECT count(DISTINCT visit_id) FROM service_completions WHERE job_id IN ({slots}) AND service_date_state='known' AND ((completed_at_utc>=? AND completed_at_utc<?) OR (completed_at_utc IS NULL AND service_date>=? AND service_date<?))",[*ids,start,end,date_start,local_date(end)]).fetchone()[0]
            results.append({'provider_id':pid,'business_name':jobs[0]['display_name'],'trade':trade,'distinct_jobs':len(ids),'completed_visits':count,'evidence_refs':refs,'maximum_distance_miles':max(nearby[j['property_id']] for j in jobs)})
        return _envelope(connection,results)


def block_schedule(database: Path,address: Any,start: str='2026-11-02T06:00:00+00:00',end: str='2026-11-16T06:00:00+00:00') -> dict[str,Any]:
    start,end=str(instant(start)),str(instant(end))
    if start>=end:
        raise ValueError('invalid time window')
    with connect_readonly(database) as connection:
        target=_address(connection,address)
        if target.number is None:
            raise ValueError('block needs a house number')
        clause='p.house_number BETWEEN ? AND ? AND p.street=? AND p.city=? AND p.state=?'
        args=[target.number//100*100,target.number//100*100+99,target.street,target.city,target.state]
        result=records(connection,f"SELECT v.id AS visit_id,coalesce(j.provider_id,e.provider_id) AS provider_id,coalesce(j.property_id,e.property_id) AS property_id,v.job_id,v.estimate_id,v.appointment_kind,v.scheduled_start_utc AS start_utc,v.scheduled_end_utc AS end_utc,v.scheduling_state AS status FROM canonical_visits v LEFT JOIN canonical_jobs j ON j.id=v.job_id LEFT JOIN canonical_estimates e ON e.id=v.estimate_id JOIN canonical_properties p ON p.id=coalesce(j.property_id,e.property_id) WHERE {clause} AND v.scheduled_start_utc<? AND v.scheduled_end_utc>? AND v.scheduling_state NOT IN ('cancelled','completed','superseded') ORDER BY v.scheduled_start_utc,v.id",[*args,end,start])
        for row in result:
            row['evidence_refs']=[r[0] for r in connection.execute("SELECT source_id FROM canonical_crosswalk WHERE kind='visit' AND canonical_id=?",(row['visit_id'],))]
        response=_envelope(connection,result)
        uncertain=records(connection,f"SELECT j.* FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id WHERE {clause} AND j.lifecycle='unknown'",args)
        response['uncertain_candidates']=[_job(connection,j) for j in uncertain]
        return response


def provider_summary(database: Path,provider_id: str) -> dict[str,Any]:
    with connect_readonly(database) as connection:
        from .registry import resolve_identity
        resolved=resolve_identity(connection,provider_id,'provider')
        if resolved['status']=='ambiguous':
            return _envelope(connection,{'identity_status':'ambiguous','requested_id':provider_id,'candidate_ids':resolved['ids']})
        if resolved['status']=='resolved':
            provider_id=cast(list[str],resolved['ids'])[0]
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
        return _envelope(connection,{'provider_id':provider_id,'business_name':provider[0],'service_zips':zips,'observed_service_zips':observed,'history':history,'uncertain_date_history':uncertain_history,'trades':[r[0] for r in connection.execute('SELECT trade_code FROM provider_trades WHERE provider_id=?',(provider_id,))],'distinct_jobs':len(rows),'completed_distinct_jobs':len(history),'completed_visits':sum(j['completed_visits'] for j in history),'source_count':len(refs),'evidence_refs':refs,'openings':None,'opening_status':'not_implemented_until_P3'})

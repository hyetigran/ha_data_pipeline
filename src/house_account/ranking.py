from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from statistics import median

from . import privacy
from .availability import envelope, openings
from .queries import records
from .storage import connect_readonly
from .time_policy import REFERENCE, WEEK_END, ZONE, Interval, request_window


def candidates(connection: sqlite3.Connection, postal: str, trade: str, service: str | None,
               window: Interval, duration: int | None, require_history: bool = False) -> tuple[list[dict],list[dict]]:
    if not re.fullmatch(r'\d{5}',postal) or trade not in {r[0] for r in connection.execute('SELECT DISTINCT trade_code FROM provider_trades')}:
        raise ValueError('supported trade and five-digit postal code required')
    result, excluded = [], []
    for pid,name in connection.execute('SELECT id,display_name FROM canonical_providers ORDER BY id'):
        reasons = []
        trades = {r[0] for r in connection.execute('SELECT trade_code FROM provider_trades WHERE provider_id=?',(pid,))}
        exclusions = {r[0] for r in connection.execute('SELECT trade_code FROM provider_exclusions WHERE provider_id=?',(pid,))}
        if trade not in trades or trade in exclusions:
            reasons.append('service_capability_absent_or_excluded')
        historical = records(connection,"SELECT DISTINCT j.id,p.postal_code,v.scheduled_start_utc,v.scheduled_end_utc,c.visit_id FROM canonical_jobs j JOIN job_services s ON s.job_id=j.id JOIN completion_services cs ON cs.job_service_id=s.id JOIN service_completions c ON c.id=cs.completion_id LEFT JOIN canonical_properties p ON p.id=j.property_id LEFT JOIN canonical_visits v ON v.id=c.visit_id WHERE j.provider_id=? AND s.trade_code=? AND (? IS NULL OR s.service_code=?) AND c.service_date_state='known' AND c.service_date<? AND (c.completed_at_utc IS NULL OR c.completed_at_utc<?)",(pid,trade,service,service,window.start.astimezone(ZONE).date().isoformat(),window.start.isoformat()))
        jobs = {h['id'] for h in historical}
        observed = connection.execute("SELECT 1 FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id JOIN service_completions c ON c.job_id=j.id WHERE j.provider_id=? AND p.postal_code=? AND c.service_date_state='known' AND c.service_date<? AND (c.completed_at_utc IS NULL OR c.completed_at_utc<?) LIMIT 1",(pid,postal,window.start.astimezone(ZONE).date().isoformat(),window.start.isoformat())).fetchone() is not None
        declared = connection.execute('SELECT 1 FROM provider_declared_service_areas WHERE provider_id=? AND postal_code=?',(pid,postal)).fetchone() is not None
        if not observed and not declared:
            reasons.append('area_evidence_absent')
        if require_history and not any(h['postal_code']==postal for h in historical):
            reasons.append('completed_work_in_postal_code_absent')
        visits = {h['visit_id']:h for h in historical if h['visit_id'] and h['scheduled_start_utc'] and h['scheduled_end_utc']}
        durations = []
        for h in visits.values():
            attributed = {r[0] for r in connection.execute("SELECT DISTINCT s.service_code FROM service_completions c JOIN completion_services cs ON cs.completion_id=c.id JOIN job_services s ON s.id=cs.job_service_id WHERE c.visit_id=?",(h['visit_id'],))}
            if service is not None and attributed != {service}:
                continue
            minutes = (datetime.fromisoformat(h['scheduled_end_utc'])-datetime.fromisoformat(h['scheduled_start_utc'])).total_seconds()/60
            if 0<minutes<=1440:
                durations.append(minutes)
        if duration is not None:
            minutes,basis = duration,'explicit_request'
        elif len(durations)>=3:
            minutes,basis = int(median(durations)+.999),'median_scheduled_duration_of_single_service_completed_visits'
        else:
            minutes,basis = 240,'disclosed_four_hour_demo_assumption'
        if reasons:
            excluded.append({'provider_id':pid,'business_name':name,'reasons':reasons})
            continue
        schedule = openings(connection,pid,window,minutes,3)
        if not schedule['openings']:
            excluded.append({'provider_id':pid,'business_name':name,'reasons':['availability_unknown' if schedule['status']=='unknown' else 'no_sufficient_defensible_opening'],'availability':schedule,'duration':{'minutes':minutes,'basis':basis,'historical_visit_sample':len(durations)}})
            continue
        first = datetime.fromisoformat(schedule['openings'][0]['start_utc'])
        score = {'relevant_completed_work':min(10,len(jobs))*4,
                 'area_evidence':20 if observed and declared else 15 if observed else 10,
                 'opening_fit':round(25*max(0,1-(first-window.start).total_seconds()/(window.end-window.start).total_seconds()),2),
                 'confidence':round(15*schedule['confidence']['score']/100,2)}
        result.append({'provider_id':pid,'business_name':name,'eligible':True,'availability':schedule,
                       'duration':{'minutes':minutes,'basis':basis,'historical_visit_sample':len(durations)},
                       'completed_relevant_jobs':len(jobs),'completed_job_refs':sorted(jobs),
                       'area_evidence':{'declared':declared,'completed_work':observed},
                       'score_breakdown':score,'score':round(sum(score.values()),2)})
    result.sort(key=lambda item:(-item['score'],item['provider_id']))
    return result,excluded


def recommend_providers(database: Path, postal_code: str, service: str = 'water_heater', start: str = REFERENCE,
                        end: str = WEEK_END, duration_minutes: int | None = None, limit: int = 10) -> dict:
    if service not in privacy.SERVICES:
        raise ValueError('unsupported service')
    window = request_window(start,end,240 if duration_minutes is None else duration_minutes)
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=100:
        raise ValueError('limit must be 1 through 100')
    trade = privacy.TRADES.get(service, service)
    with connect_readonly(database) as connection:
        eligible,excluded = candidates(connection,postal_code,trade,service,window,duration_minutes)
        return envelope(connection,{'providers':eligible[:limit],'excluded':excluded,'total':len(eligible),'truncated':len(eligible)>limit,
                                   'ranking_policy':{'completed_work':'4 per distinct relevant completed job, capped at 40', 'area':'20 both declared and completed; 15 completed; 10 declared', 'opening_fit':'25 times fraction of horizon remaining at first opening', 'confidence':'15 times ordinal confidence divided by 100', 'tie_break':'canonical provider ID'}})

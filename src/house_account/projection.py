from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from . import privacy
from .addresses import words
from .model import canonical_json, digest, instant
from .schema import create_canonical


def insert(connection: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
    connection.execute(f'INSERT INTO {table}({",".join(values)}) VALUES({",".join("?" for _ in values)})', list(values.values()))


def local_date(value: str | None) -> str | None:
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(ZoneInfo('America/Chicago')).date().isoformat()


def temporal(value: str | None, raw: Any, disputed: bool = False) -> tuple[str | None, str | None, str, str]:
    if disputed:
        return None, None, 'disputed', 'unknown'
    if value:
        return value, local_date(value), 'known', 'instant'
    if raw:
        try:
            date = datetime.fromisoformat(str(raw)).date().isoformat()
            try:
                selected = instant(raw)
            except ValueError:
                return None, date, 'ambiguous', 'date'
            if selected:
                return selected, local_date(selected), 'known', 'instant'
        except ValueError:
            pass
    return None, None, 'missing', 'unknown'


def optional_instant(value: Any) -> str | None:
    try:
        return instant(value)
    except (ValueError,TypeError):
        return None


def lifecycle(source: str, status: str | None, normalized: str | None) -> str:
    status = (status or '').lower().replace('_', ' ')
    if source == 'jobber':
        return {'active':'active','upcoming':'open','today':'open','unscheduled':'open'}.get(status, 'unknown')
    if source == 'workiz' and status == 'done pending approval':
        return 'pending_approval'
    return {'completed':'completed','cancelled':'cancelled','scheduled':'open','pending':'open','in_progress':'active','active':'active'}.get(normalized or '', 'unknown')


def project(connection: sqlite3.Connection, sources: dict, providers: dict, properties: dict,
            jobs: dict, visits: dict, addresses: dict, provider_map: dict, property_map: dict,
            job_map: dict, proposals: list, events: list, stale: list, decisions: dict) -> dict:
    from .identity import rows
    from .registry import assign_ids
    from .review import RULE

    create_canonical(connection)
    insert(connection, 'reconciliation_metadata', {'ledger_revision':events[-1]['decision_id'] if events else '', 'stale_decisions':canonical_json(stale),'rule_version':RULE})
    for item in proposals:
        insert(connection,'reconciliation_proposals',{'id':item.proposal_id,'document':item.model_dump_json()})
    trades = {'handyman','plumbing','hvac','electrical','cleaning','landscaping','pest_control','roofing','gutters','painting','appliance_repair','garage_doors','unknown'}
    categories = {**{k:k.replace('_',' ').capitalize() for k in privacy.SERVICES},'unknown':'Unclassified service'}
    for code in sorted(trades):
        insert(connection,'trades',{'code':code,'label':code.replace('_',' ').capitalize()})
    for code,label in categories.items():
        insert(connection,'service_categories',{'code':code,'label':label})
        allowed = trades if code == 'unknown' else {privacy.TRADES.get(code,code)}
        for trade in allowed:
            insert(connection,'service_category_trades',{'service_code':code,'trade_code':trade})

    events_by_id = {event['decision_id']:event for event in events}

    def lineage(entity: str, fields: list[str], refs: list[str], rule: str) -> None:
        entity_kind = connection.execute('SELECT kind FROM identity_registry WHERE id=?',(entity,)).fetchone()
        kind = entity_kind[0] if entity_kind else 'job_service' if connection.execute('SELECT 1 FROM job_services WHERE id=?',(entity,)).fetchone() else 'completion' if connection.execute('SELECT 1 FROM service_completions WHERE id=?',(entity,)).fetchone() else 'estimate_service'
        connection.execute('INSERT OR IGNORE INTO lineage_entities VALUES(?,?)',(entity,kind))
        for ref in refs:
            related = [ref]
            if ref in visits and visits[ref].get('job_id'):
                related.append(visits[ref]['job_id'])
            for field in fields:
                selected_decision = None
                for target in related:
                    for decision_id in decisions.get(target,[]):
                        action = events_by_id[decision_id]['proposal']['proposed_action']
                        expected = {'scheduled_start':'start_utc','scheduled_end':'end_utc','service_date':'start_utc','address':'address','property_id':'address'}.get(field)
                        if action['operation']=='merge' or action.get('field')==expected:
                            selected_decision = decision_id
                connection.execute('INSERT OR IGNORE INTO field_lineage VALUES(?,?,?,?,?)',(entity,field,ref,rule,selected_decision))

    estimates = rows(connection,'estimates')
    estimate_map = assign_ids(connection,'estimate',{k:k for k in estimates})
    visit_map = assign_ids(connection,'visit',{k:k for k in visits})
    for kind,mapping in [('provider',provider_map),('property',property_map),('job',job_map),('estimate',estimate_map),('visit',visit_map)]:
        for key,cid in mapping.items():
            insert(connection,'canonical_crosswalk',{'source_id':key,'kind':kind,'canonical_id':cid,'rule':'reviewed_or_exact_'+kind,'evidence':canonical_json({'source_refs':[key],'content_hashes':{key:sources[key]['content_hash']},'decisions':decisions.get(key,[])})})

    def grouped(mapping: dict) -> dict[str,list[str]]:
        result: dict[str,list[str]] = {}
        for source,cid in sorted(mapping.items()):
            result.setdefault(cid,[]).append(source)
        return result

    provider_trades: dict[str,list[str]] = {}
    for cid,members in grouped(provider_map).items():
        ordered = sorted(members,key=lambda k:(sources[k]['source']!='profiles',k))
        profiles = [sources[k]['raw'] for k in ordered if sources[k]['source']=='profiles']
        insert(connection,'canonical_providers',{'id':cid,'display_name':providers[ordered[0]]['display_name']})
        seen = set()
        for member in members:
            label = providers[member]['display_name']
            normalized = words(label)
            if normalized not in seen:
                insert(connection,'provider_aliases',{'id':digest([cid,normalized]),'provider_id':cid,'name':label,'normalized_name':normalized})
                seen.add(normalized)
        capabilities = {privacy.trade(t) for profile in profiles for t in profile.get('trades',[])} | {privacy.trade(providers[k].get('trade')) for k in members if providers[k].get('trade')}
        provider_trades[cid] = sorted(capabilities & trades)
        for code in provider_trades[cid]:
            insert(connection,'provider_trades',{'provider_id':cid,'trade_code':code})
        for code in {privacy.trade(t) for profile in profiles for t in profile.get('does_not_do',[])} & trades:
            insert(connection,'provider_exclusions',{'provider_id':cid,'trade_code':code})
        for postal in {z for profile in profiles for z in profile.get('service_zips',[])}:
            insert(connection,'provider_declared_service_areas',{'provider_id':cid,'postal_code':postal})
        lineage(cid,['display_name','capabilities'],members,'business_assertion')
    for cid,members in grouped(property_map).items():
        address = addresses[members[0]]
        insert(connection,'canonical_properties',{'id':cid,'house_number':address.number,'street':address.street or None,'unit':address.unit or None,'unit_state':'known' if address.unit else 'unknown','city':address.city or None,'state':address.state or None,'postal_code':address.postal_code or None,'latitude':address.latitude,'longitude':address.longitude,'geocode_precision':address.precision,'reference_segment_id':address.segment_key})
        lineage(cid,['address','unit'],members,'normalized_address')
        if address.segment_key:
            lineage(cid,['postal_code','city','state','coordinates'],[address.segment_key],'unique_street_segment')

    def service_rows(kind: str, cid: str, members: list[str], data: dict, pid: str) -> list[str]:
        mapped = set()
        for member in members:
            raw_service = data[member].get('service')
            for category in privacy.service_codes(raw_service,provider_trades.get(pid,[])):
                if category == 'other':
                    category = 'unknown'
                trade = privacy.TRADES.get(category,category)
                if category == 'unknown':
                    trade = next(iter(provider_trades.get(pid,[])),'unknown')
                mapped.add((trade,category))
        result = []
        for trade,category in sorted(mapped):
            sid = digest([kind,cid,trade,category])
            insert(connection,kind+'_services',{'id':sid,kind+'_id':cid,'trade_code':trade,'service_code':category,'safe_description':categories[category],'classification_state':'unmapped' if category=='unknown' else 'mapped'})
            lineage(sid,['service_code'],members,'controlled_service_vocabulary')
            if category=='unknown':
                connection.executemany('INSERT INTO issues VALUES(?,?,?,?)',[(m,'unmapped_service','service','No supported controlled service classification') for m in members])
            result.append(sid)
        return result

    job_services = {}
    for kind,data,mapping in [('job',jobs,job_map),('estimate',estimates,estimate_map)]:
        for cid,members in grouped(mapping).items():
            row = data[members[0]]
            pid = provider_map[row['provider_id']]
            props = {property_map.get(data[m].get('property_id') or m) for m in members}
            prop = next(iter(props)) if len(props)==1 else None
            values: dict[str,Any] = {'id':cid,'provider_id':pid,'property_id':prop,'property_link_state':'resolved' if prop else 'conflicting' if len(props)>1 else 'unresolved' if any(data[m].get('property_id') for m in members) else 'missing'}
            if kind == 'job':
                states = {lifecycle(sources[m]['source'],data[m]['source_status'],data[m]['status']) for m in members}
                amounts = {(data[m]['amount_minor'],data[m]['currency']) for m in members if data[m]['amount_minor'] is not None}
                amount,currency = next(iter(amounts)) if len(amounts)==1 else (None,None)
                values.update(lifecycle=next(iter(states)) if len(states)==1 else 'unknown',amount_minor=amount,currency=currency,amount_state='known' if amount is not None and currency else 'disputed' if len(amounts)>1 else 'missing')
                if values['amount_state']!='known':
                    values['amount_minor']=None
            else:
                state=row['status']
                values['estimate_state']=state if state in {'open','scheduled','in_progress','completed','cancelled'} else 'unknown'
            insert(connection,'canonical_'+kind+'s',values)
            services = service_rows(kind,cid,members,data,pid)
            if kind=='job':
                job_services[cid]=services
            lineage(cid,(['lifecycle','property_id','amount_minor','currency'] if kind=='job' else ['estimate_state','property_id']),members,'source_specific_selection')

    selected_visits = {}
    selected_by_job: dict[str,dict] = {}
    for key,row in visits.items():
        raw = sources[key]['raw']
        source = sources[key]['source']
        parent = row.get('job_id')
        status_time = optional_instant(sources[parent]['raw'].get('LastStatusUpdate')) if source=='workiz' and parent in sources else None
        disputed = bool(source=='workiz' and parent in jobs and row['start_utc'] and status_time and row['start_utc']>status_time and jobs[parent]['status']=='completed' )
        values = {'id':visit_map[key],'job_id':job_map.get(parent),'estimate_id':estimate_map.get(row.get('estimate_id')),'appointment_kind':row['appointment_kind'],'scheduling_state':row['status'] if row['status'] in {'scheduled','in_progress','completed','cancelled','overdue','unscheduled','superseded'} else 'unknown','timezone_name':'America/Chicago'}
        for end,raw_keys in [('start',('startAt','JobDateTime','start_time','scheduled_start')),('end',('endAt','JobEndDateTime','end_time','scheduled_end'))]:
            raw_time=next((raw.get(k) for k in raw_keys if raw.get(k)),None)
            values.update(zip([f'scheduled_{end}_{suffix}' for suffix in ('utc','local_date','state','precision')],temporal(row[end+'_utc'],raw_time,disputed),strict=True))
        insert(connection,'canonical_visits',values)
        selected_visits[key]=values
        if parent:
            selected_by_job.setdefault(parent,values)
        lineage(visit_map[key],['scheduled_start','scheduled_end','scheduling_state'],[key],'source_time_interpretation')

    def complete(job: str, visit: str | None, ref: str, basis: str, stamp: str | None, date: str | None, state: str, date_basis: str) -> None:
        candidates = list(connection.execute('SELECT id FROM service_completions WHERE job_id=? AND completed_at_utc=? AND (? IS NULL OR visit_id=?)',(job,stamp,visit,visit))) if stamp else []
        existing = candidates[0] if len(candidates)==1 else None
        cid=existing[0] if existing else digest(['completion',job,visit or stamp or date,basis])
        if connection.execute('SELECT 1 FROM service_completions WHERE id=?',(cid,)).fetchone():
            connection.execute('INSERT OR IGNORE INTO completion_evidence VALUES(?,?)',(cid,ref))
            lineage(cid,['service_date','completed_at'],[ref],date_basis)
            return
        insert(connection,'service_completions',{'id':cid,'job_id':job,'visit_id':visit,'evidence_basis':basis,'service_date':date,'service_date_state':state,'service_date_basis':date_basis,'completed_at_utc':stamp,'completed_at_state':'known' if stamp else 'missing'})
        insert(connection,'completion_evidence',{'completion_id':cid,'source_id':ref})
        lineage(cid,['service_date','completed_at'],[ref],date_basis)
        if len(job_services[job])==1:
            insert(connection,'completion_services',{'completion_id':cid,'job_service_id':job_services[job][0]})

    completed_jobs=set()
    for ref,row in visits.items():
        if not row.get('job_id') or row['status']!='completed' or sources[ref]['source']!='jobber':
            continue
        job=job_map[row['job_id']]
        raw=sources[ref]['raw']
        stamp=instant(raw.get('completedAt'))
        selected=selected_visits[ref]
        date=local_date(stamp) if stamp else selected['scheduled_start_local_date']
        state='known' if stamp else selected['scheduled_start_state']
        complete(job,visit_map[ref],ref,'completed_visit',stamp,date,state,'completion_timestamp' if stamp else 'completed_visit_schedule')
        completed_jobs.add(job)
    for job,members in grouped(job_map).items():
        for member in members:
            source=sources[member]['source']; raw=sources[member]['raw']; row=jobs[member]
            if source=='housecall_pro' and row['status']=='completed':
                stamp=instant(raw.get('work_timestamps',{}).get('completed_at'))
                complete(job,None,member,'job_completion_timestamp' if stamp else 'job_completed_status',stamp,local_date(stamp),'known' if stamp else 'missing','completion_timestamp' if stamp else 'unknown')
            elif source=='workiz' and (row['source_status'] or '').lower()=='done':
                schedule=selected_by_job.get(member)
                date=schedule['scheduled_start_local_date'] if schedule else None
                state=schedule['scheduled_start_state'] if schedule else 'missing'
                complete(job,None,member,'job_completed_status',None,date,state,'completed_job_schedule' if schedule else 'unknown')
    return {'providers':len(set(provider_map.values())),'properties':len(set(property_map.values())),'jobs':len(set(job_map.values())),'visits':len(visits),'estimates':len(estimates),'proposals':len(proposals),'stale_decisions':len(stale)}

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal, cast

from . import privacy
from .addresses import normalize, words
from .model import digest, instant
from .review import Action, current_decisions, proposal, read_ledger


class Groups:
    def __init__(self, keys: list[str]):
        self.parent = {key:key for key in keys}

    def find(self, key: str) -> str:
        if self.parent[key] != key:
            self.parent[key] = self.find(self.parent[key])
        return self.parent[key]

    def merge(self, keys: list[str]) -> None:
        roots = sorted({self.find(key) for key in keys})
        for root in roots[1:]:
            self.parent[root] = roots[0]

    def ids(self, kind: str) -> dict[str,str]:
        groups: dict[str,list[str]] = defaultdict(list)
        for key in sorted(self.parent):
            groups[self.find(key)].append(key)
        return {key:digest([kind,members]) for members in groups.values() for key in members}


def rows(connection: sqlite3.Connection, table: str) -> dict[str,dict[str,Any]]:
    cursor = connection.execute(f'SELECT * FROM {table}')
    names = [column[0] for column in cursor.description]
    return {row[0]:dict(zip(names,row,strict=True)) for row in cursor}


def phone(raw: dict[str,Any]) -> str:
    number = re.sub(r'\D','',str(raw.get('phone',raw.get('phone_number',''))))
    return number[-10:] if len(number) in (10,11) else ''


def reconcile(connection: sqlite3.Connection, ledger: Path) -> dict[str,Any]:
    sources = rows(connection,'source_records')
    for row in sources.values():
        row['raw'] = json.loads(row['raw_json'])
    providers = rows(connection,'providers')
    properties = rows(connection,'properties')
    jobs = rows(connection,'jobs')
    customers = rows(connection,'customers')
    visits = rows(connection,'visits')
    segments = [dict(id=row['id'],**json.loads(row['attributes_json'])) for row in rows(connection,'street_segments').values()]
    pg = Groups(list(providers))
    links: list[tuple[str,str,str]] = []
    proposals = []
    by_phone: dict[str,list[str]] = defaultdict(list)
    for key in providers:
        number = phone(sources[key]['raw'])
        if number:
            by_phone[number].append(key)
    provider_trades: dict[str,set[str]] = defaultdict(set)
    provider_evidence = {key:{key} for key in providers}
    for key,row in providers.items():
        raw = sources[key]['raw']
        provider_trades[key].update(privacy.trade(t) for t in raw.get('trades',[]))
        if row['trade']:
            provider_trades[key].add(privacy.trade(row['trade']))
    for key,job in jobs.items():
        category = privacy.service(job['service'])
        if category != 'other':
            provider_trades[job['provider_id']].add(privacy.TRADES.get(category,category))
            provider_evidence[job['provider_id']].add(key)
    for members in by_phone.values():
        for index,left in enumerate(members):
            for right in members[index+1:]:
                if provider_trades[left] & provider_trades[right]:
                    pg.merge([left,right])
                    links.append((left,right,'exact_business_phone_and_trade'))
                else:
                    targets = sorted([left,right])
                    proposals.append(proposal(Action(operation='merge',entity='provider',targets=targets),
                                              {t:sources[t]['content_hash'] for t in targets},['Shared business phone'],['No corroborating trade evidence']))
    for key,row in providers.items():
        src = sources[key]
        if src['source'] not in {'calendars','spreadsheet'}:
            continue
        filename = src['account'].removesuffix('_google_calendar')
        token = re.sub(r'[^a-z0-9]','',filename.lower())
        candidates = [other for other,p in providers.items() if sources[other]['source'] not in {'calendars','spreadsheet'} and re.sub(r'[^a-z0-9]','',str(p['display_name']).lower()).startswith(token)]
        if candidates:
            targets = sorted([key,candidates[0]])
            proposals.append(proposal(Action(operation='merge',entity='provider',targets=targets),
                                      {t:sources[t]['content_hash'] for t in targets},['Similar provider label without independent identity proof'],['No shared phone or explicit source identifier']))
    names: dict[str,list[str]] = defaultdict(list)
    for key,row in providers.items():
        names[words(row['display_name'])].append(key)
    for members in names.values():
        roots = {pg.find(k) for k in members}
        if len(roots)>1:
            targets = sorted(members)
            proposals.append(proposal(Action(operation='merge',entity='provider',targets=targets),
                                      {t:sources[t]['content_hash'] for t in targets},['Exact normalized name'],['Name alone does not establish identity']))
    addresses = {key:normalize(json.loads(row['attributes_json']).get('address',{}),segments) for key,row in properties.items()}
    for key,row in jobs.items():
        if sources[key]['source']=='spreadsheet':
            addresses[key] = normalize(json.loads(row['attributes_json'])['address_raw'],segments)
    address_evidence = {key:{key} | ({address.segment_key} if address.segment_key else set())
                        for key,address in addresses.items()}
    address_candidates: dict[tuple[Any,...],list[str]] = defaultdict(list)
    for key,address in addresses.items():
        if address.number is not None:
            address_candidates[(address.number,address.street,address.unit)].append(key)
    for members in address_candidates.values():
        distinct = {addresses[k].key for k in members}
        if len(distinct)>1:
            representatives = {addresses[k].key:k for k in sorted(members)}
            targets = sorted(representatives.values())
            candidate_refs = set().union(*(address_evidence[t] for t in targets))
            proposals.append(proposal(Action(operation='merge',entity='property',targets=targets),
                                      {t:sources[t]['content_hash'] for t in sorted(candidate_refs)},['Same house number, street and unit'],['Conflicting or missing locality/postal assertions'], 'low'))
    for key,row in jobs.items():
        raw = sources[key]['raw']
        if sources[key]['source']=='workiz' and sources[key]['source_key']=='J8OMKP':
            linked = sorted(k for k,v in visits.items() if v['job_id']==key)
            if linked and raw.get('JobDateTime','').startswith('2026-') and str(raw.get('LastStatusUpdate','')).startswith('2025-'):
                hashes = {k:sources[k]['content_hash'] for k in [key,*linked]}
                for field,rawfield in [('start_utc','JobDateTime'),('end_utc','JobEndDateTime')]:
                    old = visits[linked[0]][field]
                    new = instant(str(raw[rawfield]).replace('2026-','2025-',1))
                    proposals.append(proposal(Action(operation='correct',entity='job',targets=[key],field=cast(Literal["start_utc","end_utc"],field),original=old,proposed=new),hashes,
                                              ['Completed status and status update in 2025 conflict with a 2026 scheduled interval'],['Inferred year correction requires human approval'],'high'))
        if sources[key]['source']=='spreadsheet' and words(raw.get('Address',''))=='5832 belmont ave':
            contact = phone({'phone':raw.get('Phone','')})
            label = words(raw.get('Customer',''))
            evidence_keys = [k for k in jobs if sources[k]['source']=='spreadsheet'
                             and sources[k]['account']==sources[key]['account']
                             and words(sources[k]['raw'].get('Address',''))=='5823 belmont ave'
                             and label and words(sources[k]['raw'].get('Customer',''))==label
                             and contact and phone({'phone':sources[k]['raw'].get('Phone','')})==contact]
            corroborating = []
            for prop_ref,record in properties.items():
                customer = record['customer_id']
                if sources[prop_ref]['source']!='jobber' or customer not in customers:
                    continue
                address = json.loads(record['attributes_json']).get('address',{})
                contacts = sources[customer]['raw'].get('phones',[])
                if (words(address.get('street1',''))=='5823 belmont ave' and contact
                        and any(phone({'phone':p.get('number','')})==contact for p in contacts)):
                    corroborating.append((prop_ref,customer))
            accounts = {sources[prop_ref]['account'] for prop_ref,_ in corroborating}
            if evidence_keys and len(accounts)>=2:
                refs = sorted({key,*evidence_keys,*(ref for pair in corroborating for ref in pair)})
                proposals.append(proposal(Action(operation='correct',entity='job',targets=[key],field='address',original=raw['Address'],proposed=re.sub('5832','5823',raw['Address'],count=1)),
                                          {k:sources[k]['content_hash'] for k in refs},
                                          ['Repeated 5823 address with matching normalized customer label and phone in the same spreadsheet account',
                                           'Matching normalized contact links the 5823 property in two independent Jobber accounts'],
                                          ['House-number transposition is inferred; a contact may own multiple properties; original retained until review'],'high'))
    provider_group_evidence: dict[str,set[str]] = defaultdict(set)
    for key,provider_refs in provider_evidence.items():
        provider_group_evidence[pg.find(key)].update(provider_refs)
    visit_evidence: dict[str,set[str]] = defaultdict(set)
    starts_by_job: dict[str,list[str]] = defaultdict(list)
    for key,visit in visits.items():
        if visit['job_id']:
            visit_evidence[visit['job_id']].add(key)
        if visit['job_id'] and visit['start_utc']:
            starts_by_job[visit['job_id']].append(visit['start_utc'])
    job_candidates: dict[tuple[Any,...],list[str]] = defaultdict(list)
    for key,row in jobs.items():
        job_address = addresses.get(row['property_id'] or key)
        if not job_address or not job_address.key:
            continue
        starts = sorted(starts_by_job[key])
        if starts:
            job_candidates[(pg.find(row['provider_id']),job_address.key,privacy.service(row['service']),starts[0])].append(key)
    for members in job_candidates.values():
        if len(members)>1 and len({sources[k]['source'] for k in members})>1:
            targets = sorted(members)
            candidate_refs = set(targets)
            for key in targets:
                job = jobs[key]
                candidate_refs.update(provider_group_evidence[pg.find(job['provider_id'])])
                candidate_refs.update(address_evidence[job['property_id'] or key])
                candidate_refs.update(visit_evidence[key])
            proposals.append(proposal(Action(operation='merge',entity='job',targets=targets),
                                      {t:sources[t]['content_hash'] for t in sorted(candidate_refs)},['Same corroborated provider, exact unit address, service category and start'],['No shared immutable cross-system job identifier; distinct work may coincide']))
    proposals = list({p.proposal_id:p for p in proposals}.values())
    for candidate in proposals:
        candidate.observations = {ref:sources[ref]['raw'] for ref in candidate.source_refs}
    events = read_ledger(ledger)
    approved, stale = current_decisions(proposals,events)
    decision_links: dict[str,list[str]] = defaultdict(list)
    for event in approved:
        action = Action.model_validate(event['proposal']['proposed_action'])
        for key in action.targets:
            decision_links[key].append(event['decision_id'])
        if action.operation=='merge' and action.entity=='provider':
            pg.merge(action.targets)
        elif action.operation=='correct':
            key = action.targets[0]
            if action.field=='address':
                addresses[key] = normalize(action.proposed,segments)
            else:
                for visit in visits.values():
                    if visit['job_id']==key:
                        visit[str(action.field)] = action.proposed
    for visit in visits.values():
        if visit['start_utc'] and visit['end_utc'] and visit['start_utc']>=visit['end_utc']:
            raise ValueError('review creates invalid visit interval')
    property_groups = Groups(list(addresses))
    by_address: dict[Any,list[str]] = defaultdict(list)
    for key,address in addresses.items():
        if address.key:
            by_address[address.key].append(key)
    for members in by_address.values():
        property_groups.merge(members)
    for event in approved:
        action = Action.model_validate(event['proposal']['proposed_action'])
        if action.operation=='merge' and action.entity=='property':
            units = {addresses[k].unit for k in action.targets}
            if len(units)>1:
                raise ValueError('property merge crosses unit identities')
            property_groups.merge(action.targets)
    provider_map, property_map = pg.ids('provider'),property_groups.ids('property')
    job_groups = Groups(list(jobs))
    for event in approved:
        action = Action.model_validate(event['proposal']['proposed_action'])
        if action.operation=='merge' and action.entity=='job':
            signatures = {(provider_map[jobs[k]['provider_id']],property_map.get(jobs[k]['property_id'] or k)) for k in action.targets}
            if len(signatures)!=1:
                raise ValueError('job merge has incompatible provider or property')
            job_groups.merge(action.targets)
    job_map = job_groups.ids('job')
    from .projection import project
    from .registry import assign_ids

    provider_map = assign_ids(connection, 'provider', provider_map)
    property_map = assign_ids(connection, 'property', property_map)
    job_map = assign_ids(connection, 'job', job_map)
    return project(connection, sources, providers, properties, jobs, visits, addresses,
                   provider_map, property_map, job_map, proposals, events, stale, decision_links)

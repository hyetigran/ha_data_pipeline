from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar, Event

from .queries import records
from .storage import connect_readonly
from .time_policy import (
    DEFAULT_END,
    REFERENCE,
    THREE_DAYS,
    ZONE,
    Interval,
    day_interval,
    local_instant,
    request_window,
    subtract,
    union,
)

POLICY = {'capacity': 'one provider-level resource; crew assignments are not verified capacity',
          'travel': 'unmodeled', 'booking': 'candidate openings, not booking promises',
          'confidence': 'ordinal evidence score, not a probability', 'reference': REFERENCE}


@dataclass
class ScheduleEvidence:
    working: list[Interval] = field(default_factory=list)
    busy: list[Interval] = field(default_factory=list)
    unknown: list[Interval] = field(default_factory=list)
    refs: set[str] = field(default_factory=set)
    reasons: set[str] = field(default_factory=set)
    agreement: int = 0
    disagreement: int = 0


def provider_id(connection: sqlite3.Connection, value: str) -> str:
    from .identity import words
    from .registry import resolve_identity
    resolved = resolve_identity(connection, value, 'provider')
    if resolved['status'] == 'ambiguous':
        raise ValueError('provider identity is ambiguous')
    if resolved['status'] == 'resolved':
        return str(cast(list[str], resolved['ids'])[0])
    matches = [r[0] for r in connection.execute('SELECT DISTINCT provider_id FROM provider_aliases WHERE normalized_name=?', (words(value),))]
    if len(matches) != 1:
        raise ValueError('provider must identify exactly one business')
    return str(matches[0])


def envelope(connection: sqlite3.Connection, result: Any) -> dict:
    snapshot = connection.execute('SELECT id,ingested_at FROM snapshot').fetchone()
    return {'results': result, 'snapshot_id': snapshot[0], 'ingested_at': snapshot[1], 'policy': POLICY}


def _uncertain_visit(row: dict, window: Interval) -> Interval | None:
    days = [date.fromisoformat(row[k]) for k in ('scheduled_start_local_date', 'scheduled_end_local_date') if row[k]]
    if not days:
        return window if row['scheduling_state'] in {'scheduled','in_progress'} or any(row[k] in {'ambiguous','disputed'} for k in ('scheduled_start_state','scheduled_end_state')) else None
    return Interval(day_interval(min(days)).start, day_interval(max(days)).end).clip(window)


def calendar_intervals(raw_events: list[dict], window: Interval) -> tuple[list[Interval], set[str]]:
    calendar = Calendar()
    calendar.add('version', '2.0')
    reasons: set[str] = set()
    zones: dict[str,ZoneInfo] = {}
    if len(raw_events)>10000 or sum(len(raw['ical']) for raw in raw_events)>10_000_000:
        raise ValueError('calendar input limit exceeded')
    for raw in raw_events:
        event = Event.from_ical(raw['ical'].replace('\\r\\n', '\r\n'))
        zone = ZoneInfo(raw.get('calendar_timezone') or 'America/Chicago')
        zones[str(event.get('UID', ''))] = zone
        for key in ('DTSTART', 'DTEND', 'RECURRENCE-ID', 'EXDATE', 'RDATE'):
            values = event.get(key)
            if values is None:
                continue
            for value in values if isinstance(values, list) else [values]:
                for stamp in value.dts if hasattr(value, 'dts') else [value]:
                    if isinstance(stamp.dt, datetime) and stamp.dt.tzinfo is None:
                        if key not in {'DTSTART','DTEND'}:
                            local_instant(stamp.dt, zone)
                        stamp.dt = stamp.dt.replace(tzinfo=zone)
        rule = event.get('RRULE')
        if rule and str(rule.get('FREQ', [''])[0]).upper() not in {'DAILY','WEEKLY','MONTHLY','YEARLY'}:
            raise ValueError('unsupported recurrence frequency')
        if rule and any(key in rule for key in ('BYSECOND','BYMINUTE','BYHOUR')):
            raise ValueError('sub-day recurrence expansion is unsupported')
        calendar.add_component(event)
    expanded = recurring_ical_events.of(calendar).between(window.start-timedelta(days=2), window.end+timedelta(days=2))
    if len(expanded) > 10000:
        raise ValueError('recurrence occurrence limit exceeded')
    result = []
    for event in expanded:
        if str(event.get('STATUS', '')).upper() == 'CANCELLED' or str(event.get('TRANSP', 'OPAQUE')).upper() == 'TRANSPARENT':
            continue
        bounds = []
        for key in ('DTSTART', 'DTEND'):
            value = event.decoded(key)
            if isinstance(value, datetime):
                endpoint_zone = value.tzinfo or zones.get(str(event.get('UID', '')), ZONE)
                bounds.append([value.replace(tzinfo=endpoint_zone, fold=fold).astimezone(UTC) for fold in (0,1)])
            else:
                bounds.append([day_interval(value,zones.get(str(event.get('UID', '')), ZONE)).start])
        if min(bounds[0]) >= window.end or max(bounds[1]) <= window.start:
            continue
        endpoints = []
        for key in ('DTSTART', 'DTEND'):
            value = event.decoded(key)
            if isinstance(value, datetime):
                if value.tzinfo is not None and isinstance(value.tzinfo, ZoneInfo):
                    local_instant(value.replace(tzinfo=None), value.tzinfo)
                endpoints.append(local_instant(value))
            else:
                endpoints.append(day_interval(value,zones.get(str(event.get('UID', '')), ZONE)).start)
        interval = Interval(*endpoints).clip(window)
        if interval:
            result.append(interval)
            if str(event.get('STATUS', '')).upper() == 'TENTATIVE':
                reasons.add('tentative_hold_blocks')
    return sorted(result), reasons


def load_evidence(connection: sqlite3.Connection, pid: str, window: Interval) -> ScheduleEvidence:
    evidence = ScheduleEvidence()
    hours = records(connection, "SELECT h.* FROM provider_hour_declarations h JOIN canonical_crosswalk x ON x.source_id=h.provider_id AND x.kind='provider' WHERE x.canonical_id=?", (pid,))
    hour_zones = {h['timezone_name'] for h in hours}
    hour_zone = ZoneInfo(next(iter(hour_zones))) if len(hour_zones)==1 else ZONE
    if len(hour_zones)>1:
        evidence.unknown.append(window)
        evidence.reasons.add('working_timezone_conflict')
    day = window.start.astimezone(hour_zone).date()
    while day < window.end.astimezone(hour_zone).date() + timedelta(days=1):
        local_day = day_interval(day, hour_zone)
        if not local_day.overlaps(window):
            day += timedelta(days=1)
            continue
        declarations = [h for h in hours if h['weekday']==day.weekday() and (not h['effective_from'] or day.isoformat()>=h['effective_from']) and (not h['effective_before'] or day.isoformat()<h['effective_before'])]
        profiles: dict[str,set[tuple]] = {}
        for h in declarations:
            profiles.setdefault(h['source_profile_id'],set()).add((h['local_start'],h['local_end'],h['declaration_state'],h['emergency_only'],h['timezone_name']))
        signatures = {frozenset(spans) for spans in profiles.values()}
        if not declarations or len(signatures)>1 or any(h['declaration_state']=='unknown' or h['emergency_only'] for h in declarations):
            evidence.unknown.append(local_day)
            evidence.reasons.add('hours_unknown_or_conflicting')
        else:
            for h in declarations:
                if h['declaration_state'] != 'known':
                    continue
                try:
                    zone = ZoneInfo(h['timezone_name'])
                    work = Interval(local_instant(datetime.combine(day,time.fromisoformat(h['local_start'])),zone),local_instant(datetime.combine(day,time.fromisoformat(h['local_end'])),zone)).clip(window)
                    if work:
                        evidence.working.append(work)
                except ValueError:
                    evidence.unknown.append(local_day)
                    evidence.reasons.add('working_time_ambiguous')
        evidence.refs.update(h['source_profile_id'] for h in declarations)
        day += timedelta(days=1)
    visits = records(connection, "SELECT v.* FROM canonical_visits v LEFT JOIN canonical_jobs j ON j.id=v.job_id LEFT JOIN canonical_estimates e ON e.id=v.estimate_id WHERE coalesce(j.provider_id,e.provider_id)=? AND v.scheduling_state NOT IN ('cancelled','completed','superseded')", (pid,))
    crm: list[Interval] = []
    for row in visits:
        if row['scheduled_start_state']=='known' and row['scheduled_end_state']=='known' and row['scheduled_start_utc'] and row['scheduled_end_utc']:
            interval = Interval(datetime.fromisoformat(row['scheduled_start_utc']),datetime.fromisoformat(row['scheduled_end_utc'])).clip(window)
            if interval:
                crm.append(interval)
                evidence.refs.add(row['id'])
        else:
            if not row['scheduled_start_local_date'] and not row['scheduled_end_local_date'] and row['scheduling_state'] not in {'scheduled','in_progress'}:
                evidence.reasons.add('undated_backlog_not_a_booking')
            unknown = _uncertain_visit(row, window)
            if unknown:
                evidence.unknown.append(unknown)
                evidence.refs.add(row['id'])
                evidence.reasons.add('appointment_interval_unknown')
    evidence.busy.extend(crm)
    calendars = records(connection, "SELECT r.raw_json,r.account,r.id FROM calendar_blocks b JOIN source_records r ON r.id=b.id JOIN canonical_crosswalk x ON x.source_id=b.provider_id AND x.kind='provider' WHERE x.canonical_id=?", (pid,))
    grouped: dict[str,list[dict]] = {}
    for row in calendars:
        grouped.setdefault(row['account'], []).append(json.loads(row['raw_json']))
        evidence.refs.add(row['id'])
    for events in grouped.values():
        try:
            busy, reasons = calendar_intervals(events, window)
            evidence.busy.extend(busy)
            evidence.reasons.update(reasons)
            evidence.agreement += sum(interval in crm for interval in busy)
            evidence.disagreement += sum(interval not in crm and any(interval.overlaps(v) for v in crm) for interval in busy)
        except (ValueError, KeyError, TypeError, OverflowError):
            evidence.unknown.append(window)
            evidence.reasons.add('calendar_expansion_unknown')
    freshness = [r[0] for r in connection.execute("SELECT DISTINCT r.snapshot_at FROM source_records r JOIN canonical_crosswalk x ON x.source_id=r.id WHERE x.canonical_id=? AND x.kind='provider'",(pid,))]
    if not freshness or any(not stamp or stamp[:10] < REFERENCE[:10] for stamp in freshness):
        evidence.reasons.add('source_freshness_limited')
    spreadsheet = records(connection,"SELECT j.attributes_json,r.id FROM jobs j JOIN source_records r ON r.id=j.id JOIN canonical_crosswalk x ON x.source_id=j.provider_id AND x.kind='provider' WHERE x.canonical_id=? AND r.source='spreadsheet' AND j.status<>'cancelled'",(pid,))
    for row in spreadsheet:
        attributes = json.loads(row['attributes_json'])
        retained = attributes.get('start_utc')
        if retained:
            span = day_interval(datetime.fromisoformat(retained).astimezone(ZONE).date()).clip(window)
            if span:
                evidence.unknown.append(span)
                evidence.refs.add(row['id'])
                evidence.reasons.add('spreadsheet_duration_unknown')
        elif attributes.get('date'):
            span = day_interval(date.fromisoformat(attributes['date'])).clip(window)
            if span:
                evidence.unknown.append(span)
                evidence.reasons.add('spreadsheet_duration_unknown')
    has_crm = connection.execute("SELECT 1 FROM source_records r JOIN canonical_crosswalk x ON x.source_id=r.id AND x.kind='provider' WHERE x.canonical_id=? AND r.source IN ('jobber','housecallpro','housecall_pro','workiz') LIMIT 1",(pid,)).fetchone() is not None
    if not calendars and not has_crm:

        evidence.unknown.append(window)
        evidence.reasons.add('schedule_evidence_missing')
    coverage = Interval(datetime.fromisoformat(REFERENCE),datetime.fromisoformat(DEFAULT_END))
    evidence.unknown.extend(subtract([window],[coverage]))
    if not coverage.start <= window.start < window.end <= coverage.end:
        evidence.reasons.add('outside_supplied_schedule_coverage')
    if evidence.disagreement:
        evidence.reasons.add('calendar_crm_interval_disagreement')
    if evidence.agreement:
        evidence.reasons.add('calendar_crm_interval_agreement')
    return evidence


def openings(connection: sqlite3.Connection, pid: str, window: Interval, duration_minutes: int = 120, limit: int = 3) -> dict:
    if isinstance(limit,bool) or not isinstance(limit,int) or not 1 <= limit <= 100:
        raise ValueError('limit must be 1 through 100')
    evidence = load_evidence(connection, pid, window)
    unknown = [i for i in evidence.unknown if i.overlaps(window)]
    known_window = subtract([window], unknown)
    status = 'unknown' if not known_window else 'partial' if unknown else 'known'
    free = [i for i in subtract(evidence.working,evidence.busy+unknown) if i.end-i.start >= timedelta(minutes=duration_minutes)]
    reasons = {'provider_level_capacity','travel_unmodeled','static_snapshot_coverage'} | evidence.reasons
    score = 0 if status=='unknown' else max(0, 80 - 25*bool(unknown) - 15*bool(evidence.disagreement) - 5*('tentative_hold_blocks' in reasons) - 10*('source_freshness_limited' in reasons) - 10*('undated_backlog_not_a_booking' in reasons))
    return {'provider_id':pid,'business_name':connection.execute('SELECT display_name FROM canonical_providers WHERE id=?',(pid,)).fetchone()[0],
            'window':window.public(),'coverage':{'start':REFERENCE,'end_exclusive':DEFAULT_END},'unknown_windows':[i.public() for i in union(unknown)],'status':status,'openings':None if status=='unknown' else [i.public() for i in free[:limit]],'total_openings':len(free),'truncated':len(free)>limit,
            'duration_minutes':duration_minutes,'confidence':{'score':score,'label':'unknown' if status=='unknown' else 'high' if score>=75 else 'moderate' if score>=50 else 'low','reasons':sorted(reasons)},
            'evidence_refs':sorted(evidence.refs),'agreement_count':evidence.agreement,'disagreement_count':evidence.disagreement}


def next_openings(database: Path, provider: str, start: str = REFERENCE, end: str = DEFAULT_END, duration_minutes: int = 120, limit: int = 3) -> dict:
    window = request_window(start,end,duration_minutes)
    with connect_readonly(database) as connection:
        return envelope(connection,openings(connection,provider_id(connection,provider),window,duration_minutes,limit))


def available_providers(database: Path, postal_code: str, trade: str = 'handyman', start: str = REFERENCE, end: str = THREE_DAYS, duration_minutes: int = 120, limit: int = 20) -> dict:
    from .ranking import candidates
    window = request_window(start,end,duration_minutes)
    with connect_readonly(database) as connection:
        eligible, excluded = candidates(connection,postal_code,trade,None,window,duration_minutes,True)
        if isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=100:
            raise ValueError('limit must be 1 through 100')
        return envelope(connection,{'providers':eligible[:limit],'excluded':excluded,'total':len(eligible),'truncated':len(eligible)>limit})

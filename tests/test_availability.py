import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from p2_fixture import build, fixture

from house_account.availability import calendar_intervals, next_openings
from house_account.model import Entity, Observation
from house_account.time_policy import Interval, local_instant, request_window, subtract


def schedule_database(tmp_path):
    observations = fixture()
    provider = observations[0].id
    observations.append(Observation(source='jobber',account='example',kind='profile',key='hours',file='fixture.json',locator='hours',raw={},normalized=Entity(kind='profile',provider_id=provider,attributes={'working_hours':{'timezone':'America/Chicago','weekdays':{d:[['08:00','17:00']] for d in ('mon','tue','wed','thu','fri')}}})))
    db = tmp_path/'schedule.db'
    build(db,tmp_path/'ledger',observations)
    with sqlite3.connect(db) as c:
        pid = c.execute('SELECT canonical_id FROM canonical_crosswalk WHERE source_id=? AND kind=\'provider\'',(provider,)).fetchone()[0]
    return db,pid


def event(uid, start, end, extra=''):
    return {'ical':f'BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTART{start}\r\nDTEND{end}\r\n{extra}END:VEVENT\r\n'}


def test_half_open_union_and_duration():
    def interval(a,b):
        return Interval(datetime.fromisoformat(f'2026-11-02T{a}:00+00:00'),datetime.fromisoformat(f'2026-11-02T{b}:00+00:00'))
    assert subtract([interval('08:00','17:00')],[interval('09:00','11:00'),interval('10:00','12:00'),interval('12:00','13:00')]) == [interval('08:00','09:00'),interval('13:00','17:00')]


def test_dst_rejects_ambiguous_and_missing_local_time():
    for value in ('2026-11-01T01:30','2026-03-08T02:30'):
        with pytest.raises(ValueError):
            local_instant(datetime.fromisoformat(value))
    zone = ZoneInfo('America/Chicago')
    span = Interval(datetime(2026,11,1,1,30,tzinfo=zone,fold=0),datetime(2026,11,1,1,15,tzinfo=zone,fold=1))
    assert (span.end-span.start).total_seconds()==2700


def test_recurrence_cancellation_override_exdate_rdate_and_transparency():
    window=request_window('2026-11-02T00:00:00-06:00','2026-11-06T00:00:00-06:00',60)
    events=[event('repeat',':20261102T150000Z',':20261102T160000Z','RRULE:FREQ=DAILY;COUNT=3\r\nEXDATE:20261104T150000Z\r\nRDATE:20261105T150000Z\r\n'),
            event('repeat',':20261103T150000Z',':20261103T160000Z','RECURRENCE-ID:20261103T150000Z\r\nSTATUS:CANCELLED\r\n'),
            event('transparent',':20261102T170000Z',':20261102T180000Z','TRANSP:TRANSPARENT\r\n'),
            event('hold',':20261102T190000Z',':20261102T200000Z','STATUS:TENTATIVE\r\n')]
    intervals,reasons=calendar_intervals(events,window)
    assert [(v.start.isoformat(),v.end.isoformat()) for v in intervals]==[('2026-11-02T15:00:00+00:00','2026-11-02T16:00:00+00:00'),('2026-11-02T19:00:00+00:00','2026-11-02T20:00:00+00:00'),('2026-11-05T15:00:00+00:00','2026-11-05T16:00:00+00:00')]
    assert reasons=={'tentative_hold_blocks'}


def test_all_day_exclusive_and_unsafe_recurrence():
    window=request_window('2026-11-02T00:00:00-06:00','2026-11-10T00:00:00-06:00',60)
    spans,_=calendar_intervals([event('vacation',';VALUE=DATE:20261104',';VALUE=DATE:20261109')],window)
    assert spans[0].start.isoformat()=='2026-11-04T06:00:00+00:00'
    assert spans[0].end.isoformat()=='2026-11-09T06:00:00+00:00'
    with pytest.raises(ValueError):
        calendar_intervals([event('flood',':20261102T150000Z',':20261102T160000Z','RRULE:FREQ=SECONDLY\r\n')],window)


def test_provider_level_occupancy_and_unknown_hours(tmp_path):
    db,pid=schedule_database(tmp_path)
    result=next_openings(db,pid,start='2026-11-03T00:00:00-06:00',end='2026-11-04T00:00:00-06:00',duration_minutes=60)['results']
    assert [(i['start_local'],i['end_local']) for i in result['openings']]==[('2026-11-03T08:00:00-06:00','2026-11-03T09:00:00-06:00'),('2026-11-03T10:00:00-06:00','2026-11-03T17:00:00-06:00')]
    with sqlite3.connect(db) as c:
        c.execute('UPDATE provider_hour_declarations SET emergency_only=1')
    result=next_openings(db,pid)['results']
    assert result['status']=='unknown' and result['openings'] is None
    assert 'hours_unknown_or_conflicting' in result['confidence']['reasons']


def test_cancelled_out_of_area_and_missing_endpoint(tmp_path):
    db,pid=schedule_database(tmp_path)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE canonical_jobs SET property_id=NULL,property_link_state='missing'")
        c.execute("UPDATE canonical_visits SET scheduling_state='cancelled' WHERE scheduled_start_utc LIKE '2026%'")
    result=next_openings(db,pid,start='2026-11-03T00:00:00-06:00',end='2026-11-04T00:00:00-06:00')['results']
    assert result['openings'][0]['duration_minutes']==540
    with sqlite3.connect(db) as c:
        c.execute("UPDATE canonical_visits SET scheduling_state='scheduled',scheduled_end_utc=NULL,scheduled_end_state='missing',scheduled_end_precision='unknown',scheduled_end_local_date=NULL WHERE scheduled_start_utc LIKE '2026-11-03%'")
    result=next_openings(db,pid,start='2026-11-03T00:00:00-06:00',end='2026-11-04T00:00:00-06:00')['results']
    assert result['status']=='unknown' and result['openings'] is None


def test_inputs_and_privacy(tmp_path):
    db,pid=schedule_database(tmp_path)
    for kwargs in ({'duration_minutes':0},{'duration_minutes':True},{'limit':False},{'start':'2026-11-02'},{'end':'2027-01-01T00:00:00Z'}):
        with pytest.raises(ValueError):
            next_openings(db,pid,**kwargs)
    result=json.dumps(next_openings(db,pid))
    for forbidden in ('214555','raw_json','Customer','phone','assignedUsers'):
        assert forbidden not in result


def test_split_hours_and_declared_closed_days(tmp_path):
    db,pid=schedule_database(tmp_path)
    with sqlite3.connect(db) as c:
        original=c.execute('SELECT * FROM provider_hour_declarations WHERE weekday=0').fetchone()
        c.execute("UPDATE provider_hour_declarations SET local_end='12:00' WHERE weekday=0")
        row=list(original)
        row[0]='afternoon';row[4]='13:00';row[5]='17:00'
        c.execute('INSERT INTO provider_hour_declarations VALUES(?,?,?,?,?,?,?,?,?,?,?)',row)
    result=next_openings(db,pid,start='2026-11-02T00:00:00-06:00',end='2026-11-03T00:00:00-06:00')['results']
    assert result['status']=='known'
    assert [(i['start_local'],i['end_local']) for i in result['openings']]==[('2026-11-02T08:00:00-06:00','2026-11-02T12:00:00-06:00'),('2026-11-02T13:00:00-06:00','2026-11-02T17:00:00-06:00')]


def test_estimate_appointment_blocks_without_service_credit(tmp_path):
    observations=fixture()
    provider=observations[0].id
    estimate=Observation(source='jobber',account='example',kind='estimate',key='quote',file='fixture.json',locator='quote',raw={},normalized=Entity(kind='estimate',provider_id=provider,status='scheduled',service='Drain cleaning'))
    observations.append(estimate)
    observations.append(Observation(source='jobber',account='example',kind='visit',key='quote-visit',file='fixture.json',locator='quote-visit',raw={},normalized=Entity(kind='visit',provider_id=provider,estimate_id=estimate.id,appointment_kind='estimate',status='scheduled',start_utc='2026-11-02T14:00:00+00:00',end_utc='2026-11-02T16:00:00+00:00')))
    db,pid=schedule_database(tmp_path)
    profile=Observation(source='jobber',account='example',kind='profile',key='hours',file='fixture.json',locator='hours',raw={},normalized=Entity(kind='profile',provider_id=provider,attributes={'working_hours':{'timezone':'America/Chicago','weekdays':{'mon':[['08:00','17:00']]}}}))
    observations.append(profile)
    build(db,tmp_path/'ledger',observations)
    result=next_openings(db,pid,start='2026-11-02T00:00:00-06:00',end='2026-11-03T00:00:00-06:00')['results']
    assert result['openings'][0]['start_local']=='2026-11-02T10:00:00-06:00'
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT count(*) FROM service_completions').fetchone()[0]==4


def test_calendar_ambiguous_local_time_is_not_silently_certain():
    window=request_window('2026-11-01T00:00:00-05:00','2026-11-02T00:00:00-06:00',60)
    with pytest.raises(ValueError):
        calendar_intervals([event('fold',';TZID=America/Chicago:20261101T013000',';TZID=America/Chicago:20261101T023000')],window)


def test_floating_calendar_events_localize_before_horizon_filter():
    window=request_window('2026-11-02T00:00:00-06:00','2026-11-03T00:00:00-06:00',60)
    spans,_=calendar_intervals([event('floating',':20261102T010000',':20261102T020000')],window)
    assert [(i.start.isoformat(),i.end.isoformat()) for i in spans]==[('2026-11-02T07:00:00+00:00','2026-11-02T08:00:00+00:00')]
    all_day,_=calendar_intervals([event('day',';VALUE=DATE:20261102',';VALUE=DATE:20261103')],window)
    assert all_day==[window]


def test_hours_weekday_uses_declaration_timezone(tmp_path):
    db,pid=schedule_database(tmp_path)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE provider_hour_declarations SET timezone_name='Pacific/Honolulu'")
        c.execute("UPDATE provider_hour_declarations SET local_start='20:00',local_end='23:00' WHERE declaration_state='known'")
    result=next_openings(db,pid,start='2026-11-03T00:00:00-06:00',end='2026-11-03T03:00:00-06:00')['results']
    assert result['status']=='known'
    assert [(i['start_utc'],i['end_utc']) for i in result['openings']]==[('2026-11-03T06:00:00+00:00','2026-11-03T09:00:00+00:00')]


def test_all_day_calendar_still_blocks_local_evening():
    window=request_window('2026-11-02T20:00:00-06:00','2026-11-02T23:00:00-06:00',60)
    spans,_=calendar_intervals([event('day',';VALUE=DATE:20261102',';VALUE=DATE:20261103')],window)
    assert spans==[window]
    honolulu=event('local-day',';VALUE=DATE:20261102',';VALUE=DATE:20261103')
    honolulu['calendar_timezone']='Pacific/Honolulu'
    early=request_window('2026-11-02T00:00:00-06:00','2026-11-02T08:00:00-06:00',60)
    spans,_=calendar_intervals([honolulu],early)
    assert [(i.start.isoformat(),i.end.isoformat()) for i in spans]==[('2026-11-02T10:00:00+00:00','2026-11-02T14:00:00+00:00')]


def test_blank_calendar_zone_and_outside_tentative_hold():
    window = request_window('2026-11-02T00:00:00-06:00', '2026-11-03T00:00:00-06:00', 60)
    outside = event('outside', ':20261101T150000Z', ':20261101T160000Z', 'STATUS:TENTATIVE\r\n')
    outside['calendar_timezone'] = ''
    inside = event('inside', ';TZID=America/Chicago:20261102T090000', ';TZID=America/Chicago:20261102T100000')
    inside['calendar_timezone'] = ''
    intervals, reasons = calendar_intervals([outside, inside], window)
    assert [(v.start.isoformat(), v.end.isoformat()) for v in intervals] == [('2026-11-02T15:00:00+00:00', '2026-11-02T16:00:00+00:00')]
    assert reasons == set()


def test_padded_ambiguous_event_only_affects_overlapping_window():
    for suffix in (':', ';TZID=America/Chicago:'):
        ambiguous=event('fold',suffix+'20261101T013000',suffix+'20261101T023000')
        following=request_window('2026-11-02T00:00:00-06:00','2026-11-03T00:00:00-06:00',60)
        assert calendar_intervals([ambiguous],following)==([],set())
        folded=request_window('2026-11-01T01:45:00-06:00','2026-11-01T02:00:00-06:00',10)
        with pytest.raises(ValueError):
            calendar_intervals([ambiguous],folded)


def test_adjacent_calendar_matches_preserve_agreement_before_busy_union(tmp_path):
    db,pid=schedule_database(tmp_path)
    with sqlite3.connect(db) as c:
        source=c.execute("SELECT source_id FROM canonical_crosswalk WHERE canonical_id=? AND kind='provider' LIMIT 1",(pid,)).fetchone()[0]
        visits=[r[0] for r in c.execute("SELECT id FROM canonical_visits WHERE scheduled_start_utc LIKE '2026-11-03%' ORDER BY id")]
        c.execute("UPDATE canonical_visits SET scheduled_start_utc='2026-11-03T16:00:00+00:00',scheduled_end_utc='2026-11-03T17:00:00+00:00' WHERE id=?",(visits[0],))
        c.execute("UPDATE canonical_visits SET scheduled_start_utc='2026-11-03T15:30:00+00:00',scheduled_end_utc='2026-11-03T16:30:00+00:00' WHERE id=?",(visits[1],))
        for uid,start,end in [('first','150000','160000'),('second','160000','170000')]:
            raw=event(uid,':20261103T'+start+'Z',':20261103T'+end+'Z')
            c.execute('INSERT INTO source_records VALUES(?,?,?,?,?,?,?,?,?)',(uid,'calendars','example','calendar_block',uid,uid,'2026-11-02','2026-10-24',json.dumps(raw)))
            c.execute("INSERT INTO calendar_blocks(id,provider_id,attributes_json) VALUES(?,?,'{}')",(uid,source))
    result=next_openings(db,pid,start='2026-11-03T00:00:00-06:00',end='2026-11-04T00:00:00-06:00',duration_minutes=60)['results']
    assert result['agreement_count']==2
    assert result['disagreement_count']==0
    assert [(i['start_local'],i['end_local']) for i in result['openings']]==[('2026-11-03T08:00:00-06:00','2026-11-03T09:00:00-06:00'),('2026-11-03T11:00:00-06:00','2026-11-03T17:00:00-06:00')]

"""Exercise P3 CLI behavior using the private pack and disposable source fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from house_account.adapters.other import _calendars
from house_account.identity import reconcile
from house_account.model import Entity, Observation
from house_account.storage import connect_readonly, write_snapshot

ROOT = Path(__file__).resolve().parents[1]
START = '2026-11-02T06:00:00+00:00'
END = '2026-11-05T06:00:00+00:00'


def logical(database):
    with connect_readonly(database) as connection:
        return hashlib.sha256('\n'.join(connection.iterdump()).encode()).hexdigest()


def manifest(data):
    return {str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob('*')) if p.is_file()}


def spans(result):
    return [(o['start_utc'], o['end_utc']) for o in result['openings'] or []]


def overlap(a, b):
    return datetime.fromisoformat(a[0]) < datetime.fromisoformat(b[1]) and datetime.fromisoformat(b[0]) < datetime.fromisoformat(a[1])


def event(uid, start, end, extra=''):
    return f'BEGIN:VEVENT\r\nUID:{uid}\r\nDTSTART;TZID=America/Chicago:{start}\r\nDTEND;TZID=America/Chicago:{end}\r\n{extra}SUMMARY:PRIVATE_SENTINEL\r\nEND:VEVENT\r\n'


def fixture(root, name, *, events=None, hours=True, emergency=False, visit=False, crew=1, estimate=False):
    directory = root/name
    calendar_path = directory/'sources/calendars/example.ics'
    calendar_path.parent.mkdir(parents=True)
    text = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nX-WR-CALNAME:Example Plumbing\r\n'
    text += events if events is not None else event('cancelled', '20261102T080000', '20261102T090000', 'STATUS:CANCELLED\r\n')
    text += 'END:VCALENDAR\r\n'
    calendar_path.write_text(text)
    observations = list(_calendars(directory))
    provider = observations[0].id

    def add(kind, key, raw, **fields):
        observation = Observation(source='jobber', account='example', kind=kind, key=key,
                                  file='synthetic.json', locator=key, raw=raw, snapshot_at='2026-11-02',
                                  normalized=Entity(kind=kind, **fields))
        observations.append(observation)
        return observation.id

    if hours:
        add('profile', 'profile', {'crew_size':crew, 'phone':'2145550100'}, provider_id=provider,
            attributes={'crew_size':crew, 'working_hours':{'timezone':'America/Chicago', 'emergency_only':emergency,
                        'weekdays':{day:[['08:00','18:00']] for day in ('mon','tue','wed','thu','fri','sat','sun')}}})
    if visit or estimate:
        prop = add('property','out-of-area',{'address':{'street1':'1 Example St','city':'Austin','state':'TX','postalCode':'78701'}},
                   attributes={'address':{'street1':'1 Example St','city':'Austin','state':'TX','postalCode':'78701'}})
        kind = 'estimate' if estimate else 'job'
        parent = add(kind, kind, {}, provider_id=provider, property_id=prop, status='scheduled' if estimate else 'active', service='Water heater replacement')
        add('visit','appointment',{'assignedUsers':{'nodes':[{'name':'PRIVATE_SENTINEL'}]}}, provider_id=provider,
            property_id=prop, **{kind+'_id':parent}, appointment_kind=kind, status='scheduled',
            start_utc='2026-11-02T16:00:00+00:00',end_utc='2026-11-02T18:00:00+00:00')
    database = directory/'snapshot.sqlite'
    write_snapshot(observations, database, [{'path':filename,'bytes':2,'sha256':'fixture','role':'source'} for filename in sorted({o.file for o in observations})],
                   projector=lambda c: reconcile(c,directory/'decisions.jsonl'))
    return database



def optimistic_free_minutes(database, provider, start_day=2, end_day=9):
    zone = ZoneInfo('America/Chicago')
    with connect_readonly(database) as c:
        c.row_factory = sqlite3.Row
        hours = c.execute("SELECT h.* FROM provider_hour_declarations h JOIN canonical_crosswalk x ON x.source_id=h.provider_id AND x.kind='provider' WHERE x.canonical_id=?", (provider,)).fetchall()
        visits = c.execute("SELECT v.* FROM canonical_visits v LEFT JOIN canonical_jobs j ON j.id=v.job_id LEFT JOIN canonical_estimates e ON e.id=v.estimate_id WHERE coalesce(j.provider_id,e.provider_id)=? AND v.scheduling_state NOT IN ('completed','cancelled','superseded')", (provider,)).fetchall()
    busy = [(datetime.fromisoformat(v['scheduled_start_utc']), datetime.fromisoformat(v['scheduled_end_utc'])) for v in visits if v['scheduled_start_utc'] and v['scheduled_end_utc']]
    maxima = []
    for day_number in range(start_day, end_day):
        day = datetime(2026, 11, day_number, tzinfo=zone)
        working = [(datetime.fromisoformat(str(day.date())+'T'+h['local_start']).replace(tzinfo=zone), datetime.fromisoformat(str(day.date())+'T'+h['local_end']).replace(tzinfo=zone)) for h in hours if h['weekday']==day.weekday() and h['declaration_state']=='known' and not h['emergency_only']]
        longest = run = 0
        for minute in range(1440):
            stamp = day+timedelta(minutes=minute)
            free = any(a<=stamp<b for a,b in working) and not any(a<=stamp<b for a,b in busy)
            run = run+1 if free else 0
            longest = max(longest,run)
        maxima.append(longest)
    return maxima


def assert_private(value):
    if isinstance(value, dict):
        assert not set(value) & {'raw_json','raw','phone','email','customer_name','customer_phone','customer_email','notes','location_raw','summary'}
        for item in value.values():
            assert_private(item)
    elif isinstance(value, list):
        for item in value:
            assert_private(item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database',type=Path)
    parser.add_argument('--data',type=Path,default=ROOT/'data')
    parser.add_argument('--parent-source','--parent',type=Path,default=ROOT/'artifacts/P3/parent-source')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/P3')
    args = parser.parse_args()
    args.parent_source = args.parent_source.resolve()
    args.output.mkdir(parents=True,exist_ok=True)
    source_before = manifest(args.data)
    database_before = logical(args.database) if args.database else None
    if (args.parent_source/'src').is_dir():
        args.parent_source /= 'src'
    receipts, outcomes = [], []
    with tempfile.TemporaryDirectory(prefix='house-account-p3-') as temporary:
        scratch = Path(temporary)
        database = scratch/'pack.sqlite'
        if args.database:
            with connect_readonly(args.database) as source, sqlite3.connect(database) as target:
                source.backup(target)
        else:
            from house_account.cli import ingest
            ingest(args.data, database, ledger=scratch/'decisions.jsonl')
        checked_databases = {}
        def cli(kind, value, *, db=database, parent=False, **flags):
            if db not in checked_databases:
                checked_databases[db] = logical(db)
            command = [sys.executable,'-m','house_account.cli','query',kind,value,'--database',str(db)]
            for key, flag_value in flags.items():
                command.extend(['--'+key.replace('_','-'), str(flag_value)])
            env = {**os.environ, 'PYTHONPATH':str(args.parent_source if parent else ROOT/'src'), 'TMPDIR':str(scratch)}
            process = subprocess.run(command,capture_output=True,text=True,cwd=scratch,env=env,check=False)
            assert process.returncode == 0, (command,process.stderr)
            response = json.loads(process.stdout)
            assert 'PRIVATE_SENTINEL' not in process.stdout
            assert_private(response)
            receipts.append({'command':command,'parent':parent,'exit_code':process.returncode,'response':response})
            return response

        def lane(number, check):
            first = len(receipts)
            try:
                detail = check()
                result = {'lane':number,'status':'pass','checks':detail}
            except (AssertionError, ValueError, KeyError, TypeError, sqlite3.Error, OSError) as exc:
                result = {'lane':number,'status':'fail','error':repr(exc)}
            result['receipts'] = receipts[first:]
            (args.output/f'lane-{number}.json').write_text(json.dumps(result,indent=2)+'\n')
            outcomes.append({k:v for k,v in result.items() if k != 'receipts'})
            print(json.dumps(outcomes[-1]),flush=True)

        def one():
            assert (args.parent_source/'house_account/cli.py').exists(), 'Parent CLI unavailable; provide --parent for regression verification'
            old = cli('block','4501 Gaston Ave, Dallas, TX 75246',parent=True)
            new = cli('block','4501 Gaston Ave, Dallas, TX 75246')
            assert new['results'] == old['results'] and new['results'], 'schedule regression or vacuous fixture'
            result = cli('openings','Lone Star Plumbing Co.',limit=100)['results']
            assert result['openings']
            with connect_readonly(database) as c:
                occupied = c.execute("SELECT v.scheduled_start_utc,v.scheduled_end_utc FROM canonical_visits v JOIN canonical_jobs j ON j.id=v.job_id WHERE j.provider_id=? AND v.scheduling_state NOT IN ('completed','cancelled','superseded') AND v.scheduled_start_utc IS NOT NULL AND v.scheduled_end_utc IS NOT NULL",(result['provider_id'],)).fetchall()
            assert all(not overlap(opening,busy) for opening in spans(result) for busy in occupied)
            return {'same_scheduled_visits':len(new['results']),'openings_avoid_active_visits':True}
        lane(1,one)

        def two():
            result = cli('available','75214',start=START,end=END,duration_minutes=120)['results']
            assert result['providers'], 'no candidate to verify'
            for provider in result['providers']:
                openings = provider.get('availability',provider)['openings']
                assert openings
                for item in openings:
                    assert (datetime.fromisoformat(item['end_utc'])-datetime.fromisoformat(item['start_utc'])).total_seconds()>=7200
                    assert datetime.fromisoformat(START)<=datetime.fromisoformat(item['start_utc'])<datetime.fromisoformat(item['end_utc'])<=datetime.fromisoformat(END)
            return {'eligible_providers':len(result['providers']),'continuous_two_hour_intervals':True}
        lane(2,two)

        def three():
            free = fixture(scratch,'free')
            busy = fixture(scratch,'outside',visit=True)
            before = cli('openings','Example Plumbing',db=free,start=START,end='2026-11-03T06:00:00+00:00')['results']
            after = cli('openings','Example Plumbing',db=busy,start=START,end='2026-11-03T06:00:00+00:00')['results']
            assert spans(before)==[('2026-11-02T14:00:00+00:00','2026-11-03T00:00:00+00:00')]
            assert spans(after)==[('2026-11-02T14:00:00+00:00','2026-11-02T16:00:00+00:00'),('2026-11-02T18:00:00+00:00','2026-11-03T00:00:00+00:00')]
            return {'postal_code':'78701','exact_busy_interval_subtracted':True}
        lane(3,three)

        def four():
            result = cli('openings','Abrams Plumbing',limit=100)['results']
            actual_status = result['status']
            with connect_readonly(database) as c:
                raw = [json.loads(r[0])['ical'] for r in c.execute("SELECT r.raw_json FROM calendar_blocks b JOIN source_records r ON r.id=b.id JOIN providers p ON p.id=b.provider_id WHERE p.display_name='Mike Abrams' AND b.all_day=1 AND b.start_local='2026-11-04'")]
            assert len(raw)==1
            copied = fixture(scratch,'abrams-observed',events=raw[0])
            isolated = cli('openings','Example Plumbing',db=copied,limit=100)['results']
            assert isolated['openings']
            block = ('2026-11-04T06:00:00+00:00','2026-11-09T06:00:00+00:00')
            assert all(not overlap(o,block) for o in spans(isolated))
            assert all(not overlap(o,block) for o in spans(result))
            return {'observed_exclusive_all_day_block':list(block),'other_openings_present':True,'actual_provider_status':actual_status,'observed_event_on_isolated_known_hours':True}
        lane(4,four)

        def five():
            base = event('repeat','20261102T100000','20261102T120000','RRULE:FREQ=DAILY;COUNT=3\r\n')
            cancel = event('repeat','20261103T100000','20261103T120000','RECURRENCE-ID;TZID=America/Chicago:20261103T100000\r\nSTATUS:CANCELLED\r\n')
            db = fixture(scratch,'recurrence',events=base+cancel)
            result = cli('openings','Example Plumbing',db=db,start=START,end=END,limit=100)['results']
            expected = [('2026-11-02T14:00:00+00:00','2026-11-02T16:00:00+00:00'),('2026-11-02T18:00:00+00:00','2026-11-03T00:00:00+00:00'),('2026-11-03T14:00:00+00:00','2026-11-04T00:00:00+00:00'),('2026-11-04T14:00:00+00:00','2026-11-04T16:00:00+00:00'),('2026-11-04T18:00:00+00:00','2026-11-05T00:00:00+00:00')]
            assert spans(result)==expected
            return {'only_cancelled_instance_released':True,'expected_intervals':expected}
        lane(5,five)

        def six():
            db = fixture(scratch,'ambiguous',events=event('ambiguous','20261101T013000','20261101T023000'))
            with connect_readonly(db) as c:
                codes = [r[0] for r in c.execute('SELECT code FROM issues')]
            assert 'ambiguous_calendar_time' in codes
            result = cli('openings','Example Plumbing',db=db,start='2026-11-01T05:00:00+00:00',end='2026-11-02T06:00:00+00:00')['results']
            assert result['status']=='unknown' and result['openings'] is None
            return {'import_ambiguity_issue':True,'availability_unknown':True}
        lane(6,six)

        def seven():
            db = fixture(scratch,'crew',visit=True,crew=8)
            result = cli('openings','Example Plumbing',db=db,start=START,end='2026-11-03T06:00:00+00:00')['results']
            assert spans(result)==[('2026-11-02T14:00:00+00:00','2026-11-02T16:00:00+00:00'),('2026-11-02T18:00:00+00:00','2026-11-03T00:00:00+00:00')]
            assert 'provider_level_capacity' in result['confidence']['reasons']
            return {'declared_crew':8,'named_assignment_not_extra_capacity':True}
        lane(7,seven)

        def eight():
            outputs=[]
            for name,flags in [('emergency',{'emergency':True}),('missing',{'hours':False})]:
                db = fixture(scratch,name,**flags)
                result = cli('openings','Example Plumbing',db=db)['results']
                assert result['status']=='unknown' and result['openings'] is None
                outputs.append(name)
            return {'explicit_unknown_cases':outputs}
        lane(8,eight)

        def nine():
            result = cli('recommend','75206',service='water_heater')['results']
            default_count = len(result['providers'])
            independent = []
            if not default_count:
                for excluded in result['excluded']:
                    if 'availability' in excluded:
                        upper_bounds = optimistic_free_minutes(database,excluded['provider_id'])
                        assert max(upper_bounds)<excluded['availability']['duration_minutes']
                        independent.append({'provider_id':excluded['provider_id'],'optimistic_daily_free_minutes':upper_bounds,'requested_minutes':excluded['availability']['duration_minutes']})
            if not default_count:
                assert result['excluded'] and all(p['reasons'] for p in result['excluded'])
                result = cli('recommend','75206',service='water_heater',duration_minutes=120)['results']
            providers = result['providers']
            assert providers, 'no eligible explicit-duration recommendation to verify'
            for provider in providers:
                assert provider['availability']['evidence_refs'] and provider['score_breakdown']
                assert provider['duration']['minutes']>0
                assert provider['availability']['openings']
                for o in provider['availability']['openings']:
                    assert o['duration_minutes']>=provider['duration']['minutes']
            return {'default_eligible_recommendations':default_count,'eligible_recommendations':len(providers),'duration_and_evidence_present':True,'independent_minute_grid_upper_bounds':independent}
        lane(9,nine)

        def ten():
            first = cli('openings','Lone Star Plumbing Co.')
            assert cli('openings','Lone Star Plumbing Co.')==first
            assert spans(first['results'])==[('2026-11-17T16:30:00+00:00','2026-11-17T19:00:00+00:00'),('2026-11-18T16:30:00+00:00','2026-11-18T22:00:00+00:00'),('2026-11-20T16:00:00+00:00','2026-11-20T18:15:00+00:00')]
            assert max(optimistic_free_minutes(database,first['results']['provider_id'],2,17))<120
            ray = cli('openings',"Rays Fix It",limit=100)['results']
            observed = event('transparent','20261102T080000','20261102T100000','TRANSP:TRANSPARENT\r\n')+event('tentative','20261102T130000','20261102T150000','STATUS:TENTATIVE\r\n')
            db = fixture(scratch,'mixed',events=observed,estimate=True)
            result = cli('openings','Example Plumbing',db=db,start=START,end='2026-11-03T06:00:00+00:00',limit=100)['results']
            assert spans(result)==[('2026-11-02T14:00:00+00:00','2026-11-02T16:00:00+00:00'),('2026-11-02T21:00:00+00:00','2026-11-03T00:00:00+00:00')]
            with connect_readonly(database) as c:
                raw = [json.loads(r[0])['ical'] for r in c.execute("SELECT r.raw_json FROM calendar_blocks b JOIN source_records r ON r.id=b.id JOIN providers p ON p.id=b.provider_id WHERE p.display_name='Ray Delgado (work)' AND (b.transparency='TRANSPARENT' OR b.status='tentative')")]
            assert len(raw)==2
            copied = fixture(scratch,'ray-observed',events=''.join(raw),estimate=True)
            observed_result = cli('openings','Example Plumbing',db=copied,start=START,end='2026-11-06T06:00:00+00:00',limit=100)['results']
            assert all(not overlap(o,('2026-11-04T19:00:00+00:00','2026-11-04T21:00:00+00:00')) for o in spans(observed_result))
            assert any(datetime.fromisoformat(o[0])<=datetime.fromisoformat('2026-11-05T22:00:00+00:00') and datetime.fromisoformat(o[1])>=datetime.fromisoformat('2026-11-05T22:30:00+00:00') for o in spans(observed_result))
            return {'next_three_deterministic':True,'ray_status':ray['status'],'transparent_free_tentative_and_estimate_busy':True,'actual_ray_events_on_isolated_known_hours':True}
        lane(10,ten)
        assert all(logical(db)==before for db,before in checked_databases.items()), 'query modified logical database'
    assert manifest(args.data)==source_before
    assert not args.database or logical(args.database)==database_before
    summary={'status':'pass' if all(r['status']=='pass' for r in outcomes) else 'fail','lanes':outcomes,
             'source_files_unchanged':len(source_before),'source_manifest_sha256':hashlib.sha256(json.dumps(source_before,sort_keys=True).encode()).hexdigest(),
             'database_logically_unchanged':True,'scratch_removed':not scratch.exists(),
             'screenshots':'Terminal screenshot capture unavailable; exact CLI commands and JSON receipts retained.'}
    (args.output/'live-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    raise SystemExit(0 if summary['status']=='pass' else 1)


if __name__=='__main__':
    main()

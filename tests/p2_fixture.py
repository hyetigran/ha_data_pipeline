from pathlib import Path

from house_account.identity import reconcile
from house_account.model import Entity, Issue, Observation
from house_account.storage import write_snapshot

FILES = [{'path':'fixture.json','bytes':2,'sha256':'fixture','role':'source'}]


def fixture():
    output = []
    def add(kind,key,raw,source='jobber',**fields):
        row = Observation(source=source,account='example',kind=kind,key=key,file='fixture.json',locator=kind+key,raw=raw,normalized=Entity(kind=kind,**fields))
        output.append(row)
        return row.id
    provider = add('provider','provider',{'phone':'2145550100'},display_name='Example Plumbing',trade='plumbing')
    add('provider','alias',{'phone':'2145550100','trades':['plumbing']},source='profiles',display_name='Example Pipes')
    add('provider','unproven',{'phone':'2145550199'},display_name='Example Plumbing')
    add('street_segment','street',{'street':'fixture'},attributes={'street_name':'Example','street_type':'St','city':'Dallas','state':'TX','zip':'75214','from_number':4500,'to_number':4599,'start_lat':32.8,'end_lat':32.8,'start_lon':-96.8,'end_lon':-96.79})
    props = []
    for key,unit in [('a','Apt 4'),('b','#4'),('c','Unit 5')]:
        address = {'street1':'4501 Example Street','street2':unit,'city':'Dallas','province':'TX','postalCode':'75214'}
        props.append(add('property',key,{'address':address},attributes={'address':address}))
    for index,prop in enumerate(props):
        raw = {'visits':{'nodes':[{'visitStatus':'COMPLETED','completedAt':'2025-11-10T15:00:00Z'}]}}
        job = add('job',str(index),raw,provider_id=provider,property_id=prop,status='archived',source_status='archived',service='Drain cleaning')
        add('visit',f'{index}-completed',raw['visits']['nodes'][0],provider_id=provider,property_id=prop,job_id=job,appointment_kind='job',status='completed',start_utc='2025-11-10T14:00:00+00:00',end_utc='2025-11-10T15:00:00+00:00')
        for visit in range(2 if index==0 else 1):
            add('visit',f'{index}-{visit}',{'index':index,'visit':visit},provider_id=provider,property_id=prop,job_id=job,appointment_kind='job',status='scheduled',start_utc='2026-11-03T15:00:00+00:00',end_utc='2026-11-03T16:00:00+00:00')
    raw = {'JobDateTime':'2026-11-10 09:00:00','JobEndDateTime':'2026-11-10 10:00:00','LastStatusUpdate':'2025-11-11 09:00:00'}
    job = add('job','J8OMKP',raw,source='workiz',provider_id=provider,property_id=props[0],status='completed',source_status='Done',service='Drain cleaning')
    observations_job = output[-1]
    observations_job.issues.append(Issue(code='temporal_inconsistency',field='start_utc'))
    add('visit','trap',{'start':'2026-11-10'},source='workiz',provider_id=provider,property_id=props[0],job_id=job,appointment_kind='job',status='completed',start_utc='2026-11-10T15:00:00+00:00',end_utc='2026-11-10T16:00:00+00:00')
    return output


def build(database: Path, ledger: Path, observations=None, *, identity_source=None):
    return write_snapshot(observations or fixture(),database,FILES,projector=lambda c:reconcile(c,ledger),identity_source=identity_source)

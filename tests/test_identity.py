import json

from p2_fixture import build

from house_account.addresses import distance_miles, normalize
from house_account.storage import connect_readonly


def test_phone_requires_trade_and_units_remain_distinct(tmp_path):
    database = tmp_path/'db'
    build(database,tmp_path/'ledger')
    with connect_readonly(database) as c:
        assert c.execute('SELECT count(*) FROM canonical_providers').fetchone()[0] == 2
        assert c.execute('SELECT count(*) FROM canonical_properties').fetchone()[0] == 2
        assert c.execute('SELECT count(*) FROM canonical_jobs').fetchone()[0] == 4
        assert c.execute('SELECT count(*) FROM canonical_visits').fetchone()[0] == 8
        candidates = [json.loads(r[0]) for r in c.execute('SELECT document FROM reconciliation_proposals')]
        assert any(p['kind']=='provider_match' for p in candidates)


def test_units_not_erased_and_interpolation():
    base = {'street':'4500 Example St','city':'Dallas','state':'TX','zip':'75214'}
    a = normalize({**base,'street_line_2':'Apt 4-A'},[])
    b = normalize({**base,'street_line_2':'#4A'},[])
    assert a.key != b.key
    assert normalize({**base,'street_line_2':'#4'},[]).key == normalize({**base,'street_line_2':'Apt 4'},[]).key
    assert distance_miles(32.8,-96.8,32.8,-96.8)==0


def test_transposed_address_needs_normalized_contact_label_and_independent_properties(tmp_path):
    from p2_fixture import fixture

    from house_account.model import Entity, Observation

    observations = fixture()
    provider = observations[0].id
    def add(kind,key,raw,source='spreadsheet',account='rays_fixit',**fields):
        item = Observation(source=source,account=account,kind=kind,key=key,file='fixture.json',locator=key,
                           raw=raw,normalized=Entity(kind=kind,**fields))
        observations.append(item)
        return item.id
    suspect = add('job','row175',{'Address':'5832 belmont ave','Phone':'+1 214 555 0123','Customer':'Example Customer'},
                  provider_id=provider,service='TV mount',attributes={'address_raw':'5832 belmont ave'})
    earlier = add('job','row88',{'Address':'5823 Belmont Ave','Phone':'(214) 555-0123','Customer':'Example Customer'},
                  provider_id=provider,service='Drywall patch',attributes={'address_raw':'5823 Belmont Ave'})
    evidence = {suspect,earlier}
    for account in ('cleaner','plumber'):
        customer = add('customer','contact',{'phones':[{'number':'214.555.0123'}]},source='jobber',account=account,provider_id=provider)
        address = {'street1':'5823 Belmont Ave','city':'Dallas','province':'TX','postalCode':'75214'}
        prop = add('property','property',{'address':address},source='jobber',account=account,
                   customer_id=customer,provider_id=provider,attributes={'address':address})
        evidence.update((customer,prop))
    database = tmp_path/'db'
    def corrections():
        build(database,tmp_path/'ledger',observations)
        with connect_readonly(database) as c:
            proposals = [json.loads(r[0]) for r in c.execute('SELECT document FROM reconciliation_proposals')]
            crosswalk = c.execute('SELECT canonical_id FROM canonical_crosswalk WHERE source_id=? AND kind=?',(suspect,'property')).fetchone()[0]
            original = c.execute('SELECT house_number FROM canonical_properties WHERE id=?',(crosswalk,)).fetchone()[0]
            assert original==5832
        return [p for p in proposals if p['proposed_action'].get('field')=='address']
    result = corrections()
    assert len(result)==1
    assert result[0]['proposed_action']['original']=='5832 belmont ave'
    assert result[0]['proposed_action']['proposed']=='5823 belmont ave'
    assert set(result[0]['source_refs'])==evidence
    assert set(result[0]['observations'])==evidence
    assert result[0]['confidence']=='high'
    prior = next(o for o in observations if o.id==earlier)
    prior.raw['Customer']='Different Customer'
    assert corrections()==[]
    prior.raw['Customer']='Example Customer'
    prior.raw['Phone']=''
    assert corrections()==[]
    prior.raw['Phone']='(214) 555-0123'
    observations[:] = [o for o in observations if not (o.source=='jobber' and o.account=='plumber')]
    assert corrections()==[]


def test_job_review_tracks_provider_property_visit_and_reference_evidence(tmp_path,monkeypatch):
    from house_account import cli
    from house_account.model import Entity, Observation
    from house_account.review import apply_review, export_review, validate_review

    observations = []
    def add(kind,key,raw,source='jobber',**fields):
        item = Observation(source=source,account='fixture',kind=kind,key=key,file='fixture.json',locator=key,
                           raw=raw,normalized=Entity(kind=kind,**fields))
        observations.append(item)
        return item.id
    segment = {'street_name':'Example','street_type':'St','city':'Dallas','state':'TX','zip':'75214',
               'from_number':4500,'to_number':4599,'start_lat':32.8,'end_lat':32.8,'start_lon':-96.8,'end_lon':-96.79}
    reference = add('street_segment','reference',segment.copy(),attributes=segment)
    left = add('provider','left',{'phone':'2145550100'},display_name='Fixture Plumbing')
    right = add('provider','right',{'phone':'2145550100','trades':['plumbing']},source='housecall_pro',display_name='Fixture Pipes')
    trade_job = add('job','trade-evidence',{'service':'Drain cleaning'},provider_id=left,service='Drain cleaning')
    expected = {reference,left,right,trade_job}
    for index,(provider,source) in enumerate(((left,'jobber'),(right,'housecall_pro'))):
        address = {'street1':'4501 Example Street','street2':'Apt 4'}
        prop = add('property',f'property-{index}',{'address':address},source,attributes={'address':address})
        job = add('job',f'job-{index}',{'service':'Other'},source,provider_id=provider,property_id=prop,service='Other')
        visit = add('visit',f'visit-{index}',{'start':'2026-11-03T15:00:00+00:00'},source,
                    provider_id=provider,property_id=prop,job_id=job,appointment_kind='job',
                    start_utc='2026-11-03T15:00:00+00:00',end_utc='2026-11-03T16:00:00+00:00')
        expected.update((prop,job,visit))
    unrelated = add('property','unrelated',{'address':{'street1':'9999 Different Road'}},
                    attributes={'address':{'street1':'9999 Different Road'}})
    db,file,ledger = [tmp_path/name for name in ('db','review.json','ledger.jsonl')]
    monkeypatch.setattr(cli,'ingest',lambda data,database,ledger,**kw:build(database,ledger,observations,identity_source=kw.get('identity_source')))
    build(db,ledger,observations)
    export_review(db,file,ledger)
    document = json.loads(file.read_text())
    candidate = next(p for p in document['proposals'] if p['kind']=='job_match')
    assert set(candidate['source_refs'])==expected
    assert set(candidate['observations'])==expected
    candidate['human']={'decision':'approve','reviewer':'Fixture Reviewer','reason':'Sanitized test only','decided_at':'2026-10-24T12:00:00Z'}
    file.write_text(json.dumps(document))
    apply_review(tmp_path/'unused',db,file,ledger)
    with connect_readonly(db) as c:
        assert c.execute('SELECT count(*) FROM canonical_jobs').fetchone()[0]==2
    for item in observations:
        if item.id not in expected:
            continue
        item.raw['changed_evidence']='fixture revision'
        build(db,ledger,observations)
        with connect_readonly(db) as c:
            assert c.execute('SELECT count(*) FROM canonical_jobs').fetchone()[0]==3
            stale = json.loads(c.execute('SELECT stale_decisions FROM reconciliation_metadata').fetchone()[0])
            assert len(stale)==1
        del item.raw['changed_evidence']
    next(item for item in observations if item.id==unrelated).raw['changed_evidence']='unrelated revision'
    build(db,ledger,observations)
    validate_review(db,file,ledger)
    with connect_readonly(db) as c:
        assert c.execute('SELECT count(*) FROM canonical_jobs').fetchone()[0]==2
        assert json.loads(c.execute('SELECT stale_decisions FROM reconciliation_metadata').fetchone()[0])==[]


def test_spreadsheet_comma_postal_code_uses_unique_reference():
    segment = {'street_name':'Live Oak','street_type':'St','city':'Dallas',
               'state':'TX','zip':'75204','from_number':4500,'to_number':4599,
               'start_lat':32.8,'end_lat':32.81,'start_lon':-96.8,'end_lon':-96.79}
    address = normalize('4541 Live Oak ST, 75204', [segment])
    assert address.key == (4541, 'live oak st', '', 'dallas', 'tx', '75204')
    assert address.precision == 'street_segment_interpolation'
    assert normalize('4541 Live Oak ST, 75206', [segment]).latitude is None

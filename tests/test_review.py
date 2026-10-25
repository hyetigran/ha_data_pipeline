import json
from pathlib import Path

import pytest
from p2_fixture import build, fixture

from house_account import cli
from house_account.review import (
    apply_review,
    export_review,
    read_ledger,
    validate_review,
)
from house_account.storage import connect_readonly


def setup(tmp_path, monkeypatch):
    database, file, ledger = [tmp_path/name for name in ('db','review.json','decisions.jsonl')]
    build(database,ledger)
    export_review(database,file,ledger)
    monkeypatch.setattr(cli,'ingest',lambda data,database,ledger,**kw:build(database,ledger,identity_source=kw.get('identity_source')))
    return database,file,ledger


def decide(file,kind='field_correction',decision='approve',supersedes=None):
    document = json.loads(file.read_text())
    for item in document['proposals']:
        if item['kind']==kind:
            item['human']={'decision':decision,'reviewer':'Fixture Reviewer','reason':'Sanitized test only','decided_at':'2026-10-24T12:00:00Z','supersedes_decision_id':supersedes.get(item['proposal_id']) if supersedes else None}
    file.write_text(json.dumps(document))


def test_approve_dry_run_replay_supersession(tmp_path,monkeypatch):
    db,file,ledger = setup(tmp_path,monkeypatch)
    original = db.read_bytes()
    decide(file)
    dry = apply_review(Path('unused'),db,file,ledger,dry_run=True)
    assert len(dry['changes']['canonical_visits']['changed_ids']) == 1
    assert db.read_bytes()==original and not ledger.exists()
    first = apply_review(Path('unused'),db,file,ledger)
    assert first['decisions_to_record']==2
    events = read_ledger(ledger)
    assert len(events)==2
    assert apply_review(Path('unused'),db,file,ledger)['decisions_to_record']==0
    assert read_ledger(ledger)==events
    with connect_readonly(db) as c:
        assert c.execute("SELECT count(DISTINCT job_id) FROM canonical_visits WHERE scheduled_start_state='disputed'").fetchone()[0]==0
    decide(file,decision='defer',supersedes={e['proposal']['proposal_id']:e['decision_id'] for e in events})
    apply_review(Path('unused'),db,file,ledger)
    build(db,ledger)
    with connect_readonly(db) as c:
        assert c.execute("SELECT count(DISTINCT job_id) FROM canonical_visits WHERE scheduled_start_state='disputed'").fetchone()[0]==1
    assert len(read_ledger(ledger))==4


def test_reject_defer_export_preserves_edits(tmp_path,monkeypatch):
    db,file,ledger=setup(tmp_path,monkeypatch)
    decide(file,kind='provider_match',decision='reject')
    before=json.loads(file.read_text())
    export_review(db,file,ledger)
    assert json.loads(file.read_text())==before
    apply_review(Path('unused'),db,file,ledger)
    fresh=tmp_path/'fresh.json'
    export_review(db,fresh,ledger)
    assert any(p['human']['decision']=='reject' for p in json.loads(fresh.read_text())['proposals'])
    with connect_readonly(db) as c:
        assert c.execute('SELECT count(*) FROM canonical_providers').fetchone()[0]==2


@pytest.mark.parametrize('field',['confidence','source_refs','proposed_action'])
def test_forged_proposal_fails_without_writes(tmp_path,monkeypatch,field):
    db,file,ledger=setup(tmp_path,monkeypatch)
    document=json.loads(file.read_text())
    p=document['proposals'][0]
    if field=='confidence':
        p[field]='low' if p[field]!='low' else 'high'
    elif field=='source_refs':
        p[field]=['forged']
    else:
        p[field]['proposed']='forged'
    file.write_text(json.dumps(document))
    before=db.read_bytes()
    with pytest.raises(ValueError):
        apply_review(Path('unused'),db,file,ledger)
    assert before==db.read_bytes() and not ledger.exists()


def test_failure_after_recording_recovers_and_truncated_ledger_fails(tmp_path,monkeypatch):
    db,file,ledger=setup(tmp_path,monkeypatch)
    decide(file)
    before=db.read_bytes()
    with pytest.raises(ValueError,match='recorded but not applied'):
        apply_review(Path('unused'),db,file,ledger,fail_after=1)
    assert db.read_bytes()==before and len(read_ledger(ledger))==2
    apply_review(Path('unused'),db,file,ledger)
    assert len(read_ledger(ledger))==2
    ledger.write_text(ledger.read_text()+'{"partial":')
    before=db.read_bytes()
    with pytest.raises(ValueError):
        build(db,ledger)
    assert db.read_bytes()==before


def test_changed_evidence_stales_only_affected_and_export_keeps_context(tmp_path,monkeypatch):
    db,file,ledger=setup(tmp_path,monkeypatch)
    decide(file)
    decide(file,kind='provider_match',decision='reject')
    apply_review(Path('unused'),db,file,ledger)
    observations=fixture()
    for o in observations:
        if o.key=='J8OMKP':
            o.raw['extra']='changed'
    build(db,ledger,observations)
    with pytest.raises(ValueError,match='stale'):
        validate_review(db,file,ledger)
    fresh=tmp_path/'new.json'
    result=export_review(db,fresh,ledger)
    assert result['stale']==2
    doc=json.loads(fresh.read_text())
    assert any(p['human']['decision']=='reject' for p in doc['proposals'])
    assert all(p['human']['decision']=='approve' for p in doc['stale_proposals'])


def test_conflicting_partial_year_correction_validated_before_append(tmp_path,monkeypatch):
    db,file,ledger=setup(tmp_path,monkeypatch)
    doc=json.loads(file.read_text())
    for p in doc['proposals']:
        if p['proposed_action']['field']=='end_utc':
            p['human']={'decision':'approve','reviewer':'Fixture','reason':'test only','decided_at':'2026-10-24T12:00:00Z'}
    file.write_text(json.dumps(doc))
    before=db.read_bytes()
    with pytest.raises(ValueError,match='paired interval corrections'):
        apply_review(Path('unused'),db,file,ledger,dry_run=True)
    assert before==db.read_bytes() and not ledger.exists()


def test_database_lock_and_output_collision(tmp_path,monkeypatch):
    from house_account.review import review_lock
    db,file,ledger=setup(tmp_path,monkeypatch)
    with review_lock(db), pytest.raises(BlockingIOError):
        apply_review(Path('unused'),db,file,ledger)
    with pytest.raises(ValueError,match='distinct'):
        export_review(db,db,ledger)


@pytest.mark.parametrize('field',['start_utc','end_utc'])
@pytest.mark.parametrize('mode',['validate','dry_run'])
def test_interval_correction_requires_both_endpoints(tmp_path,monkeypatch,field,mode):
    db,file,ledger=setup(tmp_path,monkeypatch)
    doc=json.loads(file.read_text())
    for p in doc['proposals']:
        if p['proposed_action']['field']==field:
            p['human']={'decision':'approve','reviewer':'Fixture','reason':'test only','decided_at':'2026-10-24T12:00:00Z'}
    file.write_text(json.dumps(doc))
    before=db.read_bytes()
    with pytest.raises(ValueError,match='paired interval corrections'):
        if mode=='validate':
            validate_review(db,file,ledger)
        else:
            apply_review(Path('unused'),db,file,ledger,dry_run=True)
    assert db.read_bytes()==before and not ledger.exists()


@pytest.mark.parametrize('field',['start_utc','end_utc'])
def test_interval_correction_cannot_be_partially_superseded(tmp_path,monkeypatch,field):
    db,file,ledger=setup(tmp_path,monkeypatch)
    decide(file)
    apply_review(Path('unused'),db,file,ledger)
    events=read_ledger(ledger)
    doc=json.loads(file.read_text())
    for p in doc['proposals']:
        if p['proposed_action']['field']==field:
            event=next(e for e in events if e['proposal']['proposal_id']==p['proposal_id'])
            p['human']={'decision':'defer','reviewer':'Fixture','reason':'test only','decided_at':'2026-10-24T12:00:00Z','supersedes_decision_id':event['decision_id']}
    file.write_text(json.dumps(doc))
    before=db.read_bytes(),ledger.read_bytes()
    with pytest.raises(ValueError,match='paired interval corrections'):
        apply_review(Path('unused'),db,file,ledger,dry_run=True)
    assert (db.read_bytes(),ledger.read_bytes())==before


def test_rebuild_rejects_incomplete_interval_approval(tmp_path,monkeypatch):
    from house_account.model import canonical_json, digest
    db,file,ledger=setup(tmp_path,monkeypatch)
    decide(file)
    apply_review(Path('unused'),db,file,ledger)
    event=next(e for e in read_ledger(ledger) if e['proposal']['proposed_action']['field']=='start_utc')
    body={key:value for key,value in event.items() if key!='decision_id'}
    body['previous']=''
    ledger.write_text(canonical_json({'decision_id':digest(body),**body})+'\n')
    before=db.read_bytes()
    with pytest.raises(ValueError,match='paired interval corrections'):
        build(db,ledger)
    assert db.read_bytes()==before

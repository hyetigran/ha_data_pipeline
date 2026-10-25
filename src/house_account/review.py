from __future__ import annotations

import fcntl
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .model import canonical_json, digest
from .storage import connect_readonly

RULE = 'reconciliation-v2'


class Decision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approve','reject','defer'] = 'defer'
    reviewer: str | None = None
    decided_at: str | None = None
    reason: str | None = None
    supersedes_decision_id: str | None = None

    @model_validator(mode='after')
    def attributed(self) -> Decision:
        attributed = self.decision != 'defer' or any((self.reviewer,self.decided_at,self.reason,self.supersedes_decision_id))
        if attributed:
            if not self.reviewer or not self.reviewer.strip() or not self.reason or not self.reason.strip() or not self.decided_at:
                raise ValueError('explicit decisions require reviewer, decided_at and reason')
            time = datetime.fromisoformat(self.decided_at)
            offset = time.utcoffset()
            if offset is None or offset.total_seconds() != 0:
                raise ValueError('decision timestamp must be UTC')
        return self


class Action(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation: Literal['merge','correct']
    entity: Literal['provider','property','job']
    targets: list[str]
    field: Literal['address','start_utc','end_utc'] | None = None
    original: Any = None
    proposed: Any = None

    @model_validator(mode='after')
    def allowed(self) -> Action:
        if self.operation == 'merge':
            if len(set(self.targets)) < 2 or self.field is not None:
                raise ValueError('merge requires distinct identities and no field')
        elif len(self.targets) != 1 or not self.field:
            raise ValueError('correction requires one identity and an allowed field')
        return self


class Proposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    proposal_id: str
    evidence_version: str
    kind: Literal['provider_match','property_match','job_match','field_correction']
    source_refs: list[str]
    source_hashes: dict[str,str]
    observations: dict[str,dict[str,Any]] = Field(default_factory=dict)
    rule_version: str
    proposed_action: Action
    evidence: list[str]
    conflicts: list[str]
    confidence: Literal['high','medium','low']
    human: Decision = Field(default_factory=Decision)

    def authentic(self) -> dict[str, Any]:
        return self.model_dump(exclude={'human'})


class ReviewFile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1] = 1
    proposals: list[Proposal]
    stale_proposals: list[Proposal] = Field(default_factory=list)


def proposal(action: Action, hashes: dict[str,str], evidence: list[str], conflicts: list[str], confidence: Literal['high','medium','low']='medium') -> Proposal:
    refs = sorted(hashes)
    pid = digest([action.model_dump(), refs, RULE])
    return Proposal(proposal_id=pid,evidence_version=digest([pid,hashes,RULE]),
                    kind=cast(Literal['provider_match','property_match','job_match','field_correction'], 'field_correction' if action.operation=='correct' else f'{action.entity}_match'),
                    source_refs=refs,source_hashes=hashes,rule_version=RULE,proposed_action=action,
                    evidence=evidence,conflicts=conflicts,confidence=confidence)


def proposals(connection: sqlite3.Connection) -> list[Proposal]:
    return [Proposal.model_validate_json(row[0]) for row in connection.execute('SELECT document FROM reconciliation_proposals ORDER BY id')]


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    previous = ''
    for line in path.read_text().splitlines():
        event = json.loads(line)
        if set(event) != {'decision_id','previous','proposal','human'}:
            raise ValueError('invalid ledger event')
        body = {key:value for key,value in event.items() if key!='decision_id'}
        if event['previous'] != previous or digest(body) != event['decision_id']:
            raise ValueError('ledger chain invalid')
        Proposal.model_validate({**event['proposal'],'human':event['human']})
        result.append(event)
        previous = event['decision_id']
    return result


def effective(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active: dict[str,dict[str,Any]] = {}
    seen: dict[str,dict[str,Any]] = {}
    for event in events:
        pid = event['proposal']['proposal_id']
        old = active.get(pid)
        supersedes = event['human'].get('supersedes_decision_id')
        if supersedes:
            if not old or old['decision_id'] != supersedes or supersedes not in seen:
                raise ValueError('supersession must replace the active decision for this proposal')
        elif old:
            raise ValueError('replacement requires supersedes_decision_id')
        active[pid] = event
        seen[event['decision_id']] = event
    return list(active.values())


def current_decisions(items: list[Proposal], events: list[dict[str,Any]]) -> tuple[list[dict[str,Any]],list[str]]:
    lookup = {(p.proposal_id,p.evidence_version):p for p in items}
    approved, stale = [], []
    interval_pairs: dict[tuple[str,str],dict[str,str]] = {}
    for item in items:
        action = item.proposed_action
        if action.operation == 'correct' and action.field in {'start_utc','end_utc'}:
            group = (action.targets[0],digest(item.source_hashes))
            interval_pairs.setdefault(group,{})[str(action.field)] = item.proposal_id
    fields: dict[tuple[str,str | None],Any] = {}
    for event in effective(events):
        old = event['proposal']
        candidate = lookup.get((old['proposal_id'],old['evidence_version']))
        if not candidate or candidate.authentic() != old:
            stale.append(event['decision_id'])
            continue
        if event['human']['decision'] != 'approve':
            continue
        action = candidate.proposed_action
        if action.operation == 'correct':
            key = (action.targets[0],action.field)
            if key in fields and fields[key] != action.proposed:
                raise ValueError('conflicting field corrections')
            fields[key] = action.proposed
        approved.append(event)
    approved_ids = {event['proposal']['proposal_id'] for event in approved}
    for pair in interval_pairs.values():
        ids = set(pair.values())
        if set(pair) == {'start_utc','end_utc'} and ids & approved_ids and not ids <= approved_ids:
            raise ValueError('paired interval corrections require both endpoints approved or neither')
    return approved, stale


def safe_paths(data: Path, database: Path, file: Path, ledger: Path) -> None:
    paths = [p.resolve() for p in (database,file,ledger)]
    if len(set(paths)) != 3:
        raise ValueError('database, review and ledger must be distinct')
    source = data.resolve()
    if any(p == source or source in p.parents for p in paths):
        raise ValueError('maintenance output must be outside source pack')
    if any(str(p).endswith('.lock') for p in paths):
        raise ValueError('maintenance output cannot be a lock path')


def export_review(database: Path, file: Path, ledger: Path = Path('review/decisions.jsonl')) -> dict[str,Any]:
    from .cli import write_report
    safe_paths(Path('data'),database,file,ledger)
    with connect_readonly(database) as connection:
        items = proposals(connection)
    existing = ReviewFile.model_validate_json(file.read_text()) if file.exists() else ReviewFile(proposals=[])
    old = {(p.proposal_id,p.evidence_version):p for p in existing.proposals}
    ledger_items = {(e['proposal']['proposal_id'],e['proposal']['evidence_version']):e for e in effective(read_ledger(ledger))}
    stale = list(existing.stale_proposals)
    keys = {(p.proposal_id,p.evidence_version) for p in items}
    for key,p in old.items():
        if key not in keys:
            stale.append(p)
    for p in items:
        key = p.proposal_id,p.evidence_version
        if key in old:
            if old[key].authentic() != p.authentic():
                raise ValueError('existing proposal content changed')
            p.human = old[key].human
        elif key in ledger_items:
            p.human = Decision.model_validate(ledger_items[key]['human'])
    for key,event in ledger_items.items():
        if key not in keys:
            stale.append(Proposal.model_validate({**event['proposal'],'human':event['human']}))
    unique_stale = {(p.proposal_id,p.evidence_version):p for p in stale}
    document = ReviewFile(proposals=items,stale_proposals=list(unique_stale.values()))
    write_report(file,document.model_dump())
    file.chmod(0o600)
    return {'status':'exported','proposals':len(items),'new_review':sum(p.human.decision=='defer' for p in items),'stale':len(unique_stale)}


def validate_review(database: Path, file: Path, ledger: Path = Path('review/decisions.jsonl')) -> dict[str,Any]:
    safe_paths(Path('data'),database,file,ledger)
    document = ReviewFile.model_validate_json(file.read_text())
    with connect_readonly(database) as connection:
        trusted = {(p.proposal_id,p.evidence_version):p for p in proposals(connection)}
        snapshot_revision = connection.execute('SELECT ledger_revision FROM reconciliation_metadata').fetchone()[0]
    events = read_ledger(ledger)
    active = {e['proposal']['proposal_id']:e for e in effective(events)}
    new: list[dict[str,Any]] = []
    seen = set()
    for item in document.proposals:
        key = item.proposal_id,item.evidence_version
        if key in seen:
            raise ValueError('duplicate proposal')
        seen.add(key)
        if key not in trusted or trusted[key].authentic()!=item.authentic():
            raise ValueError('proposal changed or evidence stale')
        if not item.human.reviewer:
            continue
        old = active.get(item.proposal_id)
        if old and old['proposal']==item.authentic() and old['human']==item.human.model_dump():
            continue
        body = {'previous':events[-1]['decision_id'] if events else '', 'proposal':item.authentic(),'human':item.human.model_dump()}
        event = {'decision_id':digest(body),**body}
        events.append(event)
        new.append(event)
    approved,stale = current_decisions(list(trusted.values()),events)
    if any(e['human']['decision']=='approve' and e['decision_id'] in stale for e in new):
        raise ValueError('new approval is stale')
    with connect_readonly(database) as connection:
        corrected = {row[0]:{'start_utc':row[1],'end_utc':row[2]} for row in connection.execute('SELECT id,start_utc,end_utc FROM visits')}
        for event in approved:
            action = Action.model_validate(event['proposal']['proposed_action'])
            if action.operation=='correct' and action.field in {'start_utc','end_utc'}:
                for row in connection.execute('SELECT id FROM visits WHERE job_id=?',(action.targets[0],)):
                    corrected[row[0]][str(action.field)] = action.proposed
        if any(v['start_utc'] and v['end_utc'] and v['start_utc']>=v['end_utc'] for v in corrected.values()):
            raise ValueError('review creates invalid visit interval')
    return {'status':'valid','new_events':new,'events':events,'approved':approved,'stale':stale,
            'ledger_revision':events[-1]['decision_id'] if events else '', 'snapshot_revision':snapshot_revision}


@contextmanager
def review_lock(ledger: Path):
    ledger.parent.mkdir(parents=True,exist_ok=True)
    fd = os.open(str(ledger)+'.lock',os.O_CREAT|os.O_RDWR,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def apply_review(data: Path, database: Path, file: Path, ledger: Path, *, dry_run: bool = False, fail_after: int | None = None) -> dict[str,Any]:
    import tempfile

    from .cli import ingest
    safe_paths(data,database,file,ledger)
    database.parent.mkdir(parents=True,exist_ok=True)
    with review_lock(database), review_lock(ledger):
        result = validate_review(database,file,ledger)
        with tempfile.TemporaryDirectory(prefix='.review-',dir=database.parent) as temporary:
            candidate = Path(temporary)/'candidate.sqlite'
            candidate_ledger = Path(temporary)/'decisions.jsonl'
            candidate_ledger.write_text(''.join(canonical_json(e)+'\n' for e in result['events']))
            candidate_ledger.chmod(0o600)
            ingest(data,candidate,ledger=candidate_ledger,identity_source=database)
            with connect_readonly(candidate) as connection:
                fresh = {(p.proposal_id,p.evidence_version):p for p in proposals(connection)}
                submitted = ReviewFile.model_validate_json(file.read_text())
                for old in submitted.proposals:
                    item = fresh.get((old.proposal_id,old.evidence_version))
                    if not item or item.authentic()!=old.authentic():
                        raise ValueError('source evidence changed since review')
                after = {table:{row[0]:canonical_json(row[1:]) for row in connection.execute(f'SELECT * FROM {table}')} for table in ('canonical_providers','canonical_properties','canonical_jobs','canonical_visits','canonical_estimates','service_completions','job_services')}
            with connect_readonly(database) as connection:
                before = {table:{row[0]:canonical_json(row[1:]) for row in connection.execute(f'SELECT * FROM {table}')} for table in after}
            impact = {'status':'dry_run' if dry_run else 'applied','decisions_to_record':len(result['new_events']),
                      'changes':{table:{'before_count':len(before[table]),'after_count':len(after[table]),
                                       'added_ids':sorted(after[table].keys()-before[table].keys()),
                                       'removed_ids':sorted(before[table].keys()-after[table].keys()),
                                       'changed_ids':sorted(k for k in before[table].keys() & after[table].keys() if before[table][k]!=after[table][k])} for table in after},
                      'history_consequences':'Derived job/property changes listed above; original observations preserved.',
                      'availability_consequences':'Corrected intervals and provider links will feed P3; availability is not implemented.',
                      'ledger_revision':result['ledger_revision'],'stale_decisions':len(result['stale'])}
            if dry_run:
                return impact
            ledger.parent.mkdir(parents=True,exist_ok=True)
            fd = os.open(ledger,os.O_CREAT|os.O_APPEND|os.O_WRONLY,0o600)
            with os.fdopen(fd,'a') as handle:
                for event in result['new_events']:
                    handle.write(canonical_json(event)+'\n')
                handle.flush()
                os.fsync(handle.fileno())
            directory = os.open(ledger.parent,os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            try:
                if fail_after is not None:
                    raise ValueError('injected failure after recording decisions')
                from .publication import publish
                publish(candidate,database)
            except Exception as exc:
                raise ValueError('decisions recorded but not applied; rebuild to recover') from exc
            try:
                directory = os.open(database.parent,os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            except OSError:
                impact['warning'] = 'Snapshot published but directory durability unconfirmed.'
            return impact

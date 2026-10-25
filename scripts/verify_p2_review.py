"""Exercise review decisions on sanitized observations, never on the supplied pack."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from p2_fixture import build

from house_account.review import apply_review, export_review, read_ledger
from house_account.storage import connect_readonly


def main():
    target = Path(sys.argv[1]) if len(sys.argv)>1 else Path('artifacts/P2/review/sanitized-workflow.json')
    receipts = []
    with tempfile.TemporaryDirectory(prefix='p2-review-') as directory:
        root = Path(directory)
        database,file,ledger = [root/name for name in ('db.sqlite','reconciliation.json','decisions.jsonl')]
        build(database,ledger)
        receipts.append(export_review(database,file,ledger))
        document=json.loads(file.read_text())
        for p in document['proposals']:
            p['human']={'decision':'approve' if p['kind']=='field_correction' else 'reject','reviewer':'Sanitized fixture reviewer','reason':'Demonstration only; no source-pack approval','decided_at':'2026-10-24T12:00:00Z'}
        file.write_text(json.dumps(document))
        def ingest(data,database,ledger,**kwargs):
            return build(database,ledger)
        with patch('house_account.cli.ingest',ingest):
            before=database.read_bytes()
            receipts.append(apply_review(root/"input",database,file,ledger,dry_run=True))
            assert before==database.read_bytes() and not ledger.exists()
            receipts.append(apply_review(root/"input",database,file,ledger))
            receipts.append(apply_review(root/"input",database,file,ledger))
            assert receipts[-1]['decisions_to_record']==0
            active={e['proposal']['proposal_id']:e['decision_id'] for e in read_ledger(ledger)}
            for p in document['proposals']:
                if p['kind']=='field_correction':
                    p['human'].update(decision='defer',reason='Demonstrate reversing a derived correction',supersedes_decision_id=active[p['proposal_id']])
            file.write_text(json.dumps(document))
            receipts.append(apply_review(root/"input",database,file,ledger))
            build(database,ledger)
            with connect_readonly(database) as c:
                assert c.execute("SELECT count(DISTINCT job_id) FROM canonical_visits WHERE scheduled_start_state='disputed'").fetchone()[0]==1
            receipts.append({'rebuild_reproduced_supersession':True,'ledger_events':len(read_ledger(ledger))})
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'fixture':'sanitized only','receipts':receipts,'passed':True},indent=2)+'\n')
    print(json.dumps({'status':'passed','receipt':str(target)}))


if __name__=='__main__':
    main()

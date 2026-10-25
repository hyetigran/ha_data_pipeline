"""Run the real review CLI against an isolated copy of the local snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, default=Path('var/house_account.sqlite'))
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/P2R/review-cli.json'))
    args = parser.parse_args()
    original = sha(args.database)
    receipts = []
    with tempfile.TemporaryDirectory(prefix='p2-cli-review-') as directory:
        root = Path(directory)
        database, file, ledger = root/'snapshot.sqlite', root/'review.json', root/'decisions.jsonl'
        with sqlite3.connect(args.database) as source, sqlite3.connect(database) as target:
            source.backup(target)

        def drive(action: str, *, dry: bool = False, data: Path = args.data, expected: int = 0) -> dict:
            command = [sys.executable, '-m', 'house_account.cli', 'review', action,
                       '--data', str(data), '--database', str(database), '--file', str(file), '--ledger', str(ledger)]
            if dry:
                command.append('--dry-run')
            proc = subprocess.run(command, capture_output=True, text=True, check=False)
            assert proc.returncode == expected, (proc.returncode, proc.stderr)
            result = json.loads(proc.stdout if proc.returncode == 0 else proc.stderr)
            receipts.append({'command': command, 'exit_code': proc.returncode, 'result': result})
            return result

        drive('export')
        doc = json.loads(file.read_text())
        assert all(p['human']['decision'] == 'defer' and not p['human']['reviewer'] for p in doc['proposals'])
        assert all(p['observations'] for p in doc['proposals'])
        decisions = {'approve': 0, 'reject': 0, 'defer': 0}
        for p in doc['proposals']:
            choice = 'approve' if p['kind'] == 'field_correction' else 'reject' if decisions['reject'] == 0 else 'defer'
            p['human'] = {'decision': choice, 'reviewer': 'Automated isolated CLI test',
                          'decided_at': '2026-10-24T15:00:00Z', 'supersedes_decision_id': None, 'reason': 'Test-only decision in disposable snapshot; not approval of active data.'}
            decisions[choice] += 1
        assert all(decisions.values()), decisions
        file.write_text(json.dumps(doc))
        edit_bytes = file.read_bytes()
        drive('export')
        assert json.loads(file.read_text()) == json.loads(edit_bytes)
        def correction_state() -> dict:
            result = {}
            with sqlite3.connect(database) as db:
                for item in doc['proposals']:
                    action = item['proposed_action']
                    if item['kind'] != 'field_correction':
                        continue
                    canonical = db.execute("SELECT canonical_id FROM canonical_crosswalk WHERE kind='job' AND source_id=?", (action['targets'][0],)).fetchone()[0]
                    if action['field'] == 'address':
                        result[item['proposal_id']] = db.execute("SELECT p.house_number FROM canonical_jobs j JOIN canonical_properties p ON p.id=j.property_id WHERE j.id=?", (canonical,)).fetchone()[0]
                    else:
                        column = {'start_utc': 'scheduled_start_utc', 'end_utc': 'scheduled_end_utc'}[action['field']]
                        result[item['proposal_id']] = db.execute(f'SELECT {column} FROM canonical_visits WHERE job_id=?', (canonical,)).fetchone()[0]
            return result

        original_corrections = correction_state()
        before = sha(database)
        drive('validate')
        drive('apply', dry=True)
        assert sha(database) == before and not ledger.exists()
        drive('apply')
        applied_corrections = correction_state()
        for item in doc['proposals']:
            if item['kind'] == 'field_correction':
                expected_value = 5823 if item['proposed_action']['field'] == 'address' else item['proposed_action']['proposed']
                assert applied_corrections[item['proposal_id']] == expected_value
        events = ledger.read_bytes()
        repeat = drive('apply')
        assert repeat['decisions_to_record'] == 0 and ledger.read_bytes() == events
        active = {e['proposal']['proposal_id']: e['decision_id'] for e in map(json.loads, ledger.read_text().splitlines())}
        for p in doc['proposals']:
            if p['human']['decision'] == 'approve':
                p['human'].update(decision='defer', reason='Test-only supersession restores original derived facts.', supersedes_decision_id=active[p['proposal_id']])
        file.write_text(json.dumps(doc))
        drive('apply', dry=True)
        drive('apply')
        assert correction_state() == original_corrections
        with sqlite3.connect(database) as db:
            assert db.execute("SELECT count(*) FROM canonical_visits WHERE scheduled_start_state='disputed'").fetchone()[0] > 0
        changed = root/'changed-data'
        shutil.copytree(args.data, changed)
        path = changed/'sources/workiz/lakewood_air/jobs.json'
        payload = json.loads(path.read_text())
        jobs = payload['data']
        item = next(j for j in jobs if j['UUID'] == 'J8OMKP')
        item['verification_only_changed_evidence'] = True
        path.write_text(json.dumps(payload))
        before, ledger_before = sha(database), sha(ledger)
        drive('validate', data=changed, expected=1)
        assert sha(database) == before and sha(ledger) == ledger_before
        assert sha(args.database) == original
        outcome = {'status': 'pass', 'scope': 'Disposable snapshot and ledger only; active database unchanged.',
                   'decisions_tested': decisions, 'exact_correction_effects_and_reversal': True, 'ledger_events': len(ledger.read_text().splitlines()), 'receipts': receipts}
    outcome['scratch_removed'] = not root.exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outcome, indent=2) + '\n')
    print(json.dumps({k: v for k, v in outcome.items() if k != 'receipts'}))


if __name__ == '__main__':
    main()

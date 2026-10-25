"""Check real-pack answers against source records inspected independently of P2."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from house_account.queries import (
    block_schedule,
    history_radius,
    property_history,
    provider_summary,
)

BELMONT_COMPLETED = {
    '5df8011118a61c258916e8153a61ed38377c814e110dff87ed603fa9739bdbc2',
    '60f85781e122366899719586c3270ae9d7c41b793b9deabb5dc6fb4281cb9cbf',
    'd0a3ca3f1955d40113672338400e4a82da91ff0396759a15afe521c6c4025702',
    '0c4d423ed527e88680559b42a6142c01860ac7ebff4137cd6f2d0aa10a4dbce4',
}
LIVE_OAK_VISITS = {
    'c72f66e851e00492cae3b01c88cad65f581c4afdeccd6595824289ba4b49ed84',
    '53ce7fe60db1a338f662a95086144c802011f0d91b56664c518c23e917fec6ed',
    '1c5d4aba9423068dc59166003ee0edd7e2c20c2d0ea9730a82a3ad994f5f276c',
    '27a4df938a31b6d6a86190695fddfcdfdf92be090415ac83e60166f5d2979629',
}
LONE_STAR = 'db1994aaa58753691d5420714a4338da957be044d08b62befd3552b4ac872e5c'
FORBIDDEN = {'raw', 'raw_json', 'attributes_json', 'phone', 'email', 'owner_name',
             'customer_name', 'customer_id', 'reviewer', 'reason', 'source_path',
             'file', 'locator', 'summary', 'description', 'notes', 'original'}


def inspect_public(value: object) -> None:
    if isinstance(value, dict):
        assert not FORBIDDEN.intersection(value), FORBIDDEN.intersection(value)
        for child in value.values():
            inspect_public(child)
    elif isinstance(value, list):
        for child in value:
            inspect_public(child)
    elif isinstance(value, str):
        assert 'sources/' not in value
        assert '@' not in value


def verify(database: Path) -> dict:
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
        assert db.execute('SELECT count(*) FROM source_records').fetchone()[0] == 46092
        assert db.execute('SELECT count(*) FROM occurrences').fetchone()[0] == 46888
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        aliases = db.execute("SELECT DISTINCT x.canonical_id FROM providers p JOIN canonical_crosswalk x ON x.source_id=p.id AND x.kind='provider' WHERE p.display_name IN ('Big D Handyman','Lakewood Home Repair')").fetchall()
        assert len(aliases) == 1
        provider = db.execute("SELECT canonical_id FROM canonical_crosswalk WHERE kind='provider' AND source_id=?", (LONE_STAR,)).fetchone()[0]
        for source_id in ('dbe191fcdbd50b587ed27e5dc5b412d0b431b86b7ce926f91fd6fa0ddea9a1ec', '32032094cd72254a1352c59a95030e004480306ed5ec72d7f0d39340dff0e307'):
            job = db.execute("SELECT canonical_id FROM canonical_crosswalk WHERE kind='job' AND source_id=?", (source_id,)).fetchone()[0]
            assert db.execute('SELECT count(*) FROM job_services WHERE job_id=?', (job,)).fetchone()[0] == 2
            assert db.execute('SELECT count(*) FROM service_completions WHERE job_id=?', (job,)).fetchone()[0] == 1
            assert db.execute('SELECT count(*) FROM completion_services cs JOIN service_completions c ON c.id=cs.completion_id WHERE c.job_id=?', (job,)).fetchone()[0] == 0

    exact = property_history(database, '5823 Belmont Ave, Dallas, TX 75206')
    assert exact['results']['distinct_jobs'] == 4
    assert {ref for job in exact['results']['jobs'] for ref in job['evidence_refs']} == BELMONT_COMPLETED
    assert any('58192acd3f3b3b28bb597998cfa1994c3c5ca481505c76747c03e61f6bf6c374' in j['evidence_refs'] for j in exact['results']['other_or_uncertain_jobs'])
    block = block_schedule(database, '4512 Live Oak St, Dallas, TX 75204')
    assert {visit['visit_id'] for visit in block['results']} == LIVE_OAK_VISITS
    assert any('e7f968099577fec7ae0669496c6b7d20c448abf89259162955187d5d467ea664' in j['evidence_refs'] for j in block['uncertain_candidates'])
    summary = provider_summary(database, provider)
    assert summary['results']['completed_distinct_jobs'] == 262
    assert set(summary['results']['service_zips']) == {'75206', '75214', '75204', '75219', '75223'}
    assert summary['results']['opening_status'] == 'not_implemented_until_P3'
    radius = history_radius(database, '4512 Live Oak St, Dallas, TX 75204')
    # Two combined patch/paint jobs retain completion but lack service-specific attribution.
    assert sum(row['distinct_jobs'] for row in radius['results']) == 969
    for response in (exact, block, summary, radius):
        inspect_public(response)
    return {'status': 'pass', 'source_records': 46092, 'occurrences': 46888,
            'belmont_completed_jobs': 4, 'live_oak_active_crm_visits': 4,
            'lone_star_completed_jobs': 262, 'public_projection_checked': True,
            'radius_distinct_jobs': sum(row['distinct_jobs'] for row in radius['results']),
            'radius_golden_count': 969}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, default=Path('var/house_account.sqlite'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/P2R/independent-verification.json'))
    args = parser.parse_args()
    result = verify(args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

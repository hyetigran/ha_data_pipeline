import json

from p2_fixture import build

from house_account.queries import (
    block_schedule,
    history_radius,
    property_history,
    provider_summary,
)


def test_questions_distinct_jobs_and_visits(tmp_path):
    db = tmp_path/'db'
    build(db,tmp_path/'ledger')
    home = property_history(db,'4501 Example St Apt 4, Dallas, TX 75214')['results']
    assert home['distinct_jobs']==2
    assert len(home['other_or_uncertain_jobs'])==1
    assert property_history(db,'4501 Example St #5, Dallas, TX 75214')['results']['distinct_jobs']==1
    radius = history_radius(db,'4501 Example St, Dallas, TX 75214')['results']
    assert sum(r['distinct_jobs'] for r in radius)==3
    assert len(block_schedule(db,'4500 Example St, Dallas, TX 75214')['results'])==4
    summary = provider_summary(db,radius[0]['provider_id'])['results']
    assert summary['completed_distinct_jobs']==3
    assert summary['openings'] is None


def test_half_mile_boundary_and_privacy(tmp_path):
    from math import degrees

    from p2_fixture import fixture
    db = tmp_path/'db'
    observations = fixture()
    segment = next(o for o in observations if o.kind == 'street_segment')
    segment.normalized.attributes.update(from_number=4500, to_number=4501,
                                        start_lat=0.0, start_lon=0.0,
                                        end_lat=degrees(0.5 / 3958.7613), end_lon=0.0)
    build(db, tmp_path/'ledger', observations)
    assert sum(r['distinct_jobs'] for r in history_radius(db,'4500 Example St, Dallas, TX 75214',0.5)['results'])==3
    assert history_radius(db,'4500 Example St, Dallas, TX 75214',0.49999)['results']==[]
    result = json.dumps(property_history(db,'4501 Example St #4, Dallas, TX 75214'))
    for forbidden in ['214555','raw_json','fixture.json','phone','customer','instructions']:
        assert forbidden not in result


def test_full_texas_state_name_preserves_property_history(tmp_path):
    database = tmp_path / 'db'
    build(database, tmp_path / 'ledger')
    expected = property_history(database, '4501 Example St Apt 4, Dallas, TX 75214')
    assert expected['results']['distinct_jobs'] == 2
    for state in ('Texas', 'texas', 'TEXAS'):
        actual = property_history(database, f'4501 Example St Apt 4, Dallas, {state} 75214')
        assert actual == expected

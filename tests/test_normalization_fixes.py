import csv
from pathlib import Path

import pytest
from p2_fixture import build, fixture

from house_account import privacy
from house_account.addresses import normalize
from house_account.queries import history_radius, property_history


@pytest.mark.parametrize(('label','expected'),[
    ('Gutter clean out','gutters'),('gutters cleaned','gutters'),
    ('Drain cleaning','drain'),('Standard clean','cleaning'),
    ('WH replace','water_heater'),('WH no hot water','water_heater'),
    ('Tankless conversion','water_heater'),('assemble IKEA','furniture_assembly'),
    ('furniture build','furniture_assembly'),('Hang TV + hide wires','tv_mounting'),
    ('tv install 65in','tv_mounting'),('EV charger install','electrical'),
    ('GFCI replace','electrical'),('Hydro jet','drain'),
    ('fridge not cooling','appliance_repair'),('washing machine fix','appliance_repair'),
    ('leak in roof','roofing'),('roof leak repair','roofing'),
    ('washer not draining','appliance_repair'),('Heating repair','hvac'),
    ('Leaf cleanup','landscaping'),('Light fixture install','electrical'),
])
def test_clear_pack_service_aliases(label,expected):
    assert privacy.service(label)==expected


def test_service_context_and_compounds_do_not_guess_vague_work():
    assert privacy.service('No cool')=='other'
    assert privacy.service('No cool',('hvac',))=='hvac'
    assert privacy.service('No cool',('hvac','appliance_repair'))=='other'
    assert privacy.service('fall cleanup',('landscaping',))=='landscaping'
    for label in ('spray','changeout','seasonal maintenance','pilot light out'):
        assert privacy.service(label,('hvac','plumbing','pest_control'))=='other'
    assert privacy.service_codes('Patch & paint drywall')=={'handyman','painting'}
    assert privacy.service_codes('Hang TV + hide wires')=={'tv_mounting'}
    assert privacy.service_codes('Toilet repair + WH replace')=={'plumbing','water_heater'}
    assert privacy.service_codes('No cool + broken spring',iter(('hvac','garage_doors')))=={'hvac','garage_door'}
    assert privacy.service('not a WH replacement')=='other'


def test_pack_address_formats_preserve_unit_and_source():
    with Path('data/reference/street_segments.csv').open() as handle:
        segments=list(csv.DictReader(handle))
    raw='6399 Abrams Rd., A, Dallas, TX 75214'
    actual=normalize(raw,segments)
    expected=normalize({'street':'6399 abrams rd','street_line_2':'A','city':'Dallas',
                        'state':'TX','zip':'75214-7530'},segments)
    assert actual.key==expected.key and actual.precision=='street_segment_interpolation'
    assert actual.original==raw and actual.unit=='a'
    assert normalize('6399 Abrams Rd., B, Dallas, TX 75214',segments).key!=actual.key
    assert normalize('6399 Abrams Rd, Dallas, TX 75214',segments).key!=actual.key
    assert normalize('6600 Abrams Rd dallas',segments).key==normalize(
        '6600 Abrams Rd, Dallas, TX 75214',segments).key
    assert normalize('6159 McMillan AVE, B dallas',segments).key==normalize(
        '6159 McMillan Ave Apt B, Dallas, TX 75206',segments).key
    assert normalize('4501 Dallas St',[]).street=='dallas st'
    assert normalize('4501 Example St dallas',[]).city=='dallas'
    assert normalize('4501 Example St dallas',[]).precision=='missing'
    assert normalize('4501 Example St, Dallas, XX nonsense',[]).state==''
    assert normalize('4501 Example St, Unknown, Dallas, TX 75214',[]).unit==''
    assert normalize('4501 Example St, Plano, Dallas, TX 75214',[]).key is None
    assert normalize('4501 Example St Apt 4, 5, Dallas, TX 75214',[]).key is None
    assert normalize('5690 Blemont Ave',segments).precision=='missing'
    assert normalize('123 Cottonwood Trail, Dallas, TX 75019',segments).street=='cottonwood trl'
    assert normalize('123 Cottonwood Trail, Dallas, TX 75019',segments).precision=='missing'


@pytest.mark.parametrize(('label','trade','service'),[
    ('Gutter cleaning','gutters','gutters'),('WH replace','plumbing','water_heater'),
    ('Hang TV + hide wires','handyman','tv_mounting'),
    ('leak in roof','roofing','roofing'),('washer not draining','appliance_repair','appliance_repair'),
])
def test_classification_reaches_completed_history_without_spurious_unknown(tmp_path,label,trade,service):
    observations=fixture()
    for o in observations:
        if o.kind=='job':
            o.normalized.service=label
    db=tmp_path/'snapshot.sqlite'
    build(db,tmp_path/'no-decisions.jsonl',observations)
    groups=history_radius(db,'4501 Example St, Dallas, TX 75214')['results']
    assert {g['trade'] for g in groups}=={trade}
    home=property_history(db,'4501 Example St, 4, Dallas, TX 75214')['results']
    assert home['distinct_jobs']==2
    for job in home['jobs']:
        assert {s['service_code'] for s in job['services']}=={service}
    assert len(home['other_or_uncertain_jobs'])==1


def test_patch_and_paint_keeps_distinct_scope_without_fabricating_completion_credit(tmp_path):
    observations=fixture()
    for o in observations:
        if o.kind=='job':
            o.normalized.service='Patch & paint drywall'
    db=tmp_path/'snapshot.sqlite'
    build(db,tmp_path/'no-decisions.jsonl',observations)
    assert history_radius(db,'4501 Example St, Dallas, TX 75214')['results']==[]
    home=property_history(db,'4501 Example St, 4, Dallas, TX 75214')['results']
    assert home['distinct_jobs']==2
    for job in home['jobs']:
        assert {s['service_code'] for s in job['services']}=={'handyman','painting'}
        assert job['completion_supported_services']==[]
        assert all(c['service_attribution']=='unattributed' for c in job['service_completions'])

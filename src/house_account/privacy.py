from __future__ import annotations

import re
from collections.abc import Iterable

SERVICES = {
    'gate_repair': ('gate fix','gate repair'),
    'tv_mounting': ('tv mount','mount tv','mounting tv'),
    'furniture_assembly': ('furniture assembl','assemble furniture'),
    'water_heater': ('water heater', 'waterheater'),
    'roofing': ('roof','shingle'),
    'gutters': ('gutter',),
    'drain': ('drain','sewer','clog'),
    'leak': ('leak', 'pipe'),
    'hvac': ('hvac','a/c','ac tune','ac repair','air condition','furnace','heat pump','thermostat'),
    'electrical': ('electri','outlet','breaker','panel','lighting','ceiling fan'),
    'garage_door': ('garage','torsion','opener'),
    'plumbing': ('plumb','toilet','faucet','disposal','sink'),
    'landscaping': ('lawn','mow','landscap','hedge','tree','yard','mulch'),
    'cleaning': ('clean','maid'),
    'pest_control': ('pest','termite','roach','rodent','ant treatment','ant control'),
    'painting': ('paint',),
    'appliance_repair': ('appliance','dishwasher','washer','dryer','refrigerator','oven'),
    'handyman': ('handyman','drywall','paint','door','fixture','repair'),
}
TRADES = {'gate_repair':'handyman','tv_mounting':'handyman','furniture_assembly':'handyman','water_heater':'plumbing','drain':'plumbing','leak':'plumbing','garage_door':'garage_doors'}

ALIASES = {
    'water_heater': ('wh replace','wh no hot water','tankless conversion'),
    'tv_mounting': ('hang tv hide wires','tv install 65in'),
    'furniture_assembly': ('assemble ikea','furniture build'),
    'handyman': ('replace fence pickets','fence boards'),
    'drain': ('hydro jet','main line clear'),
    'hvac': ('ac not cooling','ac service call','heating repair'),
    'electrical': ('ev charger install','tesla wall charger','gfci replace',
                   'can lights x6','recessed lights','switch replace','light fixture install'),
    'appliance_repair': ('fridge not cooling','washing machine fix','washer not draining'),
    'landscaping': ('aeration','core aeration','aerate seed','leaf cleanup'),
    'pest_control': ('wdi inspection','rats in attic'),
    'garage_door': ('liftmaster install',),
}
EXACT_ALIASES = {label:category for category,labels in ALIASES.items() for label in labels}
COMPOUND_SERVICES = {'patch paint drywall': {'handyman','painting'}}
CONTEXTUAL_ALIASES = {
    'no cool': {'hvac':'hvac','appliance_repair':'appliance_repair'},
    'no heat': {'hvac':'hvac'},
    'spring replacement': {'garage_doors':'garage_door'},
    'broken spring': {'garage_doors':'garage_door'},
    'move out': {'cleaning':'cleaning'},
    'ice maker': {'appliance_repair':'appliance_repair'},
    'level 2 charger': {'electrical':'electrical'},
    'leaf guards': {'gutters':'gutters'},
    'hail inspection': {'roofing':'roofing'},
    'fall cleanup': {'landscaping':'landscaping'},
}


def alias_key(value: str | None) -> str:
    return re.sub(r'[^a-z0-9]+',' ',(value or '').lower()).strip()


def service(value: str | None, declared_trades: Iterable[str] = ()) -> str:
    key = alias_key(value)
    if key in EXACT_ALIASES:
        return EXACT_ALIASES[key]
    if key in CONTEXTUAL_ALIASES:
        declared_trades = frozenset(declared_trades)
        candidates = {category for trade,category in CONTEXTUAL_ALIASES[key].items()
                      if trade in declared_trades}
        return next(iter(candidates)) if len(candidates)==1 else 'other'
    text = (value or '').lower()
    return next((key for key, tokens in SERVICES.items() if any(token in text for token in tokens)), 'other')


def service_codes(value: str | None, declared_trades: Iterable[str] = ()) -> set[str]:
    declared_trades = tuple(declared_trades)
    if alias_key(value) in COMPOUND_SERVICES:
        return set(COMPOUND_SERVICES[alias_key(value)])
    if alias_key(value) in EXACT_ALIASES:
        return {EXACT_ALIASES[alias_key(value)]}
    return {service(part,declared_trades) for part in re.split(r'\s+(?:and|&)\s+|[+;]',value or '')}


def trade(value: str | None) -> str:
    normalized = re.sub(r'[^a-z]', '', (value or '').lower())
    exact = {'pestcontrol':'pest_control','lawncare':'landscaping','lawn':'landscaping','garagedoor':'garage_doors','garagedoors':'garage_doors','appliancerepair':'appliance_repair','electrical':'electrical','plumbing':'plumbing','handyman':'handyman','painting':'painting','roofing':'roofing','gutters':'gutters','cleaning':'cleaning','landscaping':'landscaping'}
    if normalized in exact:
        return exact[normalized]
    if normalized in {'hvac','heatingcooling'}:
        return 'hvac'
    key = service(value)
    return TRADES.get(key, key)

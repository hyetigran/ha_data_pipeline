from __future__ import annotations

import re

SERVICES = {
    'gate_repair': ('gate fix','gate repair'),
    'tv_mounting': ('tv mount','mount tv','mounting tv'),
    'furniture_assembly': ('furniture assembl','assemble furniture'),
    'water_heater': ('water heater', 'waterheater'),
    'drain': ('drain','sewer','clog'),
    'leak': ('leak', 'pipe'),
    'hvac': ('hvac','a/c','ac tune','ac repair','air condition','furnace','heat pump','thermostat'),
    'electrical': ('electri','outlet','breaker','panel','lighting','ceiling fan'),
    'garage_door': ('garage','torsion','opener'),
    'plumbing': ('plumb','toilet','faucet','disposal','sink'),
    'landscaping': ('lawn','mow','landscap','hedge','tree','yard','mulch'),
    'cleaning': ('clean','maid'),
    'pest_control': ('pest','termite','roach','rodent','ant treatment','ant control'),
    'roofing': ('roof','shingle'),
    'gutters': ('gutter',),
    'painting': ('paint',),
    'appliance_repair': ('appliance','dishwasher','washer','dryer','refrigerator','oven'),
    'handyman': ('handyman','drywall','paint','door','fixture','repair'),
}
TRADES = {'gate_repair':'handyman','tv_mounting':'handyman','furniture_assembly':'handyman','water_heater':'plumbing','drain':'plumbing','leak':'plumbing','garage_door':'garage_doors'}


def service(value: str | None) -> str:
    text = (value or '').lower()
    return next((key for key, tokens in SERVICES.items() if any(token in text for token in tokens)), 'other')


def trade(value: str | None) -> str:
    normalized = re.sub(r'[^a-z]', '', (value or '').lower())
    exact = {'pestcontrol':'pest_control','lawncare':'landscaping','lawn':'landscaping','garagedoor':'garage_doors','garagedoors':'garage_doors','appliancerepair':'appliance_repair','electrical':'electrical','plumbing':'plumbing','handyman':'handyman','painting':'painting','roofing':'roofing','gutters':'gutters','cleaning':'cleaning','landscaping':'landscaping'}
    if normalized in exact:
        return exact[normalized]
    if normalized in {'hvac','heatingcooling'}:
        return 'hvac'
    key = service(value)
    return TRADES.get(key, key)

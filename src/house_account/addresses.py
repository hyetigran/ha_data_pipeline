from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any

SUFFIXES = {'street':'st','avenue':'ave','boulevard':'blvd','drive':'dr','lane':'ln','road':'rd','court':'ct','place':'pl','parkway':'pkwy','circle':'cir','terrace':'ter'}


def words(value: Any) -> str:
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', str(value or '').lower()).split())


def street_name(value: str) -> str:
    return ' '.join(SUFFIXES.get(word, word) for word in words(value).split())


@dataclass(frozen=True)
class Address:
    number: int | None
    street: str
    unit: str
    city: str
    state: str
    postal_code: str
    original: Any
    latitude: float | None = None
    longitude: float | None = None
    precision: str = 'missing'
    segment_key: str | None = None
    fraction: float | None = None

    @property
    def key(self) -> tuple[Any, ...] | None:
        if self.number is None or not self.street or not self.city or not self.state:
            return None
        return self.number, self.street, self.unit, self.city, self.state, self.postal_code

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize(value: Any, segments: list[dict[str, Any]]) -> Address:
    original = value
    if isinstance(value, str):
        parts = value.split(',')
        street, unit = parts[0], ''
        city, state, postal = '', '', ''
        if len(parts) > 1:
            locality = parts[1].strip()
            if re.fullmatch(r'\d{5}(?:-\d{4})?', locality):
                postal = locality[:5]
            else:
                city = locality
        if len(parts) > 2:
            match = re.search(r'([A-Za-z]{2})\s*(\d{5})?', parts[2])
            if match:
                state, postal = match[1], match[2] or ''
    else:
        value = value or {}
        street = value.get('street1', value.get('street', value.get('Address', '')))
        unit = value.get('street2', value.get('street_line_2', value.get('Unit', ''))) or ''
        city = value.get('city', value.get('City', '')) or ''
        state = value.get('province', value.get('state', value.get('State', ''))) or ''
        postal = value.get('postalCode', value.get('zip', value.get('PostalCode', ''))) or ''
    unit_match = re.search(r'(?:\bapt\.?|\bunit|\bsuite|#)\s*([\w-]+)\s*$', str(street), re.IGNORECASE)
    if unit_match:
        unit = unit_match[1]
        street = street[:unit_match.start()]
    unit = re.sub(r'^(apt\.?|unit|suite|#)\s*', '', str(unit).strip(), flags=re.IGNORECASE)
    match = re.match(r'^\s*(\d+)\s+(.+?)\s*$', str(street))
    number, street = (int(match[1]), street_name(match[2])) if match else (None, street_name(street))
    city, state, postal = words(city), words(state), str(postal).strip()[:5]
    state = {'texas':'tx'}.get(state,state)
    candidates = [s for s in segments if street_name(s['street_name']+' '+s['street_type']) == street
                  and number is not None and int(s['from_number']) <= number <= int(s['to_number'])
                  and (not city or words(s['city']) == city) and (not state or words(s['state']) == state)
                  and (not postal or s['zip'] == postal)]
    geo: dict[str, Any] = {}
    if len(candidates) == 1:
        s = candidates[0]
        city, state, postal = words(s['city']), words(s['state']), s['zip']
        width = int(s['to_number']) - int(s['from_number'])
        fraction = (int(number or 0)-int(s['from_number']))/width if width else 0.0
        geo = {'latitude':float(s['start_lat']) + fraction*(float(s['end_lat'])-float(s['start_lat'])),
               'longitude':float(s['start_lon']) + fraction*(float(s['end_lon'])-float(s['start_lon'])),
               'precision':'street_segment_interpolation', 'fraction':fraction,'segment_key':s.get('id')}
    return Address(number, street, str(unit).strip().lower(), city, state, postal, original, **geo)


def distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = p2-p1, math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dlon/2)**2
    return 3958.7613*2*math.atan2(math.sqrt(a), math.sqrt(max(0,1-a)))

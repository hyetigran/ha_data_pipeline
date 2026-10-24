from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal['provider', 'customer', 'property', 'job', 'estimate', 'visit', 'calendar_block', 'profile', 'street_segment']


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def identity(source: str, account: str, kind: str, key: str) -> str:
    return digest([source, account, kind, str(key)])


class Issue(BaseModel):
    code: str
    field: str = ''
    detail: str = ''


class Entity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Kind
    provider_id: str | None = None
    property_id: str | None = None
    customer_id: str | None = None
    job_id: str | None = None
    estimate_id: str | None = None
    display_name: str | None = None
    trade: str | None = None
    service: str | None = None
    status: str | None = None
    source_status: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    start_utc: str | None = None
    end_utc: str | None = None
    timezone_origin: str | None = None
    appointment_kind: Literal['job', 'estimate'] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    source: str
    account: str
    kind: Kind
    key: str
    file: str
    locator: str
    raw: dict[str, Any]
    normalized: Entity
    issues: list[Issue] = Field(default_factory=list)
    snapshot_at: str | None = None
    rule: str = 'source-local-v1'

    @property
    def id(self) -> str:
        return identity(self.source, self.account, self.kind, self.key)


def money(value: Any, *, cents: bool = False) -> int | None:
    if value is None or str(value).strip() == '':
        return None
    try:
        number = Decimal(str(value).replace('$', '').replace(',', '').strip())
        minor = number if cents else number * 100
        if not minor.is_finite() or minor != minor.to_integral_value():
            raise ValueError('money requires exact minor units')
        return int(minor)
    except InvalidOperation as exc:
        raise ValueError('invalid money') from exc


def instant(value: Any, *, local_zone: str = 'America/Chicago') -> str | None:
    if value is None or str(value).strip() == '':
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        zone = ZoneInfo(local_zone)
        candidates = [parsed.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
        valid = [item for item in candidates if item.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == parsed]
        if not valid or len({item.utcoffset() for item in valid}) > 1:
            raise ValueError('ambiguous or nonexistent local time')
        parsed = valid[0]
    return parsed.astimezone(UTC).isoformat()

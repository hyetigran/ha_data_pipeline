from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Assertion(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ProviderAssertion(Assertion):
    display_name: str | None = None
    trade: str | None = None


class CustomerAssertion(Assertion):
    provider_id: str | None = None
    display_name: str | None = None


class PropertyAssertion(Assertion):
    provider_id: str | None = None
    customer_id: str | None = None
    house_number: int | None = None
    street: str | None = None
    unit: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


class JobAssertion(Assertion):
    provider_id: str
    property_id: str | None = None
    customer_id: str | None = None
    trade: str | None = None
    service: str | None = None
    status: str | None = None
    source_status: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    source_status_updated_at: str | None = None


class EstimateAssertion(JobAssertion):
    pass


class VisitAssertion(Assertion):
    provider_id: str
    property_id: str | None = None
    customer_id: str | None = None
    job_id: str | None = None
    estimate_id: str | None = None
    status: str | None = None
    source_status: str | None = None
    start_utc: str | None = None
    end_utc: str | None = None
    timezone_origin: str | None = None
    appointment_kind: Literal['job','estimate']
    source_completed_at: str | None = None


class CalendarAssertion(Assertion):
    uid: str | None = None
    start_local: str | None = None
    end_local: str | None = None
    all_day: bool | None = None
    end_exclusive: bool | None = None
    rrule: str | None = None
    recurrence_id: str | None = None
    transparency: str | None = None
    provider_id: str
    status: str | None = None
    source_status: str | None = None
    start_utc: str | None = None
    end_utc: str | None = None
    timezone_origin: str | None = None


class ProfileAssertion(Assertion):
    provider_id: str
    display_name: str | None = None


class StreetAssertion(Assertion):
    street_name: str
    street_type: str
    city: str
    state: str
    zip: str
    from_number: int
    to_number: int
    start_lat: float
    end_lat: float
    start_lon: float
    end_lon: float


MODELS: dict[str,type[Assertion]] = {
    'provider':ProviderAssertion,'customer':CustomerAssertion,'property':PropertyAssertion,
    'job':JobAssertion,'estimate':EstimateAssertion,'visit':VisitAssertion,
    'calendar_block':CalendarAssertion,'profile':ProfileAssertion,'street_segment':StreetAssertion,
}

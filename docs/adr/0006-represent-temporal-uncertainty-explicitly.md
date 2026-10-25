# Time values and uncertainty

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

A missing timestamp cannot distinguish an absent date from a disputed year or an ambiguous daylight-saving transition. Q9 therefore separates the value from its evidence state.

Q16 defines a selected UTC instant, an independently established local date, an evidence state, a precision, and a timezone for each scheduled endpoint. Evidence states are `known`, `missing`, `ambiguous`, and `disputed`. Precision is `instant`, `date`, or `unknown`.

An ambiguous or disputed time has no selected UTC instant. A supported local date can remain. Alternate interpretations stay in evidence. Date-only facts do not become midnight appointments.

Schedule time, completion time, and source status-update time remain distinct. SQL checks reject inconsistent combinations.

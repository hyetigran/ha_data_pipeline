# Visit ownership through one parent

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

A canonical visit belongs to exactly one job or estimate. SQL enforces that relationship. The visit derives its provider and property through its parent instead of storing competing copies.

Q13 accepts an extra join to prevent inconsistent ownership. Worker assignments remain evidence about workers, not a replacement for provider identity.

The model assumes one provider and at most one resolved property per job or estimate. A project involving several providers or properties needs an explicit extension. Conflicting source assertions remain preserved.

# Related provider facts

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Provider aliases, trades, exclusions, and declared service areas use related tables rather than JSON lists. Declared coverage stays separate from observed completed work.

The additional joins support filtering and constraints. They also prevent a provider's claim of coverage from being presented as evidence of past service in that area. Q8 established this choice.

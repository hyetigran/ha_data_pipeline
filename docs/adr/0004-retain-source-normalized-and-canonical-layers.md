# Source observations and canonical facts

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Original records, normalized source entities, and canonical entities remain separate. Each source entity has appropriate fields. Frequently queried facts use SQL columns. Raw payloads and variable evidence can remain JSON.

The extra schema work preserves conflicting assertions before and after reconciliation. Removing the normalized source layer would make those differences harder to inspect.

Q14 requires a provider for each canonical job or estimate but permits an unresolved property link. Missing, unresolved, and conflicting property evidence remain explicit. The system retains the original address instead of creating a placeholder home. Exact-property results disclose incomplete coverage when unresolved work is excluded.

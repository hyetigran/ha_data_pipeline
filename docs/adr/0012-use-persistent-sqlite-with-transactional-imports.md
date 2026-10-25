# Persistent SQLite and transactional imports

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Whole-file replacement made durable identity state harder to preserve. Revised Q23 retains one SQLite database and publishes derived facts and relevant identity changes in one transaction.

Imports stage and validate a candidate before publication. A failed build preserves the last successful snapshot. Backup restoration and interruption tests verify recovery. The local review ledger remains authoritative outside the database commit, so recorded decisions can require replay after a publication failure.

This change solves identity preservation and coordinated publication. It does not implement continuous synchronization. Source ordering, retries, checkpoints, deletion, and freshness require separate production contracts.

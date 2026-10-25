# Continuous ingestion and syncing: current readiness

October 24, 2026. Production must support continuous source ingestion and syncing. This requirement informs the schema now; it does not authorize live CRM integrations or expand the current challenge beyond its supplied files.

## Current implementation

`cli.ingest` enumerates the complete local data pack and calls `storage.write_snapshot`. The writer builds and validates a staging database, then publishes its facts and identity state in a transaction on the persistent database. Routine imports preserve the database inode. A file lock rejects another concurrent importer. Source-scoped keys and content hashes deduplicate repeated observations in a snapshot. A failed build preserves the last successful published state.

This supports repeated full imports of supplied files. It does not provide a continuous sync worker, API polling/webhook connectors, per-source checkpoints, a durable queue, incremental source-version history, out-of-order update handling or explicit remote-deletion semantics. A disappeared input record simply is not part of the new full projection; that is not a safe general policy for partial API responses. The persistent identity registry preserves canonical IDs when new evidence joins an entity. Reviewed merges retain redirects, and split references can resolve as ambiguous. The [P2R execution record](p2r-execution.md) and [migration notes](p2r-migration.md) document the verification and recovery behavior.

## Accepted direction

[ADR 0012](adr/0012-use-persistent-sqlite-with-transactional-imports.md) is implemented for full local-file imports. P2R preserves authoritative identities and the last successful published state in one persistent SQLite database. Its verification includes crash recovery, pinned readers, and backup restoration. The private append-only review ledger remains authoritative outside the database transaction. Recovery distinguishes recorded decisions from database-applied decisions.

Q25 is also accepted (ADR 0013): deliveries declare source/account, scope and completeness semantics. Verified complete-snapshot omission establishes disappearance only within its scope. Partial-batch omission establishes nothing. Scope disappearance, explicit deletion and cancellation are distinct; history remains preserved. Completeness requires evidence, not merely a boolean claim.

## Production extension requirements and implementation details

- Separate stable source-record identity from versioned assertions. Retain source change time/version when supplied and ingestion time independently. Do not use latest arrival as universal business truth.
- Persist per-source sync runs/checkpoints and source record revisions. Advance an applied checkpoint only with its successfully published batch, or explicitly distinguish durably received from applied checkpoints if asynchronous processing is introduced.
- Define idempotency for retries and overlapping deliveries, including sources lacking monotonic revisions or stable row IDs. CSV edits cannot be treated as reliable updates solely because a content hash changed.
- Define tombstones and scoped complete-snapshot disappearance separately from cancellation. Retire source assertions without deleting historical evidence or arbitrarily destroying a canonical identity supported by other sources.
- Reconcile changed records and affected relationships. Revalidate evidence-bound review decisions when supporting assertions change; do not silently reuse stale approvals.
- Distinguish source freshness from job/provider availability. A successful sync of one account must not imply that all accounts are current. Expose last successful update, coverage and failure state as appropriate.
- Readers must see a consistent published generation while imports/review updates are serialized or otherwise coordinated. Preserve matching integrity when related changes arrive separately. Define whether invalid individual changes block the batch or enter quarantine without falsely advancing publication state.

Candidate tables include source_connections, sync_runs, sync_checkpoints, source_record_versions and deletion/disappearance evidence, alongside persistent identity and canonical tables. Their exact names, columns, revision, and publication semantics remain future production design work. P3 does not require these tables or another broad design interview.

SQLite capacity depends on actual transaction size, writer contention, query workload and deployment. Do not claim either production suitability at 10,000 providers or a need to replace SQLite from provider count alone. Benchmark representative continuous ingestion plus concurrent reads and revisit the database engine when measured requirements warrant it.

## Verification needed before a production-ready claim

Exercise duplicate delivery, a changed existing source ID, an older update arriving late, interrupted pagination, partial-batch omission, explicit deletion, cancellation, account-level failure, stale review evidence, crash before/after commit, identity merge/split during updates, checkpoint recovery and backup restore. These are proposed future checks; the existing full-import tests do not prove them.

## Accepted sync principles: Q26–Q29

- Q26: ordering uses a source-supported revision/ordering contract. Older arrivals do not overwrite newer accepted versions; incomparable assertions remain unresolved rather than using arrival order. Conflicting content at the same revision is an issue.
- Q27: retries are expected and idempotent. A duplicate delivery does not duplicate effects; applied progress and published changes commit together. A durable receipt is distinguishable from application, and checkpoints never skip unapplied work.
- Q28: validation/publication failure preserves prior published state for the affected source/account batch, retains diagnostic evidence and allows unrelated accounts to continue. A bad required record or incomplete page blocks that batch; atomicity is not imposed across every provider.
- Q29: freshness is per source/account/coverage stream, exposing last successful publication, source coverage and degraded state. A failed sync cannot manufacture availability or be hidden by successful updates elsewhere. Numerical stale thresholds and refresh targets are separate follow-ups.

Q26–Q29 are accepted design contracts, not implemented capabilities or implementation authorization. The operator requested a minimal initial design rather than further speculative edge-case rounds. Keep these contracts as production extension requirements; resolve publication and review consistency concretely when designing the relevant implementation.

## Scope control

The initial redesign remains a local file-import system. P2R implements the accepted domain schema and persistent transactional storage. The authorized P3 work derives availability and rankings from that model. Live connectors, queues, scheduling daemons, and a generalized event-processing framework remain deferred. Continuous sync remains a documented production requirement and later implementation phase. Preserve source/account keys, source timing/evidence and clear delivery boundaries so the future work has a defined starting point. Do not claim the small initial redesign alone delivers production syncing.

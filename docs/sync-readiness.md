# Production synchronization requirements

The local importer rebuilds the supplied pack. Production synchronization must handle changing sources without treating every partial response as a complete replacement.

That difference matters when a record disappears. A job absent from a weekly schedule may have moved outside the week. A partial response may omit it without changing it at all.

## Implemented full-pack imports

`cli.ingest` inventories the pack and calls `storage.write_snapshot`. The writer validates a candidate and publishes its facts and identity state transactionally. A file lock rejects competing importers. Routine publication preserves the database inode, and failed builds preserve prior facts.

Source-scoped keys and content hashes distinguish repeated observations. The identity registry preserves canonical IDs as evidence grows. Merges retain redirects, and splits can leave earlier references ambiguous.

The review ledger remains authoritative outside the SQLite commit. Recovery distinguishes recorded decisions from applied database state. [The P2R record](p2r-execution.md) documents the tested local guarantees.

These operations do not provide polling, webhooks, queues, per-source checkpoints, incremental version history, revision ordering, or remote-deletion semantics.

## Scope and completeness

Q25 requires each delivery to identify its source account, collection, coverage scope, and completeness evidence. Only a verified complete snapshot can establish disappearance within its scope.

A partial batch leaves omitted records unchanged. Explicit deletion retires a source assertion without erasing its history. Cancellation remains a business status. An identity supported by other sources can survive the loss of one assertion.

Completeness follows the adapter contract and validated delivery evidence. A boolean payload claim alone is insufficient. [ADR 0013](adr/0013-distinguish-complete-and-partial-source-deliveries.md) records the accepted distinction.

## Ordering, retries, and publication

Q26 uses a source-supported revision contract. Older arrivals cannot replace newer accepted versions. Incomparable assertions remain unresolved. Conflicting content at one revision creates an issue.

Q27 expects retries to be idempotent. Repeated deliveries cannot duplicate effects. Applied checkpoints and published changes commit together. A durable receipt differs from successful application, and a checkpoint cannot skip unapplied work.

Stable source identity also differs from versioned content. A changed spreadsheet hash alone does not establish which earlier row was updated. Source update time remains distinct from ingestion time.

## Failure isolation and freshness

Q28 preserves the affected account's prior published state when validation or publication fails. Diagnostic evidence survives. An invalid required record or incomplete page blocks that batch without blocking unrelated accounts.

Q29 reports freshness per source account and coverage stream. Successful updates elsewhere cannot conceal one stream's failure. Last successful publication, source coverage, and degraded state remain visible.

A failed or stale delivery cannot manufacture availability. Numerical stale thresholds and refresh targets still require a production policy.

## Review and reader consistency

Changed assertions can invalidate dependent approvals. A synchronization design must revalidate evidence-bound decisions rather than silently reuse them.

Readers need one consistent published revision while maintenance updates related facts. Publication, identity changes, and review replay need a defined recovery contract. A proposed table name such as `sync_checkpoints` does not establish that contract.

## Evidence still required

A production claim needs observed behavior for duplicate deliveries, changed source IDs, late older updates, interrupted pagination, partial omissions, explicit deletions, cancellations, and account failures.

It also needs checks for stale review evidence, interruption around commit, identity merges and splits during updates, checkpoint recovery, and backup restoration. Existing full-import tests prove only their stated local cases.

## Scope and capacity

The accepted Q25 through Q29 contracts guide future work. They do not authorize a generalized synchronization framework in the initial release.

Database choice depends on transaction size, writer contention, query cost, and deployment. Measurements of continuous imports with concurrent reads would inform a change. Neither SQLite failure at 10,000 providers nor a need for PostgreSQL follows from provider count alone.

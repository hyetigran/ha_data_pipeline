# P2R migration and recovery

P2R keeps one persistent SQLite database. Imports build a disposable candidate, seed its identity registry from the published database, validate the candidate, and publish facts and identity state in one transaction. Queries open a read transaction. Existing readers finish on their original revision; new transactions see the new revision.

The source pack is immutable. Schema version 2 replaces the generic source-table layout and canonical JSON documents with entity-specific source assertions and relational facts. Raw payloads, variable evidence and review proposals remain private JSON. The generic adapter transport is validated through entity-specific Pydantic models at the storage boundary.

## Local upgrade

Run the existing `house-account ingest` command with the intended database and ledger paths. A recognized legacy database gets a one-time `<database>.pre-v2.bak` SQLite backup before publication. Unknown schema versions and changed DDL without a version change are refused. A failed candidate build or pre-commit publication leaves the old facts available. A retry can reuse a matching legacy backup; an unrelated backup is never overwritten.

Preserve the backup until the migration has been reviewed. SQLite WAL may contain committed state outside the main file: use SQLite's backup API for a live backup, not a copy of the main file alone. To restore, stop writers, close connections, and restore the backup into a separate database path using the backup API; validate it before switching the local CLI to that path. The frozen P2 query code in `artifacts/P2R/baseline/code/` can read the legacy backup; P2R queries require the relational schema.

## Identity and review

Existing canonical IDs bootstrap the registry. Additional matching source members retain those IDs. A merge redirects retired IDs to the survivor. A split keeps the old reference ambiguous, even if a later merge reunites its descendants. Registry records can outlive current facts; a retired or absent provider does not return stale current data.

Review candidates use the live registry as their seed. A dry run allocates only within the candidate and leaves the published database and authoritative ledger unchanged. An applied decision is appended and fsynced to the ledger before database publication. These are separate durability boundaries: failure between them is reported as `recorded_not_applied`; rerun ingestion with the same ledger to recover. Rule version `reconciliation-v2` requires old decisions to be revalidated against current evidence. No pending real-world correction was approved as part of P2R verification.

## Intentional answer changes

Job lifecycle is independent of service completion. Fresh Nest job #1034 remains active with 46 completed visits and two upcoming visits. Estimates remain separate and never establish performed work. Results expose distinct jobs and completed visits separately. Completed-visit counts require independent visit-completion evidence (currently Jobber). HCP job timestamps and Workiz Done status contribute job-level completion; their projected schedule rows do not independently prove that an appointment occurred. Job-level completion does not fabricate a performed visit.

The radius example changes from 971 to 969 service-attributed jobs. Two records describe “Patch & paint drywall.” They retain job completion evidence and multiple service assertions, but lack evidence assigning that completion to a particular service. They no longer receive automatic painting credit. Provider and exact-home history can still report their job-level completion. Trade groups may overlap and must not be summed as a general distinct-job total.

Blank units remain unknown, not affirmative evidence of no unit. Exact complete addresses with unknown units can still match other unknown-unit assertions under the existing rule; they do not automatically merge with known unit identifiers. This preserves the approved matching scope without adding a broad address uniqueness constraint.

The Nov 1, 2026 DST start retains local date `2026-11-01`, state `ambiguous`, and no selected UTC start. The two possible UTC interpretations remain recoverable from source evidence. The wrong-year interval remains disputed until reviewed. Declared hours and calendar definitions are stored separately, without recurrence expansion or availability calculations.

## Boundaries

Full supplied-pack imports are implemented. Live continuous ingestion, revision ordering, partial delivery/deletion contracts, remote authentication, availability, travel and MCP serving remain future work. Unmapped service text stays private and is surfaced as unclassified work. Approximate street interpolation is not rooftop geocoding. The private hidden grader crosswalks are unavailable, so verification cannot establish that every one of the 22 hidden traps has been found.

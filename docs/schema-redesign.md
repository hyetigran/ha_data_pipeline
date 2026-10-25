# Relational schema redesign

P2R replaced generic source columns and canonical JSON documents with typed source assertions and relational canonical facts. The redesign preserves the distinction between what a source said and what the application can support.

The operator accepted the domain decisions during the October 24, 2026 interview. Q1 through Q29 include revised Q23, which selects persistent SQLite. The [execution record](p2r-execution.md) describes the implemented local scope. Production delivery contracts remain deferred.

## Three representations

Original source records retain private payloads, account keys, hashes, and occurrence locations. Normalized source tables preserve entity-specific assertions. Canonical tables select supported identities and facts.

The extra source layer adds schema work but keeps disagreements inspectable after reconciliation. Frequently queried facts use SQL columns and relationships. Raw payloads and variable evidence can remain JSON.

## Core relationships

Providers have related aliases, trades, exclusions, service areas, and working-hour declarations. Declared coverage remains separate from completed-work evidence.

Jobs and estimates require a provider and permit an explicitly unresolved property link. A visit has exactly one job or estimate parent. Its provider and property follow that parent.

A job can list several services and retain an active lifecycle after completed visits. `service_completions` records performed-work evidence separately. Service attribution connects a completion to supported work rather than crediting every listed service.

Temporal facts retain selected values, local dates, precision, and evidence states. Date-only facts do not become invented instants. Missing money remains distinct from zero. Unknown units do not automatically match known units.

## Evidence and identity

Field lineage connects selected values to source assertions, rules, and effective review decisions. A global source priority or latest arrival does not resolve every conflict.

The persistent identity registry retains IDs when new evidence joins an entity. Merges keep redirects. Splits can leave old references ambiguous.

The first separate-store identity proposal was not accepted. One persistent SQLite database now coordinates derived facts and identity publication. The authoritative review ledger remains a separate durability boundary with explicit replay recovery.

## Publication and migration

An import seeds a candidate with existing identity state, validates the candidate, and publishes it transactionally. Failed builds preserve the last successful snapshot. Readers keep a consistent revision for each transaction.

Legacy migration preserves a private backup and prior canonical memberships. Restoration uses SQLite's backup API. The [migration guide](p2r-migration.md) provides the procedure.

## Accepted decision records

The records below explain the individual choices.

| Decision | Record |
| --- | --- |
| Lifecycle separate from completion | [ADR 0001](adr/0001-separate-job-lifecycle-from-service-history.md). |
| SQL constraints | [ADR 0002](adr/0002-enforce-core-domain-invariants-in-sql.md). |
| Safe service detail | [ADR 0003](adr/0003-preserve-safe-service-detail.md). |
| Source and canonical layers | [ADR 0004](adr/0004-retain-source-normalized-and-canonical-layers.md). |
| Related provider facts | [ADR 0005](adr/0005-relational-provider-facts.md). |
| Temporal uncertainty | [ADR 0006](adr/0006-represent-temporal-uncertainty-explicitly.md). |
| Field lineage | [ADR 0007](adr/0007-retain-field-level-lineage.md). |
| Persistent identity | [ADR 0008](adr/0008-persistent-canonical-identity.md). |
| Completion evidence | [ADR 0009](adr/0009-separate-service-completion-evidence.md). |
| Visit parent relationships | [ADR 0010](adr/0010-inherit-visit-provider-and-property.md). |
| Multiple services | [ADR 0011](adr/0011-allow-multiple-services-per-job.md). |
| Transactional SQLite imports | [ADR 0012](adr/0012-use-persistent-sqlite-with-transactional-imports.md). |
| Production delivery scope | [ADR 0013](adr/0013-distinguish-complete-and-partial-source-deliveries.md). |

The [column design record](schema-columns-draft.md) retains the accepted vocabularies and interview constraints. Executable DDL remains authoritative for the physical schema.

## Deferred production work

Live connectors, polling, webhooks, queues, incremental processing, account retries, and numerical freshness targets remain outside P2R. The [synchronization requirements](sync-readiness.md) define their accepted contracts.

The redesign deliberately kept the existing adapter boundary and CLI. It introduced the structures required by observed data without building unused production infrastructure.

# Home services data model

House Account keeps source observations separate from the facts used to answer service questions. That separation preserves evidence when sources disagree or a human later corrects a match.

The local model covers six supplied sources and the street reference. One persistent SQLite database holds the published facts. The private source pack and review ledger remain rebuild inputs.

## Observations, identities, and facts

Source records retain account-scoped keys, content hashes, source times, ingestion times, original payloads, and occurrence locations. Typed source tables hold normalized assertions. Exact repeats keep their occurrence evidence without duplicating the normalized entity.

Canonical providers have related aliases, trades, exclusions, and declared areas. Working-hour declarations stay with each source profile and reach the canonical provider through `canonical_crosswalk`. Observed areas come from completed work. A declared service area does not prove past work there.

Identity rules require supporting evidence. Similar names alone do not merge businesses. Persistent IDs survive new matching evidence. Merges retain redirects, and splits can leave earlier references ambiguous rather than silently selecting one successor.

Properties preserve address and unit uncertainty. Nearby coordinates do not establish the same home. Street-segment interpolation gives approximate locations for radius queries. Missing coordinates reduce coverage and do not imply a travel time.

## Work and completion evidence

Jobs, estimates, and visits describe different facts. A visit belongs to exactly one job or estimate and derives its provider and property from that parent.

Job lifecycle describes the overall workflow. Service completions establish performed work. A recurring job can remain active after completed visits. An estimate, payment, or scheduled appointment alone does not prove service completion.

Jobs and estimates can list several services. Completion-service links record which work the evidence supports. The import creates a link only when the job lists exactly one service. Distinct completed jobs and independently completed visits remain separate counts. Trade groups can overlap.

Public descriptions use recognized service facts and approved wording. Raw notes remain private. Unclassified work and uncertain dates remain explicit. Field lineage links selected facts to source observations, rules, and effective review decisions.

## Time and candidate openings

Time evidence separates a selected UTC instant, local date, precision, and uncertainty. Dallas presentation uses `America/Chicago`. A date-only fact does not become an invented midnight appointment.

The challenge reference date is November 2, 2026. It is independent of actual ingestion time. Query windows include their start and exclude their end. Source coverage limits what the model can establish beyond that window.

Candidate openings subtract active visits, scheduled estimates, blocking calendar occurrences, and uncertain time from declared routine hours. Recurrence expands within a bounded horizon. Cancelled and transparent events do not block time. Opaque tentative holds, vacations, and out-of-area work do.

Capacity stays conservative at provider level. Crew size does not establish independently bookable workers. Travel is unmodeled, so an opening is a calendar candidate rather than a booking guarantee.

Ranking first requires capability, area evidence, and a sufficient opening. It then scores relevant completed work, area evidence, opening fit, and ordinal confidence. Duration comes from the request, supported historical scheduled durations, or a disclosed four-hour demo assumption.

## Publication and review

One maintenance writer builds and validates a candidate before publishing facts and identity state in one transaction. Failed builds preserve the prior snapshot. Readers retain one revision per read transaction.

The private append-only ledger records approve, reject, defer, and superseding decisions. Approvals bind to evidence and rule versions. Rebuilds replay effective decisions. Verification uses disposable approvals rather than changing real unresolved cases.

## Privacy boundary

MCP tools read published facts. They cannot import data, approve decisions, execute SQL, or read arbitrary files. Responses contain business identities, controlled service facts, bounded evidence references, coverage, and limitations.

Neighborhood answers use aggregates or block locations. Exact-home history applies only to the requested home. Homeowner contacts, raw notes, personal calendar titles, and review evidence remain local.

This local boundary limits disclosure but does not authenticate property ownership. Remote access control remains future work.

## Key tables

The database has 43 tables. These are the ones a reader most often needs. The DDL in `schema.py`, `storage.py`, and `registry.py` is authoritative.

| Table | Holds |
| --- | --- |
| `source_records` | One row per unique source identity, with its content hash and private payload. |
| `occurrences` | Every input location, with disposition `accepted`, `duplicate`, `unresolved`, or `rejected`. |
| `issues`, `entity_evidence` | Missing or ambiguous source values, and the rule and confidence behind each normalized entity. |
| `identity_registry` | Persistent canonical IDs with state `active`, `redirect`, or `ambiguous`. |
| `identity_memberships`, `identity_successors` | Which source identities belong to each canonical ID, and which IDs a split replaced. |
| `canonical_crosswalk` | Source ID to canonical ID, with the matching rule and evidence. Queries use it to reach source-level facts such as working hours. |
| `service_completions` | Performed-work evidence, with `evidence_basis` of `completed_visit`, `job_completion_timestamp`, or `job_completed_status`. |
| `completion_evidence`, `completion_services` | The source records behind each completion, and the job service it credits. |
| `provider_hour_declarations` | Working hours per source profile. |
| `field_lineage`, `lineage_entities`, `lineage_fields` | Which sources, rules, and review decisions support each selected field. |
| `reconciliation_proposals`, `reconciliation_metadata` | Review proposals, and the ledger revision and rule version they were built from. |

## Scale and deferred work

SQLite avoids a separate service for the measured local workload. Larger deployments depend on visits, recurrence density, query patterns, concurrency, and refresh volume. Provider count alone cannot select a database engine.

Production synchronization still needs scoped deliveries, source-supported ordering, idempotent retries, account-level failure isolation, and freshness reporting. Full-pack imports do not establish those capabilities. Remote authorization, live connectors, incremental updates, worker scheduling, and travel optimization remain deferred.

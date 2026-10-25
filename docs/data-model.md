# Home services data model

The local application answers service-history, schedule, and provider-selection questions from six supplied sources. It retains original observations, reconciles supported identities and facts, and exposes a bounded public view through six read-only MCP tools. SQLite holds one persistent published snapshot. The source pack and review ledger remain private rebuild inputs.

## Observations and canonical facts

Source records have source/account keys, content hashes, ingestion timestamps, original payloads, and occurrence locations. Entity-specific source tables retain normalized provider, property, job, estimate, visit, profile, and calendar assertions. Exact duplicate pages preserve occurrence accounting without duplicating the normalized entity. Conflicting assertions remain evidence rather than disappearing during normalization.

Canonical providers have related trades, exclusions, aliases, declared service areas, and working-hour declarations. Observed service areas come from completed work and remain distinct from declared coverage. Persistent identity records preserve IDs as evidence grows. Approved merges retain redirects; split references can be ambiguous. Similar names alone do not establish that two businesses are one provider.

Canonical properties preserve address and unit uncertainty. Exact address evidence establishes identity; nearby coordinates do not merge homes. Street segments support approximate interpolation for radius history. Missing or coarse coordinates reduce coverage and never imply a verified travel time.

Jobs, estimates, and visits are separate. A visit belongs to exactly one job or estimate and inherits its provider and property. Job lifecycle describes the workflow, while service completions establish performed work. Completed estimates are not completed service. A paid invoice or scheduled appointment alone does not establish service completion. Answers distinguish distinct completed jobs from independently supported completed visits.

Jobs and estimates can have multiple controlled services. Completion-service links identify which services a completion supports. Public descriptions come from recognized facts and approved wording, never copied private notes. Unknown services and conflicting dates remain explicit. Field lineage links selected values to source observations, rules, and effective review decisions.

## Time and availability

Timestamp evidence separates selected UTC instants, local dates, precision, and uncertainty. Dallas presentation uses America/Chicago. Windows include the start and exclude the end. Date-only history requires whole local dates; an ingestion timestamp does not become a service date. The challenge uses November 2, 2026 as its reproducible reference date, separate from actual ingestion time.

Candidate openings subtract occupied job visits, scheduled estimate appointments, and blocking calendar occurrences from declared routine hours. Recurrence expansion is bounded. Cancelled and transparent events do not block time; opaque tentative holds and vacations do. Out-of-area appointments still occupy time. Missing hours and uncertain intervals do not become free time.

Capacity is conservative at provider level. Crew size does not prove independently bookable workers, and travel is unmodeled. An opening is a calendar candidate, not a booking guarantee. Rankings require capability, area evidence, and a sufficient candidate opening before scoring completed experience, area evidence, calendar fit, and ordinal confidence. Duration comes from an explicit request, supported historical scheduled durations, or a disclosed four-hour demo assumption.

## Publication, review, and privacy

One maintenance writer stages and validates a rebuild, then publishes facts and identity state transactionally. Failed builds preserve the prior snapshot. Readers pin a consistent revision. The private append-only review ledger records approve, reject, defer, and superseding decisions. Approvals bind to exact evidence and rule versions. Rebuilding replays effective decisions; no demo automatically approves a real correction.

MCP calls read published state. They cannot import data, approve reviews, execute arbitrary SQL, or read arbitrary files. Public answers expose business identities, controlled service facts, bounded evidence references, source categories, coverage, and limitations. Neighborhood answers use aggregates or block-level locations. Exact-home lookup is restricted to the requested home. Homeowner contacts, raw notes, private calendar titles, and review evidence stay local. Local exact-home lookup is not a production authorization system.

## Tradeoffs and next work

SQLite avoids a separate database service for the supplied local workload. Performance at 10,000 providers depends on visits, recurrence density, query patterns, concurrency, and refresh volume. Measure those before choosing a new engine. PostgreSQL or PostGIS may become useful for concurrent writers, multiple hosts, or substantial spatial workloads; they do not replace identity or evidence policy.

Continuous sync remains a production requirement, not an implemented capability. Future deliveries must distinguish complete snapshots from partial updates, preserve source-supported ordering, apply retries idempotently, isolate account failures, and report per-source freshness. Week-two work starts with representative workload measurements and those delivery contracts, followed by authenticated exact-home access and better resource/travel evidence. Live connectors, a generalized sync framework, and a seventh-source PDF parser are outside this local release.

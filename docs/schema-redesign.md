# Proposed schema redesign

**Implementation update:** the accepted design is implemented in P2R schema version 2. This document retains the interview wording for context; executable DDL and the [P2R execution record](p2r-execution.md) govern the implemented shape and verified limits.

Interview draft, October 24, 2026. Q1–Q19 are accepted in ADRs 0001–0011 and the decision log. The layout below translates those decisions into proposed tables; the newer column draft identifies alternatives for service cardinality; it is not implemented DDL or authorization to change the database. Keep SQLite and the original/source-normalized/canonical separation. P3 computation is excluded.

## Canonical domain tables

Names below are proposed. IDs and relationships use ordinary SQL columns. Requiredness, controlled vocabularies and exact SQL CHECK clauses must be settled before DDL. `id` denotes a primary key; parent IDs denote foreign keys to the named domain table.

| Table | Proposed principal columns | Responsibility |
| --- | --- | --- |
| `canonical_providers` | `id`, `display_name` | Reconciled business identity. |
| `canonical_properties` | `id`, `house_number`, `street`, `unit`, `unit_state`, `city`, `state`, `postal_code`, `latitude`, `longitude`, `geocode_precision`, `reference_segment_id` | Resolved property identity and qualified location. Missing unit is distinguishable from confirmed no unit. |
| `canonical_jobs` | `id`, `provider_id`, `property_id`, `lifecycle`, `amount_minor`, `currency` | Work undertaking and its overall lifecycle. Completed service evidence is separate. |
| `canonical_estimates` | `id`, `provider_id`, `property_id`, `estimate_state` | Proposed work; never completed-service evidence merely because the estimate is finished. |
| `canonical_visits` | `id`, `job_id`, `estimate_id`, `appointment_kind`, `scheduling_state`, explicit scheduled-start/end value and evidence columns | Appointment belonging to exactly one job or estimate. Parent supplies provider/property; Q13 rejects independent visit copies. |
| `service_completions` | `id`, `job_id`, `visit_id`, `evidence_basis`, explicit service-date/time and evidence columns | Confirmed service evidence, including job-level evidence when completed visits cannot be established. A visit reference is optional; an estimate cannot be the parent. Exact cardinality/deduplication remains to be specified. |
| `trades` | `code`, `label` | Controlled trade vocabulary. |
| `service_categories` | `code`, `label` | Controlled service vocabulary; valid trades linked through service_category_trades. |
| `job_services` / `estimate_services` | `id`, parent ID, `trade_code`, `service_code`, `safe_description`, `classification_state` | Multiple services per parent; listing is not proof of performance. |

`has_completed_work`, distinct-job counts and completed-visit counts should be derived from service evidence, not mutable copies of job lifecycle. Completion time, scheduled service date and status-update time must not be conflated. A disputed Workiz scheduled year must remain disputed even when completion itself is confirmed.

For each time endpoint, the intended shape is explicit columns such as `scheduled_start_utc`, `scheduled_start_local_date`, `scheduled_start_state`, and `scheduled_start_precision`, plus timezone interpretation and source lineage. Exact bundles and allowed combinations remain open. A known date without an instant must be representable. An ambiguous DST instant must not be fabricated. Raw assertions and alternate interpretations remain traceable.

## Provider relationships

| Table | Proposed principal columns | Responsibility |
| --- | --- | --- |
| `provider_aliases` | `id`, `provider_id`, `name`, `normalized_name` | Multiple business labels; normalized names are not globally unique identities. |
| `provider_trades` | `provider_id`, `trade_code` | Many-to-many capability classification. |
| `provider_exclusions` | `provider_id`, `trade_code` | Explicit exclusions; exact scope beyond trades remains open. |
| `provider_declared_service_areas` | `provider_id`, `postal_code` | Declared coverage with evidence links. |
| Observed service-area query/view | Derived provider, ZIP and completion evidence | Demonstrated coverage evaluated for the requested history window; not copied from declarations. View versus materialized table remains open. |

Working hours and calendar blocks must retain separate declarations, busy evidence and timezone semantics. Existing source records remain available. Their eventual canonical tables can be designed after identity/uncertainty rules settle; this draft does not implement openings, recurrence expansion, capacity or ranking.

## Source-normalized entities

Keep entity-specific `source_providers`, `source_customers`, `source_properties`, `source_jobs`, `source_estimates`, `source_visits`, `source_calendar_blocks`, `source_profiles`, and `street_segments`. Each links to original source evidence and contains only relevant normalized fields. Do not repeat visit/price/job-reference columns on unrelated tables.

Normalized source relationships remain source-scoped. Canonical foreign keys reference canonical tables. Raw contact assertions stay private and do not require creating canonical homeowner identities for the six required questions. The exact source-column inventory and requiredness will follow the canonical relationship decisions; no assertion may disappear merely because canonical resolution is incomplete.

## Provenance, identity and review

Retain snapshot/input-file/source-record/occurrence/issue accounting and existing review evidence. Proposed supporting tables:

| Table or family | Proposed principal columns | Open design detail |
| --- | --- | --- |
| `canonical_entities` | `id`, `entity_kind`, `identity_state` | Registry can give all crosswalk/lineage references an actual FK target; subtype-kind enforcement still needs design. |
| Source-to-canonical links | `source_record_id`, `canonical_entity_id`, `rule_code`, `confidence` | Source occurrences and revisions must remain distinguishable. |
| Field derivations | `id`, `canonical_entity_id`, `field_name`, `rule_code`, `review_decision_id` | Typed entity targets/field validity and support for relationship-row lineage must be designed. |
| Derivation evidence | `derivation_id`, `source_record_id`, `source_field` | Multiple supporting assertions per derived fact. |
| Identity events and targets | `event_id`, event kind, predecessor/successor IDs, evidence/decision reference | Durable merge/split history and ID allocation across full snapshot rebuilds. Storage/recovery is not decided yet. |
| Review proposals / effective decisions | Existing proposal and ledger semantics | Keep human approve/reject/defer and stale-evidence checks. A SQL projection must not silently replace the authoritative local review file. |

A snapshot-only identity table cannot by itself meet persistent-ID requirements: identity bookkeeping must survive failed imports and full rebuilds. The migration must preserve current references or provide explicit resolution behavior. Its atomic publication/recovery protocol is a later interview branch, not an assumption made here.

## Accepted follow-up rules

Q20–Q22 and Q24 are accepted: deduplicate completion evidence and require supported service attribution; do not merge unknown units with known units automatically; apply field-specific value selection and evidence-bound human corrections; keep working-hour declarations and calendar definitions separate. Their detailed rules are recorded in D010 and related ADRs. Calendar/hour design does not implement P3 calculation.

## Scope after the interview

Q1–Q29 are accepted, with revised Q23 selecting persistent SQLite and transactional imports. On October 24 the operator requested less edge-case exploration and no initial overengineering. Stop expanding the question tree; turn the accepted semantics into a small concrete schema and migration design. Source-normalized/support-table details are implementation design work, not invitations for speculative new infrastructure.

Initial redesign scope:

1. Entity-specific source/canonical tables and searchable typed columns; related provider and service facts.
2. Separate lifecycle, completion evidence and visit parents, with explicit uncertainty and lineage.
3. Persistent identities and transactional local-file imports preserving last-successful-state and existing review guarantees.
4. Focused verification of accepted semantics, existing four P2 query behaviors, replay/review, and migration compatibility. Explicitly document intended answer changes rather than forcing obsolete counts.

Defer live connectors, polling/webhooks, durable queues, full incremental event processing, account retry orchestration and numerical freshness SLAs to the production-sync phase. The accepted Q25–Q29 contracts guide that future work; they do not justify building the machinery before it is needed. Do not claim production sync is implemented. P3 and implementation authorization remain outside this design conversation.

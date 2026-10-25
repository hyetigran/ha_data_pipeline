# Canonical columns and allowed values — interview draft

**Implementation update:** the accepted design is implemented in P2R schema version 2. This document retains the interview wording for context; executable DDL and the [P2R execution record](p2r-execution.md) govern the implemented shape and verified limits.

October 24, 2026. Q1–Q19 are accepted design decisions. **The Q15–Q19 controlled values and column semantics below were accepted in the interview. This is still a design draft, not implemented or approved executable DDL.** Source-normalized, provenance and identity-registry column inventories follow after these domain choices. This is not a complete migration specification.

## Shared SQL conventions

Proposal: explicit NOT NULL primary keys and required foreign keys; TEXT for opaque persistent IDs, controlled codes, ISO dates and UTC instants; INTEGER for exact minor-unit money; REAL for geographic coordinates. No JSON substitutes for the listed canonical facts. Prefer SQLite STRICT tables with explicit checks; runtime compatibility and migration tests are implementation work. Missing facts are SQL NULL, not empty strings, zero amounts, fabricated dates or placeholder entities. Human-readable names and descriptions must be nonblank when supplied.

Primary entity `id` columns are NOT NULL primary keys and eventually reference the durable identity registry. Allocation, subtype checks and persistence across rebuilds remain open. Entity links use foreign keys. Requiredness is marked below; unmarked fields are nullable. Raw asserted values and source status are retained separately in source-normalized records and original payloads.

## Core entities

### canonical_providers

| Column | Type | Constraint / meaning |
| --- | --- | --- |
| id | TEXT | Required, PK, persistent provider identity |
| display_name | TEXT | Required, nonblank public business label |

Capabilities, aliases, exclusions, declared ZIPs and later hours belong to related records, not copied JSON arrays. Missing public label handling must be verified against source adapters before enforcing this requirement.

### canonical_properties

| Column | Type | Constraint / meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| house_number | INTEGER | Positive when present; unparseable source text stays in source evidence |
| street | TEXT | Normalized street name and suffix |
| unit | TEXT | Normalized unit identifier; preserve meaningful punctuation |
| unit_state | TEXT | Required: `known`, `none`, `unknown`, `conflicting` |
| city | TEXT | Normalized locality |
| state | TEXT | Normalized US state code; consistent case established by normalizer |
| postal_code | TEXT | Five-digit ZIP when resolved; not numeric |
| latitude | REAL | -90 through 90 |
| longitude | REAL | -180 through 180 |
| geocode_precision | TEXT | Required: `street_segment_interpolation`, `missing` |
| reference_segment_id | TEXT | FK to supplied street reference |

Proposed checks: coordinates appear as a pair. Interpolation requires coordinates and reference segment; missing precision requires neither coordinate. `unit_state=known` requires a nonblank unit; other states have no selected unit. `none` requires affirmative evidence of no unit, not merely an empty source field. Conflicting unit candidates live in evidence. A broad address UNIQUE constraint must not silently collapse unknown units or partial addresses; exact identity-key constraints remain a later matching design detail.

### canonical_jobs

| Column | Type | Constraint / meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| provider_id | TEXT | Required, FK → canonical_providers |
| property_id | TEXT | FK → canonical_properties |
| property_link_state | TEXT | Required: `resolved`, `missing`, `unresolved`, `conflicting` |
| lifecycle | TEXT | Required: `open`, `active`, `pending_approval`, `completed`, `cancelled`, `unknown` |
| amount_minor | INTEGER | Exact signed minor-unit amount when known; zero is a real amount |
| currency | TEXT | Three-letter currency code when established by explicit source/account evidence |
| amount_state | TEXT | Required: `known`, `missing`, `disputed` |

`resolved` requires property_id; all other link states leave it null and retain source addresses/reasons in evidence. Known lifecycle must have traceable supporting interpretation. `amount_state=known` requires amount and currency; missing requires amount null; disputed does not expose a selected amount, and candidate assertions remain in evidence. Currency may be known when amount is missing. Negative amounts are preserved as source assertions; canonical eligibility requires establishing whether they describe credits/refunds or invalid totals. No generic rejection of all negative source values is proposed.

**Accepted Q17 revision:** earlier sketches had `trade_code`, `service_code` and `safe_description` directly on this table. Use the related `job_services` table below; multiple services are accepted. Do not keep both as competing authorities.

### canonical_estimates

| Column | Type | Constraint / meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| provider_id | TEXT | Required, FK → canonical_providers |
| property_id | TEXT | FK → canonical_properties |
| property_link_state | TEXT | Same allowed values/checks as jobs |
| estimate_state | TEXT | Required: `open`, `scheduled`, `in_progress`, `completed`, `cancelled`, `unknown` |

Related `estimate_services` describe proposed work. Completed estimates never generate service completion rows. A completed estimate does not imply acceptance, conversion or performed work. Estimate price normalization is out of this round: raw HCP option amounts remain evidence, not silently selected totals.

### canonical_visits

| Column | Type | Constraint / meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| job_id | TEXT | FK → canonical_jobs |
| estimate_id | TEXT | FK → canonical_estimates |
| appointment_kind | TEXT | Required: `job`, `estimate` |
| scheduling_state | TEXT | Required: `scheduled`, `in_progress`, `completed`, `cancelled`, `overdue`, `unscheduled`, `superseded`, `unknown` |
| scheduled_start_utc | TEXT | UTC instant when uniquely established |
| scheduled_start_local_date | TEXT | Independently established Dallas local date, when available |
| scheduled_start_state | TEXT | Required: `known`, `missing`, `ambiguous`, `disputed` |
| scheduled_start_precision | TEXT | Required: `instant`, `date`, `unknown` |
| scheduled_end_utc | TEXT | Same rules as start |
| scheduled_end_local_date | TEXT | Same rules as start |
| scheduled_end_state | TEXT | Same allowed values as start |
| scheduled_end_precision | TEXT | Same allowed values as start |
| timezone_name | TEXT | Required: `America/Chicago` for this pack |

SQL enforces exactly one parent and agreement with appointment_kind. Provider/property are derived through the parent, with no duplicate independent columns. A source-reported completed visit need not have a trustworthy time. `superseded` requires evidence of a replacement; a reschedule note alone does not fabricate the replacement visit. The reference date, not real wall clock, governs any derived overdue classification; preserve explicit source-reported status separately.

### service_completions

| Column | Type | Constraint / meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| job_id | TEXT | Required, FK → canonical_jobs |
| visit_id | TEXT | Optional FK → canonical_visits; must be a job visit for this same job |
| evidence_basis | TEXT | Required: `completed_visit`, `job_completion_timestamp`, `job_completed_status` |
| service_date | TEXT | Local date associated with performed service when established or explicitly qualified |
| service_date_state | TEXT | Required: `known`, `missing`, `ambiguous`, `disputed` |
| service_date_basis | TEXT | Required: `completion_timestamp`, `completed_visit_schedule`, `completed_job_schedule`, `unknown` |
| completed_at_utc | TEXT | Actual completion instant only, never substituted from status-update time |
| completed_at_state | TEXT | Required: `known`, `missing`, `ambiguous`, `disputed` |

A completed Workiz job can have job_completed_status evidence and an approximate service date from its schedule while actual completed_at remains missing. Date basis and uncertainty are returned with answers. Multiple supporting sources do not create multiple completed visits. Nullable visit linkage, visit/job consistency, uniqueness of reconciled completion evidence and date-window count aggregation need exact SQL/derivation rules in the next round. When service-specific completions are discussed, do not assume completing one visit proves every service in the job was performed.

## Q15: controlled lifecycle mappings

| Source assertion | Proposed job lifecycle | Notes |
| --- | --- | --- |
| Jobber active | active | Completed visits do not change overall lifecycle |
| Jobber upcoming/today/unscheduled | open | Appointment scheduling is represented on visits |
| Jobber archived/action_required/requires_invoicing | unknown | Preserve original administrative/billing state; not proof of successfully finished work |
| HCP complete rated / complete unrated on jobs | completed | Completion-date evidence remains separate |
| HCP scheduled / needs scheduling | open | Does not imply performed service |
| HCP in progress | active | Supported by adapter vocabulary; not observed among current job rows |
| HCP user canceled / pro canceled | cancelled | Preserve who cancelled in source evidence |
| Workiz Done | completed | Exact service date can still be uncertain |
| Workiz Pending / Submitted | open | Distinct raw workflow states retained; Submitted does not establish an appointment |
| Workiz Done Pending Approval | pending_approval | Not confirmed completed service |
| Workiz Canceled; explicit CSV cancellation | cancelled | Do not infer cancellation from unpaid or no reply |
| Other CSV notes or unknown future values | unknown | Preserve source value and issue |

An archived job may still have completed-service evidence. HCP completed-status estimates map only to estimate_state=completed. Jobber visit TODAY maps to scheduled; source OVERDUE maps to overdue. Full conflict selection across source assertions remains a separate reconciliation rule; this table only interprets individual source assertions.

## Q16: time precision and uncertainty rules

UTC values represent selected unique instants. `known/instant` requires UTC plus local date consistent with the timezone. `known/date` requires local date and no UTC instant. `missing` requires no selected values and precision=unknown. `ambiguous` or `disputed` cannot contain a selected UTC instant; an independently established local date may remain with precision=date, otherwise precision=unknown. Candidate local times, alternate UTC interpretations, and disputed date assertions remain in source/lineage evidence, not silently selected canonical timestamps.

Thus the November 1 DST job keeps local date 2026-11-01, state=ambiguous and UTC=null. Its two possible UTC starts remain evidence. The wrong-year candidate cannot select one service date until resolved. Checks compare start/end order only when both endpoints are known instants; partial dates do not manufacture duration. Actual completion and source status update are separate; status-update columns belong on source assertions, not canonical completed_at.

## Q17: service classifications and public wording

Proposed `trades(code TEXT PK, label TEXT NOT NULL)` values: handyman, plumbing, hvac, electrical, cleaning, landscaping, pest_control, roofing, gutters, painting, appliance_repair, garage_doors, unknown. The known codes derive from existing mappings, not an assertion that all services in the world are enumerated.

Proposed `service_categories(code TEXT PK, label TEXT NOT NULL)` plus `service_category_trades(service_code FK, trade_code FK, PRIMARY KEY(service_code, trade_code))`. A service can belong to more than one trade; do not force one trade globally for overlapping work such as painting. Dictionary changes are deliberate, versioned changes rather than arbitrary incoming source strings.

Proposed `job_services(id TEXT PK, job_id TEXT NOT NULL FK, trade_code TEXT NOT NULL, service_code TEXT NOT NULL, safe_description TEXT NOT NULL, classification_state TEXT NOT NULL)` and equivalent `estimate_services` with estimate_id. A composite FK constrains (service_code, trade_code) to allowed dictionary pairs. classification_state: `mapped`, `unmapped`, `conflicting`. Use explicit `unknown` category/allowed trade pairs for unrecognized work and a safe generic description with an issue; preserve raw wording privately. Multiple distinct service rows are permitted. Safe descriptions come from approved templates for supported facts, not copied source text.

Initial mappings must distinguish repair/replacement only when supported. “No heat” does not establish a failed furnace, and “torsion spring” does not establish replacement. Gate repair, TV mounting and furniture assembly are source-supported candidate categories; the complete dictionary and mapping fixtures are a follow-up after cardinality is accepted.

Related provider tables: `provider_aliases(id TEXT PK, provider_id TEXT NOT NULL FK, name TEXT NOT NULL, normalized_name TEXT NOT NULL)`, unique(provider_id, normalized_name); `provider_trades(provider_id FK, trade_code FK)` and `provider_exclusions(provider_id FK, trade_code FK)` with composite PKs; `provider_declared_service_areas(provider_id FK, postal_code TEXT)` with composite PK and five-digit ZIP checks. All relationship columns are NOT NULL. Provider aliases are not globally unique names. Lineage can have multiple evidence links per related fact; exact support-table keys remain open.

## Q18: property unknowns

Accept proposed `property_link_state` and `unit_state` enums/checks above. Missing locality components remain null; no default Dallas ZIP is guessed. Unique street-reference inference remains allowed only with one supported match and field lineage. Keep unavailable geometry distinguishable from a location that was evaluated outside a radius. The data pack is US/Dallas scoped; broader countries/address formats require an explicit extension rather than lossy normalization.

## Q19: money semantics

Accept nullable exact INTEGER minor units, separate currency, explicit known/missing/disputed evidence, and no blank-to-zero conversion. Actual normalized job data includes zero amounts, 95 missing Jobber amounts and 41 missing unique spreadsheet amounts; no negative job totals were observed. Missing source currency may be supplied only by explicit source/account contract evidence, not a universal guess. Distinct source totals for one canonical job remain separate assertions until a selection rule resolves them; do not add them together merely because two sources describe the same job.

## Still open after this round

Q15–Q19 are accepted; remaining structural and enforcement details are still draft. Next decisions include service-level completion attribution, completion deduplication and count windows, source-normalized columns/status-update timestamps, property matching/unique keys, conflict-selection policy, field-lineage relational integrity, identity-registry persistence and redirects, canonical hours/calendar representation, and safe migration. None require implementing P3 while this interview is ongoing.

# Canonical column design from the interview

This reference records the column design accepted on October 24, 2026. P2R subsequently implemented schema version 2. The tables below describe the interview contract, including proposals that still needed precise SQL rules at that time. Executable DDL and the [P2R execution record](p2r-execution.md) govern the implemented shape. This record is not a migration specification.

## Shared SQL conventions

The proposed SQL types are TEXT for opaque IDs, controlled codes, dates, and UTC instants. INTEGER represents exact minor-unit amounts. REAL represents coordinates. Required keys use NOT NULL. The design calls for STRICT tables and explicit checks. Missing facts use SQL NULL. Supplied names and descriptions are nonblank.

Primary entity `id` columns are NOT NULL primary keys and eventually reference the durable identity registry. Allocation, subtype checks and persistence across rebuilds remain open. Entity links use foreign keys. Requiredness is marked below. Unmarked fields are nullable. Raw asserted values and source status are retained separately in source-normalized records and original payloads.

## Core entities

### canonical_providers

| Column | Type | Constraint or meaning |
| --- | --- | --- |
| id | TEXT | Required, PK, persistent provider identity |
| display_name | TEXT | Required, nonblank public business label |

Capabilities, aliases, exclusions, declared ZIPs and later hours belong to related records, not copied JSON arrays. Missing public label handling must be verified against source adapters before enforcing this requirement.

### canonical_properties

| Column | Type | Constraint or meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| house_number | INTEGER | Positive when present. Unparseable source text stays in source evidence |
| street | TEXT | Normalized street name and suffix |
| unit | TEXT | Normalized unit identifier. Preserve meaningful punctuation |
| unit_state | TEXT | Required: `known`, `none`, `unknown`, `conflicting` |
| city | TEXT | Normalized locality |
| state | TEXT | Normalized US state code. Consistent case established by normalizer |
| postal_code | TEXT | Five-digit ZIP when resolved. Not numeric |
| latitude | REAL | -90 through 90 |
| longitude | REAL | -180 through 180 |
| geocode_precision | TEXT | Required: `street_segment_interpolation`, `missing` |
| reference_segment_id | TEXT | FK to supplied street reference |

Proposed checks: coordinates appear as a pair. Interpolation requires coordinates and reference segment. Missing precision requires neither coordinate. `unit_state=known` requires a nonblank unit. Other states have no selected unit. `none` requires affirmative evidence of no unit, not merely an empty source field. Conflicting unit candidates live in evidence. A broad address UNIQUE constraint must not silently collapse unknown units or partial addresses. Exact identity-key constraints remain a later matching design detail.

### canonical_jobs

| Column | Type | Constraint or meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| provider_id | TEXT | Required, FK → canonical_providers |
| property_id | TEXT | FK → canonical_properties |
| property_link_state | TEXT | Required: `resolved`, `missing`, `unresolved`, `conflicting` |
| lifecycle | TEXT | Required: `open`, `active`, `pending_approval`, `completed`, `cancelled`, `unknown` |
| amount_minor | INTEGER | Exact signed minor-unit amount when known. Zero is a real amount |
| currency | TEXT | Three-letter currency code when established by explicit source/account evidence |
| amount_state | TEXT | Required: `known`, `missing`, `disputed` |

`resolved` requires property_id. All other link states leave it null and retain source addresses/reasons in evidence. Known lifecycle must have traceable supporting interpretation. `amount_state=known` requires amount and currency. Missing requires amount null. Disputed does not expose a selected amount, and candidate assertions remain in evidence. Currency may be known when amount is missing. Negative amounts are preserved as source assertions. Canonical eligibility requires establishing whether they describe credits/refunds or invalid totals. No generic rejection of all negative source values is proposed.

Q17 moved `trade_code`, `service_code`, and `safe_description` from the job row into `job_services`. A job can contain several services. The job row does not duplicate those classifications.

### canonical_estimates

| Column | Type | Constraint or meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| provider_id | TEXT | Required, FK → canonical_providers |
| property_id | TEXT | FK → canonical_properties |
| property_link_state | TEXT | Same allowed values/checks as jobs |
| estimate_state | TEXT | Required: `open`, `scheduled`, `in_progress`, `completed`, `cancelled`, `unknown` |

Related `estimate_services` describe proposed work. Completed estimates never generate service completion rows. A completed estimate does not imply acceptance, conversion or performed work. Estimate price normalization is out of this round: raw HCP option amounts remain evidence, not silently selected totals.

### canonical_visits

| Column | Type | Constraint or meaning |
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

The contract requires exactly one parent and agreement with `appointment_kind`. Provider/property are derived through the parent, with no duplicate independent columns. A source-reported completed visit need not have a trustworthy time. `superseded` requires evidence of a replacement. A reschedule note alone does not fabricate the replacement visit. The reference date governs derived overdue classification. Explicit source-reported status remains separate.

### service_completions

| Column | Type | Constraint or meaning |
| --- | --- | --- |
| id | TEXT | Required, PK |
| job_id | TEXT | Required, FK → canonical_jobs |
| visit_id | TEXT | Optional FK → canonical_visits. Must be a job visit for this same job |
| evidence_basis | TEXT | Required: `completed_visit`, `job_completion_timestamp`, `job_completed_status` |
| service_date | TEXT | Local date associated with performed service when established or explicitly qualified |
| service_date_state | TEXT | Required: `known`, `missing`, `ambiguous`, `disputed` |
| service_date_basis | TEXT | Required: `completion_timestamp`, `completed_visit_schedule`, `completed_job_schedule`, `unknown` |
| completed_at_utc | TEXT | Actual completion instant only, never substituted from status-update time |
| completed_at_state | TEXT | Required: `known`, `missing`, `ambiguous`, `disputed` |

A completed Workiz job can have job_completed_status evidence and an approximate service date from its schedule while actual completed_at remains missing. Date basis and uncertainty are returned with answers. Multiple supporting sources do not create multiple completed visits. Nullable visit linkage, visit/job consistency, uniqueness of reconciled completion evidence and date-window count aggregation need exact SQL/derivation rules in the next round. Completion of one visit does not prove that every listed service was performed.

## Q15: controlled lifecycle mappings

| Source assertion | Accepted lifecycle interpretation | Notes |
| --- | --- | --- |
| Jobber active | active | Completed visits do not change overall lifecycle |
| Jobber upcoming/today/unscheduled | open | Appointment scheduling is represented on visits |
| Jobber archived/action_required/requires_invoicing | unknown | Preserve original administrative/billing state. Not proof of successfully finished work |
| HCP complete rated / complete unrated on jobs | completed | Completion-date evidence remains separate |
| HCP scheduled / needs scheduling | open | Does not imply performed service |
| HCP in progress | active | Supported by adapter vocabulary. Not observed among current job rows |
| HCP user canceled / pro canceled | cancelled | Preserve who cancelled in source evidence |
| Workiz Done | completed | Exact service date can still be uncertain |
| Workiz Pending / Submitted | open | Distinct raw workflow states retained. Submitted does not establish an appointment |
| Workiz Done Pending Approval | pending_approval | Not confirmed completed service |
| Workiz Canceled. Explicit CSV cancellation | cancelled | Do not infer cancellation from unpaid or no reply |
| Other CSV notes or unknown future values | unknown | Preserve source value and issue |

An archived job may still have completed-service evidence. HCP completed-status estimates map only to estimate_state=completed. Jobber visit TODAY maps to scheduled. Source OVERDUE maps to overdue. Full conflict selection across source assertions remains a separate reconciliation rule. This table only interprets individual source assertions.

## Q16: time precision and uncertainty rules

UTC values represent selected unique instants. `known/instant` requires UTC plus local date consistent with the timezone. `known/date` requires local date and no UTC instant. `missing` requires no selected values and precision=unknown. `ambiguous` or `disputed` cannot contain a selected UTC instant. An independently established local date may remain with precision=date, otherwise precision=unknown. Candidate local times, alternate UTC interpretations, and disputed date assertions remain in source/lineage evidence, not silently selected canonical timestamps.

Thus the November 1 DST job keeps local date 2026-11-01, state=ambiguous and UTC=null. Its two possible UTC starts remain evidence. The wrong-year candidate cannot select one service date until resolved. Checks compare start/end order only when both endpoints are known instants. Partial dates do not manufacture duration. Actual completion and source status update are separate. Status-update columns belong on source assertions, not canonical completed_at.

## Q17: service classifications and public wording

Proposed `trades(code TEXT PK, label TEXT NOT NULL)` values: handyman, plumbing, hvac, electrical, cleaning, landscaping, pest_control, roofing, gutters, painting, appliance_repair, garage_doors, unknown. The known codes derive from existing mappings, not an assertion that all services in the world are enumerated.

Proposed `service_categories(code TEXT PK, label TEXT NOT NULL)` plus `service_category_trades(service_code FK, trade_code FK, PRIMARY KEY(service_code, trade_code))`. A service can belong to more than one trade. Do not force one trade globally for overlapping work such as painting. Dictionary changes are deliberate, versioned changes rather than arbitrary incoming source strings.

Proposed `job_services(id TEXT PK, job_id TEXT NOT NULL FK, trade_code TEXT NOT NULL, service_code TEXT NOT NULL, safe_description TEXT NOT NULL, classification_state TEXT NOT NULL)` and equivalent `estimate_services` with estimate_id. A composite FK constrains (service_code, trade_code) to allowed dictionary pairs. classification_state: `mapped`, `unmapped`, `conflicting`. Unrecognized work uses an allowed `unknown` classification, a safe generic description, and an issue. Raw wording remains private. Multiple distinct service rows are permitted. Safe descriptions come from approved templates for supported facts, not copied source text.

Repair and replacement have distinct classifications only when evidence supports that distinction. "No heat" does not establish a failed furnace, and "torsion spring" does not establish replacement. Gate repair, TV mounting and furniture assembly are source-supported candidate categories. The complete dictionary and mapping fixtures are a follow-up after cardinality is accepted.

Related provider tables: `provider_aliases(id TEXT PK, provider_id TEXT NOT NULL FK, name TEXT NOT NULL, normalized_name TEXT NOT NULL)`, unique(provider_id, normalized_name). `provider_trades(provider_id FK, trade_code FK)` and `provider_exclusions(provider_id FK, trade_code FK)` with composite PKs. `provider_declared_service_areas(provider_id FK, postal_code TEXT)` with composite PK and five-digit ZIP checks. All relationship columns are NOT NULL. Provider aliases are not globally unique names. Lineage can have multiple evidence links per related fact. Exact support-table keys remain open.

## Q18: property unknowns

Q18 accepted the proposed `property_link_state` and `unit_state` values and constraints. Missing locality components remain null. No default Dallas ZIP is guessed. Street-reference inference requires one supported match and field lineage. Missing geometry differs from a resolved location outside a radius. The data pack is US/Dallas scoped. Broader countries/address formats require an explicit extension rather than lossy normalization.

## Q19: money semantics

Q19 accepted nullable INTEGER minor units, separate currency, and explicit evidence states. Blank amounts do not become zero. Actual normalized job data includes zero amounts, 95 missing Jobber amounts and 41 missing unique spreadsheet amounts. No negative job totals were observed. Missing source currency may be supplied only by explicit source/account contract evidence, not a universal guess. Distinct source totals remain separate assertions until a selection rule resolves them. Two sources describing one job do not justify summing their amounts.

## Questions left open by this interview round

Q15 through Q19 were accepted. The remaining decisions at that time included service-level completion attribution, completion deduplication and count windows, source-normalized columns/status-update timestamps, property matching/unique keys, conflict-selection policy, field-lineage relational integrity, identity-registry persistence and redirects, canonical hours/calendar representation, and safe migration. The later [schema decisions](schema-redesign.md) record their resolution. Production delivery semantics remain deferred.

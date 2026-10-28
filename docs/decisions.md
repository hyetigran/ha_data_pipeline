# Project decisions

This record explains the choices behind the local application. Entries D001 through D013 describe decisions made on October 24, 2026. Later entries record implementation scope.

P1, P2, P2R, P3, and P4 are implemented and merged. Earlier restrictions describe authorization at the time of each decision. They do not override later requests. Execution records contain the measured results.

## D001. Calendar availability without travel estimates

The local release calculates openings from declared hours minus occupied and uncertain intervals. Travel remains unmodeled.

The street reference covers nine postal codes and supports approximate coordinates. Scheduled work also occurs outside that area. The pack has no routing network or travel-time matrix. Straight-line distance cannot establish driving time between appointments.

A fixed buffer would be an assumption. The initial model therefore discloses the missing travel calculation instead of inventing one. Responses describe openings as candidates under a stated duration. Out-of-area work still consumes time.

Route-aware scheduling would need broader location coverage, routing evidence, and resource assignments. Travel before and after an appointment would both matter. A later configurable buffer would need an explicit assumption label.

## D002. Local review of ambiguous matches and corrections

Deterministic normalization runs automatically. Ambiguous identities and inferred corrections become proposals in `review/reconciliation.json`. Each explicit decision records the reviewer, UTC decision time, and reason.

A JSON file fits the local challenge without a separate review application. New proposals default to defer. A high-confidence correction still needs approval. The wrong-year and transposed-number cases remain unresolved unless a human approves them.

Approval binds to the exact action, source hashes, and rule version. Rejection suppresses an identical proposal from the new-review count. Deferral keeps the proposal unresolved. Export preserves existing human edits.

The append-only ledger retains decisions and supersession history. Rebuilding from originals and effective decisions reverses earlier derived changes. Changed evidence invalidates dependent approvals. Paired timestamp corrections remain jointly approved or jointly unapplied.

Validation rejects stale or incompatible decisions before publication. Apply records decisions before publishing the database. A failure between those steps reports `recorded_not_applied` and recovery replays the same ledger.

Attribution is self-declared. This workflow is not authenticated multi-user approval or tamper-proof audit storage. The [review guide](review-reconciliation.md) describes operation.

## D003. Local MCP over stdio

The selected client launches the Python MCP server locally. Protocol traffic uses stdin and stdout. Controlled diagnostics use stderr.

The challenge requires local startup and an agent demonstration, not a public endpoint. Hosting would add authentication, transport, storage, and operations work beyond that deliverable.

Startup can prepare missing derived state before serving. Tool calls use read-only connections and cannot import data or apply review decisions. P4 verified Codex initialization, tool discovery, all six questions, fresh startup, and shutdown.

Remote deployment still requires authentication, authorization, persistent storage, process management, and monitoring. Changing the transport alone does not provide those controls.

## D004. SQLite for the measured local workload

SQLite stores source evidence, canonical facts, identities, and applied decision references. The application needs no separate database service. Relational constraints fit the provider, property, job, visit, and evidence relationships.

One maintenance writer validates a candidate before publication. Readers use consistent transactions. The original pack and review ledger remain rebuild inputs.

Provider count alone does not establish a database limit. Record volume, recurrence, concurrent readers, refresh frequency, and spatial queries determine the workload. Full rebuilds or application scans could become limiting costs before SQLite itself does.

PostgreSQL or PostGIS remains an option when measurements or deployment requirements justify it. Any storage change must preserve canonical IDs, source references, decision history, constraints, and answer semantics.

## D005. Canonical facts with preserved observations

P2 added canonical tables and a source crosswalk while retaining P1 observations. Queries selected public fields from those canonical facts.

Provider matching requires a shared business phone plus corroborating trade evidence. Name similarity creates a candidate, not an automatic merge. Address normalization preserves units and infers missing locality only from one supported street segment.

Cross-source jobs remain separate or reviewable without an immutable shared identifier. The conservative rule generated no job candidates in the supplied pack. That result does not establish that every hidden duplicate was found.

Completion evidence remains distinct from date evidence. Jobber completed visits and Housecall Pro completion timestamps support history. Workiz `Done` supports job completion with a qualified scheduled service date. A status update is not an exact service date. CSV payment does not prove completion.

Public output keeps business labels, controlled service facts, bounded evidence references, and limitations. Homeowner contacts, raw notes, private review evidence, and source paths remain excluded.

P2 originally derived IDs from member sets and scanned canonical documents. P2R superseded those choices with persistent identities and relational queries. [The P2 record](p2-execution.md) preserves the earlier verification results.

## D006. Lifecycle, SQL constraints, and service detail

The first schema decisions separate lifecycle from completion, enforce core relationships in SQL, and retain useful service descriptions without exposing notes.

Q4 through Q7 add separate job and visit counts, source-specific lifecycle mappings, source and canonical layers, and descriptions built from recognized facts. Unknown or conflicting evidence remains explicit.

[ADRs 0001 through 0004](schema-redesign.md) explain the accepted tradeoffs. These decisions authorized design at that stage, not an immediate migration.

## D007. Relationships, uncertainty, lineage, and identity

Q8 through Q11 select related tables for provider facts, explicit temporal uncertainty, field-level lineage, and persistent canonical IDs.

Declared service areas remain separate from observed work. Schedule time, completion time, and status-update time remain separate facts. Merges preserve redirects, and splits can leave old references ambiguous.

These choices superseded P2's member-set identity design. Their implementation followed in P2R.

## D008. Completions, visit parents, and unresolved properties

Q12 through Q14 establish `service_completions`, one parent per visit, and explicit unresolved property links.

A visit inherits its provider and property from one job or estimate. Jobs and estimates require a provider but can lack a resolved property. Missing address evidence does not create a placeholder home.

[ADRs 0009 and 0010](schema-redesign.md) and [ADR 0004](adr/0004-retain-source-normalized-and-canonical-layers.md) record the reasons.

## D009. Controlled values and column semantics

Q15 through Q19 define the following accepted semantics.

- Job lifecycle, visit scheduling state, and estimate state have separate vocabularies. Original source statuses remain available.
- Each scheduled endpoint has a UTC value, local date, evidence state, precision, and timezone. Contradictory combinations are invalid.
- Jobs and estimates can have several controlled services. Classification is `mapped`, `unmapped`, or `conflicting`.
- Property links are `resolved`, `missing`, `unresolved`, or `conflicting`. Unit states are `known`, `none`, `unknown`, or `conflicting`.
- Money uses nullable exact minor units, separately supported currency, and `known`, `missing`, or `disputed` state. Missing is not zero.

The [column design record](schema-columns-draft.md) contains the accepted values. Those values do not authorize summing conflicting totals or inventing time values.

## D010. Attribution, selection rules, and storage alternatives

Q20 through Q22 and Q24 require deduplicated completion evidence, supported service attribution, conservative property matching, field-specific selection, and separate hours and calendar definitions.

Unknown units do not automatically match known units. A completed job does not prove that every listed service happened. Source priority and arrival time do not universally resolve conflicts.

Working-hour declarations retain local time, effective dates, and emergency qualifiers. Calendar definitions retain recurrence, exclusive ends, status, transparency, and provenance.

The first Q23 proposal used a separate identity store. The operator did not accept it. SQLite supports durable transactions. The concern was preserving authoritative identity state while replacing derived data.

## D011. Persistent SQLite and the production sync requirement

Revised Q23 selected one persistent SQLite database. Imports stage and validate data, then publish facts and identity changes transactionally. Failed builds preserve prior state. Recovery verification includes backup restoration and interruption tests.

The operator also required continuous source synchronization for production. That requirement did not authorize live CRM integration during the local challenge. [The synchronization record](sync-readiness.md) separates implemented full imports from future contracts.

## D012. Delivery scope and completeness

Q25 distinguishes complete snapshots from partial changes. A delivery identifies its source account, collection, scope, and completeness evidence.

Only verified complete coverage can establish disappearance within that scope. A partial batch does not delete omitted records. Absence from a weekly schedule can mean an appointment moved outside the week. It does not establish cancellation or deletion.

[ADR 0013](adr/0013-distinguish-complete-and-partial-source-deliveries.md) records this production requirement. It does not define an implemented runtime payload.

## D013. Small initial implementation and deferred sync work

Q26 through Q29 require source-supported ordering, idempotent retries, consistent publication and applied checkpoints, account-level failure isolation, and per-stream freshness reporting.

The operator then limited further speculative design. The initial implementation would cover the accepted domain model, persistent identity, transactional full imports, and existing review behavior. Routine details would be resolved through implementation and tests.

Live connectors, polling, webhooks, queues, incremental changes, retry orchestration, and refresh targets remain deferred. The local importer does not claim those capabilities.

## D014. P2R implementation scope

The P2R request authorized the accepted local schema changes without starting P3. Schema version `2` implements typed source assertions, relational canonical facts, separate lifecycle and completion evidence, persistent identities, and transactional publication.

The ledger remains authoritative outside the SQLite commit. Rule version `reconciliation-v2` revalidates older decisions. Test approvals use disposable state. No real pending correction was approved to improve a demonstration.

Unknown units remain unknown. Complete unknown-unit addresses can match each other but do not automatically match known units. Date-only history uses whole Chicago calendar dates. The [P2R execution record](p2r-execution.md) records verification and intended answer changes.

## D015. P3 availability and rankings

The P3 request authorized implementation on merged P2R at `c6c151e`. P3 adds candidate openings and deterministic rankings over the existing facts.

Missing hours, uncertain intervals, and limited coverage remain visible. Capacity stays conservative, and travel remains unmodeled. November 2, 2026 in `America/Chicago` is the fixed challenge reference date.

The original request excluded P4 and publication. Later authorization merged P3 in PR #3 at `313847d`. [The P3 execution record](p3-execution.md) contains its evidence.

## D016. P4 MCP delivery and the Codex demo

The P4 request selected Codex and authorized six bounded read-only stdio tools, verification, and documentation fixes. Its baseline was merged P3 at `313847db86a994095face0818c685ced5c56779e`.

Typed public responses preserve completion attribution, coverage, uncertainty, and bounded evidence. Each call reads one snapshot. Neighborhood answers use aggregates or blocks. Exact-home history applies to the supplied home. Private contacts, notes, titles, and review evidence remain local.

The actual Codex capture covers all six questions. The four-minute video replays captured interaction and includes an earlier weak answer. It is not a live screen recording.

The initial request kept P4 unmerged for review. Later authorization required maintenance verification before merge. That pass corrected only the verification skill and passed all eight journeys. PR #4 then merged as `ea66e76`. [The P4 execution record](p4-execution.md) records the implementation and review limits.

## D017. Conservative normalization repairs after the trap audit

On October 27, 2026, the user authorized confirmed service-classification and address-parsing fixes, regression tests, and a comparison of all six required answers, without publishing or merging.

Use explicit aliases for clear service phrases and declared trade context for labels with competing interpretations. Specific service terms precede generic leak/cleaning/repair tokens. Vague wording stays unknown. Compound work retains separate scope where the domain distinguishes services; normalization does not grant completion attribution to every service in a completed job.

Normalize supported trailing-city and separate-unit address forms, preserving units and original text. Exact formatting equivalence can join a property; spelling corrections, conflicting locality, disputed dates, and identity matches still require review. Reference coverage limits geocoding even when parsing succeeds.

Verification uses isolated before/after snapshots and actual MCP calls. Existing source data, review files, and the running database remain unchanged. [The comparison](normalization-fixes-2026-10-27.md) records the answer changes, tests, and remaining unknowns.

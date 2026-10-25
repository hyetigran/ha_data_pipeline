# Project decision log

This log records design decisions and their implementation status. The execution records identify which acceptance checks have passed.

P1, P2, and P2R are implemented and merged. Their execution reports retain the evidence and phase-specific authorization limits that applied at the time. D015 records the current authorization to implement and verify P3, including stale documentation fixes. Stop before P4. Publication and merge require a separate request.

## D001. Defer travel-aware scheduling

Recorded October 24, 2026. Accepted for the two-day challenge scope.

Calculate candidate openings from declared working hours minus occupied appointments and blocking calendar events. Do not subtract estimated commute time or claim that a calendar gap guarantees a feasible appointment.

The supplied street reference supports approximate coordinates within nine target postal codes. Scheduled work also occurs outside that coverage. The pack supplies no routing network or travel-time matrix. Straight-line proximity for the half-mile history question does not establish driving time between appointments.

A two-hour gap between existing jobs may not fit two hours of work plus travel. Both travel from the preceding appointment to the requested property and travel to the following appointment matter. A fixed buffer would be an assumption rather than a measured journey time, so the initial calculation does not silently add one.

The tool responses, model document, and demo must disclose that travel is unmodeled. Opening confidence must not imply that geographic feasibility has been established. Rankings must describe opening suitability as calendar fit under the stated duration assumption.

Acceptance conditions for implementation:

- Return an explicit travel-unmodeled limitation with availability and recommendation responses.
- Keep out-of-area appointments in occupied time even when their coordinates are unavailable.
- Verify that the connected agent describes openings as candidates rather than guaranteed bookings.
- Keep geographic-radius calculations separate from travel-time claims.

Revisit this decision after the core works. A configurable travel buffer is a possible intermediate improvement, provided responses identify the buffer as an assumption. Route-aware scheduling requires broader location coverage, a routing source, and resource assignments. Evaluate travel on both sides of a proposed appointment before claiming feasibility.

This decision addresses the availability-reasoning rubric by making an explicit scope tradeoff and exposing its limitations. It does not establish that calendar-only availability earns full credit.

Evidence comes from [the supplied data README](../data/README.md), [the inspection findings](data-pack-inspection.md), and the user's discussion of commute handling. The [project plan](project-plan.md) includes this limitation in P3.

## D002. Review ambiguous reconciliation through a local file

Recorded October 24, 2026. Accepted by the user's request to add human review to the plan. P2 implements this workflow. No specific correction or merge is approved by this decision.

Keep deterministic normalization automatic. Export ambiguous identity matches and inferred factual corrections to `review/reconciliation.json`. A human approves, rejects, or defers each proposal with reviewer attribution, a decision timestamp, and a reason. New proposals default to defer.

Choose a JSON file with schema validation because the challenge excludes a user interface and has a two-day implementation budget. The file supports explicit decisions without adding a web application. Local maintenance may update derived data, while every MCP tool remains read-only and original sources remain intact.

Approval applies only to the exact proposed action and evidence version. Reject leaves the proposal unapplied and suppresses identical repeated suggestions. Defer keeps it unresolved. High-confidence correction candidates still require approval. In particular, the wrong-year job and transposed house number remain proposals until reviewed.

Store decisions in an append-only local ledger and link applied results to decision IDs. Rebuild canonical snapshots from immutable observations plus effective decisions. Source-record hashes and rule versions make stale approvals detectable. Superseding decisions reverse earlier derived changes through reconstruction rather than destructive edits to source records.

Validate the entire decision set and show a dry-run impact report before publication. Conflicting or stale approvals cannot partially mutate the active snapshot. Record the ledger revision in the database so interrupted application can resume idempotently. Preserve the previous successful snapshot when a build fails.

Acceptance conditions for implementation:

- Approve, reject, and defer produce the documented distinct outcomes.
- Exporting proposals never overwrites a human's existing decisions.
- Identical imports preserve decisions and repeated application has no extra effect.
- Changed evidence invalidates only affected approvals and requires fresh review.
- Conflicting decisions fail validation without partial canonical changes.
- A superseding decision reverses a merge or correction while retaining audit history.
- Rebuilding the database reproduces the effective decisions from the local ledger.
- The wrong-year and transposed-number examples remain unresolved until explicitly approved.
- Review files and the ledger remain outside version control and MCP responses do not expose their private evidence.

The tradeoff is manual review effort and self-declared reviewer attribution. This is not a multi-user approval system or a tamper-proof audit service. At larger scale, add authenticated reviewers, a review queue, concurrent-edit controls, and durable audit storage. Keep that work outside the two-day core.

This decision supports the matching rubric through explicit merge methods and uncertainty, and the provenance rubric through attributable decisions. The repository supplies tests and sanitized examples. The model document explains the policy. The demo can show one reviewed correction within its existing time limit.

The workflow contract and planned commands are in Appendix I of [the project plan](project-plan.md). Concrete initial candidates are documented in [the trap investigation](trap-investigation.md).

## D003. Run the MCP server locally over stdio

Recorded October 24, 2026. Accepted for the challenge scope. Connection to the selected demo client remains unverified.

Run the Python application as a local MCP server launched by an agent client that supports stdio. The application loads the local data snapshot and exposes the six read-only tools. Protocol messages use stdin and stdout. Diagnostic logs use stderr with privacy filtering.

The challenge requires one-command local operation and a connected-agent demo. It does not require a public endpoint. A hosted service would add deployment, authentication, transport, and persistent-storage work without being necessary for those deliverables.

Keep the data pack, generated SQLite snapshot, and review artifacts on the same machine for the demo. Startup may prepare derived data through the maintenance path before serving. Tool calls themselves use a read-only connection and cannot initiate ingestion or review actions.

Acceptance conditions for implementation:

- Select a demo client with local stdio support and prove initialization, tool discovery, a tool call, and clean shutdown early.
- Document client configuration, prerequisites, filesystem paths, and the one-command startup procedure.
- Start successfully from a fresh checkout with the supplied data and documented prerequisites.
- Keep diagnostic output out of protocol stdout and keep source files unchanged during tool calls.
- Record all six required questions through the actual connected agent for the final demo.

The limitation is local access. This arrangement does not provide a remotely accessible partner service. Revisit it when remote clients are required. Evaluate the SDK's supported HTTP transport, authentication and authorization, persistent storage, process lifecycle, and operational monitoring before hosting. Do not assume switching transport alone makes the service production-ready.

This decision supports reproducible repository setup and the demo deliverable. Evidence comes from the local-run and demo requirements in [the brief](../gauntlet-challenge-requirements.md) and the planned P4 workflow.

## D004. Use SQLite for the initial local workload

Recorded October 24, 2026. Accepted as the initial storage choice. Local P1 and P2 measurements are recorded in their execution reports. Suitability for a larger workload remains unmeasured.

Store the canonical model, source evidence, and applied review-decision references in SQLite. The application accesses a local database file, so the challenge does not need a separately operated database service. Keep the original source pack and review ledger as rebuild inputs.

Choose this arrangement for the local, read-heavy challenge workload and two-day budget. Relational constraints and joins fit providers, properties, jobs, visits, and provenance. PostgreSQL would require additional setup for the current deliverable. A document store would not eliminate the need to reconcile identities and relationships.

Build and validate replacement snapshots through one maintenance writer. Publish only successful snapshots. Give the MCP server read-only access. Specify and test when running readers adopt a new snapshot so queries do not silently mix revisions. P1 and P2 verification exercise this publication behavior, including failed builds and review replay.

Acceptance conditions for implementation:

- Verify foreign keys, source-key uniqueness, repeat-import behavior, and evidence links.
- Test failed refreshes, snapshot adoption, and reconstruction from original observations and effective review decisions.
- Measure import duration, memory, query latency, and refresh behavior on the actual pack.
- Record the machine, data size, indexes, and workload with performance results.
- Keep queries parameterized and connection handling inside the storage boundary without building a speculative multi-database abstraction.

Do not claim SQLite stops working at 10,000 providers or that PostgreSQL automatically solves scale. Provider count alone does not describe job volume, recurrence expansion, concurrent clients, write frequency, or spatial-query demand. Our current full-rebuild strategy and application scans may become the limiting factors before database capacity does.

Revisit storage when measurements show that import or query budgets cannot be met with appropriate indexes and bounded work, or when deployment requires concurrent writers, multiple application hosts, stronger operational recovery, or server-side spatial indexing. Evaluate PostgreSQL and, if spatial queries justify it, PostGIS against that workload. Fix avoidable application costs before attributing every slowdown to SQLite.

A migration must preserve canonical IDs, source references, decision history, and query behavior. Validate constraints and compare the six required answers on the same snapshot before switching storage. Distributed hosting and a database migration remain outside the two-day core.

This decision supplies the rationale for the model document and the decision log's required discussion of 10,000 providers and week-two work. The [inventory](data-pack-inventory.json) establishes the current pack size. It is not a database benchmark.

## D005. Materialize canonical facts while retaining source observations

Recorded October 24, 2026 during P2 implementation. The implementation preserves every P1 source-local row and adds canonical tables and a source crosswalk in the same atomic SQLite snapshot. Queries use canonical facts and an allowlisted public projection. Supersession rebuilds from original observations and effective decisions.

Providers match automatically on a shared business phone plus corroborating trade evidence. Name or filename similarity creates a review proposal. Exact normalized addresses preserve units and can infer missing locality only from a unique supplied street segment. Property conflicts remain reviewable. Cross-source jobs without an immutable shared identifier remain separate or become review candidates even when provider, property, service category, and time agree. There are no such generated job candidates in the current pack under the conservative rule. This is not evidence that the hidden grader has no additional duplicate jobs.

Completion and date evidence are separate. Jobber completed visits and Housecall Pro completion timestamps support history. Workiz Done status supports completion, while its scheduled interval supplies an approximate service date. A status-update timestamp does not become an exact service date. Contradictory dates remain uncertain. CSV payment does not prove completion.

Public answers retain business labels, controlled service categories, opaque evidence IDs, and limitations. They omit homeowner contacts, raw notes, review evidence, and internal source paths. Exact-property answers separate confirmed completed jobs from other observations. Approximate street interpolation supports radius history but makes no driving-distance claim.

The tradeoff is conservative under-merging and manual review work. Canonical IDs reproduce for identical member sets and decisions, but a merge or split can change an ID. The current query implementation scans canonical documents; larger workloads need measured indexing and query changes before a database migration.

Verification and remaining limitations are recorded in [the P2 execution record](p2-execution.md). This decision does not approve any real correction or identity proposal.

P2 confidence labels are rule-based categories, not calibrated probabilities. Paired year corrections must be approved or superseded together. Approving only one endpoint is incompatible with the correction and fails before ledger changes.

## D006. Schema interview: lifecycle, constraints and service detail

On October 24, 2026 the operator accepted the first three schema interview recommendations: separate job lifecycle from completed service evidence; enforce core relationships and controlled canonical values in SQL; and combine service categories with privacy-safe descriptions. See [ADR 0001](adr/0001-separate-job-lifecycle-from-service-history.md), [ADR 0002](adr/0002-enforce-core-domain-invariants-in-sql.md), [ADR 0003](adr/0003-preserve-safe-service-detail.md), and the [domain glossary](../CONTEXT.md).

These are accepted design directions, not completed implementation. Counting grain, physical tables, lifecycle mappings and description policy remain open. The interview does not authorize schema migration or P3 implementation; the existing implementation and its earlier verification receipts remain unchanged.

The operator also accepted interview Q4–Q7: expose distinct-job and completed-visit counts separately within the requested window without inventing visits; map lifecycle explicitly per source and retain unknown/conflicting evidence; retain original, source-normalized and canonical representations with entity-appropriate columns; and generate public service descriptions only from recognized facts and approved wording, flagging unmapped services. ADRs 0001 and 0003 are updated; [ADR 0004](adr/0004-retain-source-normalized-and-canonical-layers.md) records the layer/storage tradeoff. Physical schema and migration details remain under discussion.

## D007. Schema interview: relationships, uncertainty, lineage and persistent identity

On October 24, 2026 the operator accepted Q8–Q11: related tables for aliases/trades/exclusions/service areas with declared and observed coverage kept separate; explicit temporal evidence states and distinct schedule/completion/status-update facts; field-level lineage for transformed or contested values; and canonical IDs that survive new evidence, with merge redirects and ambiguous split references.

See [ADR 0005](adr/0005-relational-provider-facts.md), [ADR 0006](adr/0006-represent-temporal-uncertainty-explicitly.md), [ADR 0007](adr/0007-retain-field-level-lineage.md), and [ADR 0008](adr/0008-persistent-canonical-identity.md). ADR 0008 replaces member-set-derived IDs as the intended design. D005 and the P2 report still describe the existing implementation; no migration or identity rewrite has occurred.

The [proposed table layout](schema-redesign.md) is the next interview artifact. Its unaccepted choices remain proposals. P3 implementation remains out of scope.

## D008. Schema interview: completion evidence, visit parents and unresolved properties

On October 24, 2026 the operator accepted Q12–Q14: a separate `service_completions` table with job and optional visit linkage; visits belong to exactly one job or estimate and inherit provider/property from that parent; jobs and estimates require a provider while allowing an explicitly unresolved property link without a placeholder property.

See [ADR 0009](adr/0009-separate-service-completion-evidence.md), [ADR 0010](adr/0010-inherit-visit-provider-and-property.md), and the Q14 addition to [ADR 0004](adr/0004-retain-source-normalized-and-canonical-layers.md). New physical columns and controlled values in [the column draft](schema-columns-draft.md) are proposals for the next round, not additional accepted decisions. No SQL, live database, review approval or P3 behavior changed.

## D009. Schema interview: accepted column semantics and controlled values

On October 24, 2026 the operator accepted Q15–Q19:

- Separate controlled job lifecycle, visit scheduling and estimate state vocabularies with original source statuses retained. Archived alone is not finished work; pending approval is not confirmed completion; completed estimates are not service completions.
- Each scheduled endpoint has a selected UTC value, independently established local date, evidence state and precision; timezone interpretation is explicit and contradictory combinations are rejected.
- Related job/estimate service rows permit multiple services, with controlled trade/service pairs, safe descriptions and mapped/unmapped/conflicting classification.
- Property-link states are resolved/missing/unresolved/conflicting; unit states are known/none/unknown/conflicting. A resolved link requires a property ID; no-unit requires affirmative evidence, not merely blank input.
- Money uses nullable exact minor units, separately evidenced currency and known/missing/disputed state. Missing is not zero; conflicting source totals are not summed merely because they refer to the same job.

The accepted value lists are in [the column draft](schema-columns-draft.md). ADRs 0001 and 0006 are updated and [ADR 0011](adr/0011-allow-multiple-services-per-job.md) records service cardinality. Remaining decisions are completion attribution/deduplication, property match keys, cross-source conflict selection, lineage integrity, durable identity bookkeeping, source-normalized column definitions, hours/calendar representation, and migration. No runtime or database change occurred.

## D010. Schema interview: evidence attribution and selection; identity storage still open

On October 24, 2026 the operator accepted Q20–Q22 and Q24, but did not accept Q23's storage arrangement:

- Reconcile supporting observations into completion evidence without inflating completed visits. Attribute completed service categories only when supported; otherwise retain job-level evidence with unknown service attribution. Report distinct jobs/visits separately and explain overlapping trade groups.
- Unknown-unit assertions do not automatically merge with known units. Preserve unresolved identity candidates and use unique supported reference inference for missing locality; avoid broad uniqueness constraints that collapse uncertain properties.
- Select canonical values using field-specific rules and exact valid human corrections, not one globally preferred source or latest ingestion time. Retain unresolved contradictions. Declared and observed coverage are distinct facts.
- Represent working-hour declarations separately from calendar event definitions. Preserve local time/timezone, effective dates and emergency qualifiers for hours; preserve calendar UID, date/time form, exclusive end, recurrence, status, transparency and provenance. P3 calculation remains excluded.

Q23 remains open. The user questioned SQLite durability. Clarification: SQLite supports durable transactional storage; the current replace-the-whole-file rebuild policy is the reason authoritative identity state needs preservation. Separating identity storage into another file is one option, not a requirement of SQLite. A single persistent SQLite database with transactional replacement of derived data is another candidate, pending agreement. No engine migration, rebuild redesign or registry storage choice has been approved.

## D011. Persistent SQLite accepted; continuous sync is a production requirement

On October 24, 2026 the operator accepted revised Q23: retain one persistent SQLite database, stage and validate imports, and transactionally publish derived data/identity changes while retaining last-successful-state behavior. See [ADR 0012](adr/0012-use-persistent-sqlite-with-transactional-imports.md). Backup/restore and crash-recovery verification are part of that design. This supersedes the intended whole-file replacement architecture; existing code is unchanged.

The operator additionally stated that production must support continuous data-source ingestion and syncing. Record this as a design requirement, not a claim that the current full-pack importer supports incremental or live ingestion. The challenge's file-only input scope, stop-before-P3 boundary and lack of authorization for live CRM integration remain unchanged. The [sync-readiness note](sync-readiness.md) distinguishes current behavior from proposed production work.

## D012. Source delivery completeness and scope

On October 24, 2026 the operator accepted Q25. Deliveries identify source/account, scope and complete-snapshot versus partial-change semantics. Only verified complete coverage can establish disappearance within that scope; partial deliveries do not delete omitted records. Scoped disappearance, explicit deletion and cancellation remain distinct, and history is preserved. See [ADR 0013](adr/0013-distinguish-complete-and-partial-source-deliveries.md).

The conversation's weekly schedule example is illustrative: absence can mean an appointment moved outside the week, not deletion. Runtime payload formats, checkpoint storage, retries, update ordering and failure/freshness policy remain design work. No code or live data changed.

## D013. Sync principles accepted; prioritize a small initial design

On October 24, 2026 the operator accepted Q26–Q29: source-supported update ordering rather than arrival order; idempotent retries with applied checkpoint/publication consistency; source/account batch failure isolation preserving prior successful data; and per-source coverage/freshness reporting. These are target contracts, not implemented capabilities.

The operator also directed us to avoid spending more design effort on edge cases or overengineering the initial system. Keep the accepted domain semantics, but stop expanding the interview into speculative infrastructure. Deliver the smallest schema redesign that supports the supplied pack and leaves clear extension points for production syncing. Routine implementation details should be resolved through a concrete design and tests rather than another broad question round.

Immediate scope: entity-appropriate relational columns and relationships; separate lifecycle/completion facts; controlled services and safe descriptions; explicit uncertainty/provenance; persistent identity and transactional imports; preservation of existing review and query behavior except explicitly accepted semantic corrections. Continue using local supplied files and the existing CLI. P3 remains excluded.

Production-sync follow-up: live connectors, polling/webhooks, durable delivery queues, full incremental change processing, account-level retry orchestration and refresh/staleness policies. Capture the accepted delivery/checkpoint/freshness contracts in the design, but do not build an unused general-purpose sync framework now. The current importer must not be advertised as supporting those features. Existing accepted identity/review guarantees are not silently relaxed.

No runtime edits, migration, publication or implementation authorization resulted from this discussion.

## D014. P2R implementation of the accepted schema decisions

The subsequent explicit P2R request authorizes implementing D006–D013 without starting P3. Schema version 2 now uses typed source assertions, relational canonical facts, separate lifecycle/completion evidence, persistent identities and transactional SQLite publication. The earlier interview entries and ADR statements saying “not implemented” describe their decision-time state; see [the P2R execution record](p2r-execution.md) for current verification and [migration notes](p2r-migration.md) for recovery.

The local review ledger remains authoritative and separate from the SQLite commit. Rule version `reconciliation-v2` revalidates old approvals. No real deferred correction was approved for testing. Unknown units remain unknown; complete unknown-unit address assertions can match each other but never automatically match known units. Completed-visit counts require independent visit-completion evidence; job-level completion remains visible separately. Exact-date history windows require Chicago-midnight boundaries rather than guessing inclusion of date-only facts in partial days.

Full local snapshots remain the implementation boundary. This does not implement continuous source sync, availability, travel, remote deployment or MCP serving. No publication or merge is authorized by this entry.


## D015. Implement P3 on the merged P2R model

On October 24, 2026 the operator authorized P3 implementation and verification in Poteto Mode, including stale documentation fixes. The baseline is merged `main` at `c6c151e`. This request supersedes the earlier stop-before-P3 boundary. It does not authorize P4, publication, or merge.

P3 derives candidate openings from declared working hours minus active job visits, scheduled estimate appointments, and blocking calendar events. It adds deterministic provider rankings with eligibility, evidence, confidence, and duration assumptions. Missing hours, incomplete intervals, conflicting evidence, and insufficient schedule coverage must remain explicit uncertainty. Capacity remains conservative at provider level. Travel remains unmodeled under D001. Use November 2, 2026 in America/Chicago as the reproducible reference date.

D013's small-initial-design scope still applies. Use local supplied files, persistent SQLite, the P2R identity registry and canonical facts, and the existing CLI. Preserve source evidence, review semantics, and history behavior. Production connectors, queues, incremental sync, worker-capacity modeling, and travel optimization remain deferred. P4 owns MCP serving and the connected-agent demo.

The [P3 plan](project-plan.md#compute-defensible-openings-and-provider-rankings-p3) defines unit, live, performance, and independent-review checks. This entry records authorization and scope, not a completed implementation or verification result.

P3 implementation and verification are now recorded in [the P3 execution record](p3-execution.md). Current evidence includes 95 passing tests, ten passing CLI lanes, independent review, and bounded performance checks. No P4 implementation or production-sync claim follows from this completion.

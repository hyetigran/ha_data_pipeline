# Project decision log

This log records design decisions before implementation. Acceptance conditions describe checks to build, not checks that have already passed.

P1 implementation was authorized on October 24, 2026, with an explicit stop before P2 and no publication or merge. Execution evidence and any remaining limitations are recorded in `docs/p1-execution.md`. Decisions below remain design commitments until their acceptance checks are recorded there.

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

Recorded October 24, 2026. Accepted by the user's request to add human review to the plan. The workflow is planned and not yet implemented. No specific correction or merge is approved by this decision.

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

Recorded October 24, 2026. Accepted as the initial storage choice. Performance and scale suitability remain unmeasured.

Store the canonical model, source evidence, and applied review-decision references in SQLite. The application accesses a local database file, so the challenge does not need a separately operated database service. Keep the original source pack and review ledger as rebuild inputs.

Choose this arrangement for the local, read-heavy challenge workload and two-day budget. Relational constraints and joins fit providers, properties, jobs, visits, and provenance. PostgreSQL would require additional setup for the current deliverable. A document store would not eliminate the need to reconcile identities and relationships.

Build and validate replacement snapshots through one maintenance writer. Publish only successful snapshots. Give the MCP server read-only access. Specify and test when running readers adopt a new snapshot so queries do not silently mix revisions. This publication behavior is an implementation requirement, not a demonstrated capability of the application today.

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

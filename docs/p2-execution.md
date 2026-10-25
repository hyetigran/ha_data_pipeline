# P2 execution record

P2 implements canonical identities, four history/query operations, and local human review. P3 availability, rankings, and MCP serving are excluded. No commit, publication, or merge was performed for P2. The active review ledger contains no approved real-world decisions.

## Work checklist

- [x] `how` over the affected subsystem.
- [x] `architect` for parallel design exploration.
- [x] Write the throughput checkpoint as four todo items.
- [x] Delegate code-writing to a subagent.
- [x] Verify on the matching surface.
- [x] Rebase into small, ordered commits. Stack follow-ups. Skip commits because this handoff is the local working tree.
- [x] If the design is contested, `interrogate` before shipping. Skip because the independent design judge and both candidates agreed on the synthesized design.
- [x] Run **Opening a PR**. Skip publication under the user's explicit instruction.

## Throughput checkpoint

- Blocking first steps. Read P1 boundaries, the review contract, and actual source shapes before choosing reconciliation interfaces.
- Independent workstreams. Two read-only designs preceded one implementation owner. Independent source-answer derivation and correctness reviews ran separately.
- Shared mutable state. One owner initially changed the coupled schema, review, and query code. Later fixes had explicit file ownership. Verification used separate temporary databases and ledgers.
- Smallest safe decomposition. Reconciliation and review publication share invariants, so one owner implemented both. The lead owned acceptance checks and documentation. Performance measurements ran separately from full verification workloads.

## Architecture and policy

Candidate A materializes canonical query tables in the same staged SQLite database as the source observations. Candidate B resolves identities through views and override tables in a pinned snapshot. The independent judge preferred A because history queries and later scheduling can share one resolved model. We retained B's explicit ledger revision pinning. Source-local rows remain intact.

The Model the Domain principle shaped typed proposals, decisions, and effective ledger state. It also shaped the paired timestamp approval invariant. The Prove It Works principle required actual CLI subprocesses and database assertions, alongside tests.

The parent is `a082d3c12bb0c7dec9f394bc4f4da6cc4c164f42`. `artifacts/P2/implementation-manifest.json` identifies the verified implementation by file hashes. The skill's default model families and optional `cursor-team-kit` CLI-control tools were unavailable. Reviews used independent agents on the inherited model. No cross-model consensus or unavailable tool use is claimed.

P2 adds `addresses.py`, `identity.py`, `review.py`, `queries.py`, and `privacy.py`. Canonical tables and their source crosswalk are derived from immutable observations plus effective ledger decisions. The database stores the ledger revision. Readers retain their current snapshot until reconnecting.

A business phone requires corroborating trade evidence for automatic provider matching. Filename/name candidates stay separate. Exact normalized addresses preserve units and infer locality only from a unique supplied segment. Texas/TX and street suffix variants normalize deterministically. A comma followed by a ZIP is parsed as a ZIP. Coordinates are approximate segment interpolation.

Jobs remain distinct unless their source identity repeats or an explicit reviewed match applies. Cross-source candidates require provider, property, service, and time agreement. No cross-source job proposals occur in this pack under that conservative rule. This does not prove that all hidden duplicates have been discovered. Matching confidence is a policy category, not a calibrated probability.

Jobber completed visits and Housecall Pro completion timestamps establish history. Workiz Done establishes completion but uses a qualified scheduled service date. Status update time is not an exact service date. Contradictory year evidence remains unresolved. CSV payment never proves completion.

## Review workflow

The commands are documented in [README](../README.md), with a generated [JSON schema](../schemas/reconciliation-review.schema.json). Export preserves edits and includes original observations, proposed actions, source hashes, confidence reasons, and conflicts. Files are private and owner-readable/writable. Review evidence never appears in public query responses.

Validation and dry-run build a prospective snapshot from current sources. They reject forged proposals, stale evidence, invalid intervals, and incompatible effective decisions before recording anything. Apply holds the database and ledger locks, durably appends decisions, and atomically publishes the validated snapshot. A failure after append reports `recorded_not_applied`; rebuild replays the ledger. A post-publication directory sync failure reports a durability warning rather than claiming rollback.

Approve applies the exact action. Reject leaves it unapplied and suppresses it from the new-review count. Defer keeps it unresolved. Supersession preserves the prior event and reconstructs derived data from originals. Paired year endpoints must remain jointly approved or jointly unapplied. Decisions depend on all relevant match evidence, including provider, property, street-reference, and visit records. Unrelated evidence changes do not invalidate an approval.

The actual wrong-year and transposed-number proposals remain deferred. The address proposal includes six original supporting observations. Review attribution is self-declared and local. This is not a multi-user or tamper-proof audit service.

## Verification

All 44 tests, Ruff, mypy, and ten indexed acceptance lanes pass. Final machine-readable results are in `artifacts/P2/summary.json`. Test, lint, and type-check output is in `unit.log`, `ruff.log`, and `mypy.log` in that directory.

- `scripts/verify_p2_independent.py` compares real query answers against independently inspected source records and recursively checks the public projection.
- `scripts/verify_p2_cli.py` runs real export, validate, dry-run, apply, repeat, supersede, and stale-source CLI operations in disposable snapshots. It verifies exact derived correction values and their reversal. The active database is unchanged.
- `scripts/verify_p2_queries.py` calls the real query CLI on a sanitized snapshot. Apt 4 and #4 share history; unit 5 remains separate. A mathematically constructed half-mile point is included and a point just outside is excluded.
- `scripts/verify_p2_review.py` is a sanitized integration demonstration with a fixture importer. It is not substituted for the separate real CLI proof.
- Existing P1 tests continue to cover source accounting, duplicate import behavior, and failed snapshot preservation.

Independent expected answers were derived from P1 observations without importing P2 code. Fourteen selected records were also checked against raw files. The expanded radius oracle uses the supplied street reference directly.

| Question | Verified answer within P2 scope |
| --- | --- |
| Q1 | 971 completed distinct source jobs within half a mile and the 24-month window. The independent ID set matches the query evidence. |
| Q3 | Four active CRM appointments on the block, including an estimate. Ray's CSV entry is separate uncertain evidence. The cancelled appointment is excluded. |
| Q4 | Lone Star aliases combine with corroboration. There are 262 completed source jobs. Declared and observed service ZIPs are separate. Openings explicitly await P3. |
| Q5 | Four confirmed completed jobs at 5823 Belmont. Ray's drywall record remains unconfirmed. Upcoming/cancelled work does not increase completed history. |

Early audits found phone-only matching, incomplete dry-run validation, unsafe output-path collisions, missing original review observations, misleading failure reporting, and incomplete provider summaries. Those defects were corrected and covered by subsequent checks. Independent comparison found the Texas/TX omission, CSV ZIP parsing defect, and missing transposed-address proposal. Focused reviews added paired interval integrity and complete match-evidence dependencies.

Ten acceptance lanes are indexed in `artifacts/P2/lane-1.json` through `lane-10.json`. The lanes share reusable real CLI receipts instead of launching ten concurrent writers. No unavailable screenshot tool is claimed.

## Performance

`artifacts/P2/benchmark.json` contains five measured full imports after one warmup and thirty warm requests per query. Each query opens a read-only connection, consumes its result, and serializes it. Every import verifies persisted counts and database integrity. Measurements use macOS arm64, Python 3.13.2, and ten logical CPUs. Load averages and exact ranges are in the receipt.

P1's archived parent import took a median 6.02 seconds, range 5.51 to 6.59 seconds, with 60.80 MiB peak memory. Full P2 adds reconciliation, so these unlike operations do not justify a regression ratio. The parent has no history-query API. No speedup is claimed.

A separate cProfile run identifies repeated street-reference normalization as the largest projection cost, followed by SQLite inserts. Profile timings are not benchmark timings. The final budget verdict and measurements are copied into the summary receipt. Targets are 60 seconds per import, 512 MiB peak memory, and 500 ms query p95.

## Review artifacts and remaining uncertainty

[Proposal preview](../artifacts/P2/review/proposal-preview.png), [dry-run preview](../artifacts/P2/review/dry-run-preview.png), and [42-second sanitized playback](../artifacts/P2/review/sanitized-review.mp4) render saved integration receipts. They are labeled rendered playback, not native terminal footage. Real CLI commands, exit codes, and results are separately saved in `artifacts/P2/review/cli-workflow.json`. Operator review before any future merge remains outstanding.

- Three provider source links remain ambiguous. Do not force the model to the advertised provider count.
- Property locality conflicts remain reviewable. Typos without supported reference matches retain missing coordinates.
- Street coordinates are approximate. Absent out-of-area history is not evidence of no experience.
- CSV completion, some dates, and durations remain uncertain. The block query does not claim a complete confirmed appointment list from that source.
- Conservative job matching can under-merge. No hidden grader crosswalk is available.
- Dry-run reports entity and interval effects, not a complete before/after answer transcript for every query.
- Full rebuilds and document scans need measurement and indexing work at larger scale. No 10,000-provider capacity claim is made.
- P3 availability, rankings, travel calculations, and P4 MCP serving are not implemented.

Two `.cursor/skills/verify-house-account` files changed outside this P2 work and were preserved. The local decision trail is `artifacts/P2/decisions.tsv`. Independent same-model review found no remaining defect in the paired review and dependency changes. The reviewer noted draft documentation and unavailable transcript-level audit; this completed report and the appended trail resolve the documentation draft, without claiming a transcript audit.

## Final measured snapshot

The snapshot retains 46,092 source records and 46,888 occurrences. Its canonical projection has 43 provider groups, 3,837 properties, 11,752 jobs, and 15,512 visits. All 176 input files remain unchanged. There are 289 active deferred proposals and 74 archived unreviewed proposal versions. The real decision ledger is empty.

Five full imports took a median 9.99 seconds, range 9.88 to 10.20 seconds. Peak memory was 314.23 MiB. Thirty requests per query measured p95s of 90.90 ms for radius history, 91.34 ms for block schedule, 88.09 ms for exact-property history, and 84.02 ms for provider summary. All planned budgets passed with zero measured request failures.

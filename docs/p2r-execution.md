# P2R execution record

Implementation and verification are complete. The active local database is migrated to schema version 2, with its verified pre-migration backup retained. P3 and publication are excluded. Existing uncommitted P2 work and unrelated verification-skill edits are preserved.

## Workflow

- [x] Read the Principles section of the poteto-mode skill.
- [x] Phase A: Frame. Done means relational canonical/source facts, stable identities, safe transactional imports/review replay and verified SQL queries on all supplied sources.
- [x] Phase B: Design the workflow. Capture the old artifact first. Two read-only implementation sketches review the accepted architecture without reopening domain decisions.
- [x] Phase C: Run the loop. R1 schema, R2 normalization/completion, R3 publication/identity, R4 queries and verification.
- [x] Phase D: Keep the audit trail in artifacts/P2R/decisions.tsv.
- [x] Phase E: Verify and hand back. Independent review, real CLI receipts, performance budget, updated documentation and remaining uncertainties.
- [ ] Opening a PR. Skip publication and merge under the explicit user instruction.

## Throughput checkpoint

1. Blocking first steps. Capture the live P2 database, source hashes, code and query baseline before changing shared schema.
2. Independent workstreams. Read-only architecture checks and independent acceptance fixtures can run alongside one implementation owner.
3. Shared mutable state. One owner changes coupled schema, storage, identity and review code. Other writers own only separate verification/docs paths. Experiments use disposable databases and review files.
4. Smallest safe decomposition. Keep the existing adapter boundary and local CLI; remove generic storage fields and canonical document scans without adding production-sync machinery.

Data shape: source observations remain immutable evidence. Domain-specific source tables feed canonical provider/property/job/estimate/visit/service/completion rows. A persistent identity registry survives transactional publication. Human decisions remain in the existing append-only local ledger.

The skill's preferred model families and custom Task/control-cli tooling are unavailable. Available inherited-model agents and actual shell CLI processes provide implementation/review and runtime evidence. No cross-model consensus is claimed.

## Verification findings

The baseline is frozen under `artifacts/P2R/baseline/`, including source hashes, the P2 SQLite backup, original code, canonical membership and four query answers. The baseline suite passed 52 tests. Baseline performance was measured from the copied code before runtime changes.

The final suite passes 73 tests. Ruff and mypy pass. New cases cover invalid SQL states, recurring lifecycle, multi-service attribution, reviewed endpoint lineage, stable IDs through growth/merge/split, process exit around commit, consistent readers, migration refusal, backup restoration and calendar/hour declaration preservation.

The full-pack migration and repeat-import checks pass with all 46,092 source records and 46,888 occurrences. All 176 file hashes and all 20,609 prior canonical memberships are unchanged. The ordinary database inode is preserved. An injected import failure preserves the published facts. Restoring the migration backup reproduces all four original P2 answers with the frozen P2 query code.

Independent source checks retain four exact-home completed jobs, four block appointments and 262 completed distinct jobs for Lone Star Plumbing Co. The radius result is 969 rather than 971: two combined patch/paint jobs retain completion evidence without unsupported specific-service credit. Fresh Nest #1034 stays active with 46 independently completed visits and two upcoming visits. The Nov 1 DST start keeps its local date and ambiguity without selecting a UTC instant.

Full-pack private receipts, query answers, membership changes and source accounting live in `artifacts/P2R/`. [Migration and recovery](p2r-migration.md) explains the schema and count changes. The real review CLI passed approve/reject/defer, exact correction effects, dry-run preservation, repeat apply, supersession and stale-evidence rejection on a disposable copy. It exercised 3 approvals, 1 rejection and 285 deferrals; no active decision was approved. The isolated performance budget also passed.

## Scope and remaining uncertainty

No real pending correction is approved. The wrong-year and transposed-house-number cases stay deferred. Unresolved provider/property matches, unknown units, unclassified services, approximate geocodes, missing CSV durations and source-specific completion-date precision remain visible. Exact complete unknown-unit addresses may match each other; they never automatically match a known unit. Completed-visit counts require independent completion evidence, rather than inheriting job completion onto a projected schedule.

The supplied data remains a full local snapshot. Production continuous sync, recurrence expansion, availability, travel and MCP serving are outside P2R. The hidden grader kit was not used and finding all 22 seeded traps is not established.

Independent review found and corrected DST fallback keys, multi-service attribution, completion deduplication, SQL null-check loopholes, endpoint decision lineage, parent mutation constraints and publication dependency ordering. Comment review found no unnecessary comments, suppressions or unresolved comment constraints (zero deletions/restorations). The workflow adapted unavailable custom agent tooling to available agents; no cross-model consensus is claimed.

## Performance

One warmup and five measured fresh-process imports used the same supplied pack. Thirty warm requests per query included connection creation and full JSON serialization. No other task import was run concurrently with the reported benchmark. Machine load is recorded in the receipt; these are local observations, not production capacity estimates.

| Measurement | Frozen P2 | P2R |
| --- | ---: | ---: |
| Median full-process import | 9.96 s | 28.80 s |
| Import range | 9.87–10.08 s | 21.44–35.93 s |
| Peak RSS | 314.6 MiB | 319.2 MiB |
| Radius query p95 | 93.9 ms | 37.6 ms |
| Block query p95 | 87.9 ms | 22.5 ms |
| Property query p95 | 89.1 ms | 6.5 ms |
| Provider query p95 | 81.7 ms | 23.2 ms |

All P2R runs fit the 60-second/512-MiB import budget and 500-ms query p95 budget, with zero reported errors. Relational projection, persistent identity and additional lineage increase import work. Query semantics also changed, so these measurements do not establish an identical-work speedup ratio. Full receipts: `artifacts/P2R/benchmark.json` and `baseline/benchmark.json`.

## Final local state

The active `var/house_account.sqlite` passed integrity, foreign-key and independent query checks after migration. Its backup is `var/house_account.sqlite.pre-v2.bak`. The refreshed review file contains 289 deferred active proposals and 363 preserved stale versions. The authoritative ledger remains empty. Source hashes are unchanged. The final machine-readable result is `artifacts/P2R/summary.json`.

Model the Domain guided the separate job lifecycle, visits and completion evidence. Prove It Works guided disposable migration, real CLI replay and crash tests. Sequence Verifiable Units kept baseline, schema, publication and query gates explicit. The audit trail is `artifacts/P2R/decisions.tsv`.

P2R is complete. P3 was not started. No commit, push, PR or merge was made. Existing unrelated verification-skill edits were preserved.

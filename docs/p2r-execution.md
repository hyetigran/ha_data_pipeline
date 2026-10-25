# P2R execution record

This record describes the original schema-version-2 migration. The run retained a verified backup and preserved existing local changes. P3 and publication were outside that run. [Delivery status](project-plan.md) records subsequent implementation and merges.



## Verification findings

The baseline is frozen under `artifacts/P2R/baseline/`, including source hashes, the P2 SQLite backup, original code, canonical membership and four query answers. The baseline suite passed 52 tests. Baseline performance was measured from the copied code before runtime changes.

The final suite passes 73 tests. Ruff and mypy pass. New cases cover invalid SQL states, recurring lifecycle, multi-service attribution, reviewed endpoint lineage, stable IDs through growth/merge/split, process exit around commit, consistent readers, migration refusal, backup restoration and calendar/hour declaration preservation.

The full-pack migration and repeat-import checks pass with all 46,092 source records and 46,888 occurrences. All 176 file hashes and all 20,609 prior canonical memberships are unchanged. The ordinary database inode is preserved. An injected import failure preserves the published facts. Restoring the migration backup reproduces all four original P2 answers with the frozen P2 query code.

Independent source checks retain four exact-home completed jobs, four block appointments and 262 completed distinct jobs for Lone Star Plumbing Co. The radius result is 969 rather than 971: two combined patch/paint jobs retain completion evidence without unsupported specific-service credit. Fresh Nest #1034 stays active with 46 independently completed visits and two upcoming visits. The Nov 1 DST start keeps its local date and ambiguity without selecting a UTC instant.

Full-pack private receipts, query answers, membership changes and source accounting live in `artifacts/P2R/`. [The data model](data-model.md) explains the schema. [Migration and recovery](p2r-migration.md) describes the upgrade procedure. The real review CLI passed approve/reject/defer, exact correction effects, dry-run preservation, repeat apply, supersession and stale-evidence rejection on a disposable copy. It exercised 3 approvals, 1 rejection and 285 deferrals. No active decision was approved. The isolated performance budget also passed.

## Scope and remaining uncertainty

No real pending correction is approved. The wrong-year and transposed-house-number cases stay deferred. Unresolved provider/property matches, unknown units, unclassified services, approximate geocodes, missing CSV durations and source-specific completion-date precision remain visible. Exact complete unknown-unit addresses may match each other. They never automatically match a known unit. Completed-visit counts require independent completion evidence, rather than inheriting job completion onto a projected schedule.

The supplied data remains a full local snapshot. Production continuous sync, recurrence expansion, availability, travel and MCP serving are outside P2R. The hidden grader kit was not used and finding all 22 seeded traps is not established.

Independent review found and corrected DST fallback keys, multi-service attribution, completion deduplication, SQL null-check loopholes, endpoint decision lineage, parent mutation constraints and publication dependency ordering. Comment review found no unnecessary comments, suppressions or unresolved comment constraints (zero deletions/restorations). The workflow adapted unavailable custom agent tooling to available agents. No cross-model consensus is claimed.

## Performance

One warmup and five measured fresh-process imports used the same supplied pack. Thirty warm requests per query included connection creation and full JSON serialization. No other task import was run concurrently with the reported benchmark. Machine load is recorded in the receipt. These are local observations, not production capacity estimates.

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

## Local state at the end of P2R

The active `var/house_account.sqlite` passed integrity, foreign-key and independent query checks after migration. Its backup is `var/house_account.sqlite.pre-v2.bak`. The refreshed review file contains 289 deferred active proposals and 363 preserved stale versions. The authoritative ledger remains empty. Source hashes are unchanged. The final machine-readable result is `artifacts/P2R/summary.json`.


P3 had not started at the end of this run. The run did not publish code.

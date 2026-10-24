# Implement P1 with source-local identities

The user authorized P1 implementation on October 24, 2026. Stop before P2. Do not publish, push, open a PR, or merge. The repository has no commits, so no executable trunk baseline exists. Verification uses the original source manifest and the completed working tree rather than claiming a comparison with an earlier implementation.

## Execution checklist

- [x] Ground the design in the existing plan, decisions, source inspection, and unchanged pack inventory. No existing application requires a code walkthrough.
- [x] Explore two architectural candidates in parallel. Compare an observation stream with adapter-owned relational batches.
- [x] Select a typed observation boundary with explicit relational entities. Retain every occurrence separately from each unique source record. Storage owns constraints and publication.
- [x] Implement source adapters, validation, storage, and the CLI.
- [x] Exercise the real CLI against the full pack and targeted fixtures. Verify the ten P1 scenarios.
- [x] Run lint, type checks, meaningful tests, and performance checks.
- [x] Independently review privacy, provenance, and failure behavior. Resolve findings and rerun affected checks.
- [x] Document results and stop before P2.
- [x] Skip publication and merge. The user's instruction prohibits them.

## Throughput checkpoint

- Blocking first steps. Fix the observation and entity contract before parallel adapter work. Reproduce the input manifest before implementation.
- Independent workstreams. One implementation owner controls coupled model, adapters, storage, and tests. The root independently verifies outcomes and writes evidence documentation.
- Shared mutable state. Source files are immutable. Imports build isolated candidates. A maintenance lock prevents competing publication. Verification uses separate temporary databases.
- Smallest safe decomposition. One code owner avoids schema drift across six adapters. Independent review follows the first runnable version, while the root checks acceptance assumptions.

## Design choice

The observation-stream candidate has the smaller adapter contract and supports per-occurrence accounting. The relational-batch candidate makes entity relationships explicit. Combine the observation envelope with typed relational entities rather than putting unvalidated arbitrary dictionaries in the database layer.

The two reviewers agreed that P1 identities must remain source-scoped, repeated occurrences must survive deduplication, and malformed source containers must abort publication. One suggested unresolved as an accepted-record flag. Use exclusive dispositions for the summary instead so accepted, duplicate, unresolved, and rejected add exactly to seen. Issue counts remain a separate diagnostic dimension.

P1 lane 10 means exact source-duplicate consolidation with evidence. Cross-source provider matching belongs to P2. Runtime recurrence expansion is a dependency probe only. Availability computation belongs to P3. MCP transport initialization is a compatibility probe only. The six tools belong to P4.

The requested skill's default model families and cloud VM workflow are unavailable here. Design exploration and implementation use inherited-model agents and isolated local processes. Terminal screenshots are supplementary; JSON transcripts, database assertions, and command exit codes are the authoritative evidence.

## Verification results

P1 is implemented and verified against the supplied pack. P2 has not started. No commits, pushes, pull requests, or merges were made.

| Check | Result | Evidence |
| --- | --- | --- |
| Meaningful tests | 21 passed | `artifacts/P1/unit.log` |
| Ruff | Passed | `artifacts/P1/ruff.log` |
| mypy | Passed across seven source files | `artifacts/P1/mypy.log` |
| Ten live scenarios | All passed through CLI subprocesses and database assertions | `artifacts/P1/live.json` and individual lane files |
| Fresh environment startup | Passed with no prior virtual environment or database, using cached pinned dependencies | `artifacts/P1/fresh-start.json` |
| Independent repeat and failure checks | Stable IDs and counts; failures preserved the database SHA-256 | `artifacts/P1/root-failure-repeat.json` |
| Source preservation | All 176 input file hashes unchanged | `artifacts/P1/inventory.json` |
| Final implementation identity | 18 file hashes matched after final verification | `artifacts/P1/implementation-manifest.json` |
| Dependency compatibility | Real MCP stdio initialization and calendar recurrence probe passed | `artifacts/P1/mcp-probe.json` and `dependency-probe.json` |

The final project-local snapshot is `var/house_account.sqlite`. Recreate it with `uv run --locked house-account ingest --data data --database var/house_account.sqlite --report artifacts/P1/import.json`. The snapshot contains private raw evidence and uses owner-only permissions. The input pack, generated database, and execution artifacts are excluded from Git.

## Source accounting

The final report contains 46,888 input occurrences and 46,092 distinct source records. These include nested entity observations, not just jobs. Every source has exclusive accepted, duplicate, unresolved, and rejected counters whose sum equals seen. The successful import has no rejected observations. Structural failures abort publication rather than publish a partially rejected pack.

| Source | Verified input accounting |
| --- | --- |
| Jobber | 15 accounts, 2,964 customers, 2,964 property nodes, 4,267 jobs, 7,658 visits |
| Housecall Pro | 15 accounts, 3,551 customers, 4,633 job rows consolidated to 4,630 source jobs, 689 estimates |
| Workiz | 11 accounts and 2,657 jobs, with embedded customer and property assertions retained |
| Spreadsheet | 206 rows, including eight exact repeated rows, resulting in 198 source jobs |
| Calendars | 91 events across two calendars, with recurrence definitions preserved |
| Profiles | 40 profile assertions with independent provider identities |
| Reference | 354 street segments |

Six empty Housecall Pro estimate pages are validated and recorded explicitly. They are not missing source records. The database has 11,752 source-local jobs, 689 estimates, and 15,512 visits. Of the estimate visits, 131 are scheduled and 558 are historical estimate appointments. Neither category is stored as completed service jobs.

The 84 provider rows and 8,575 property rows are source-local identities, not estimates of unique real-world businesses or homes. P2 performs cross-source reconciliation. Workiz customer payload variants remain separate evidence instead of last-write-wins updates.

## Failure and publication guarantees

A full repeat import preserves source IDs, content hashes, entity counts, and occurrence accounting. Ingestion timestamps and snapshot IDs change intentionally. A failure injected after 23,000 observations preserves the prior published database byte-for-byte. The root independently verified another failure after 20,000 observations and malformed source JSON with the same result.

Tests also cover missing files, source mutation during import, conflicting source identities, broken references, concurrent-writer rejection, and old-reader behavior. Existing readers retain their previous snapshot until reconnecting. Successful publication creates no WAL sidecars.

Two review findings were fixed. First, a directory-sync failure after replacement now reports published data with uncertain power-loss durability. It does not falsely claim rollback. Second, the raw data pack is explicitly excluded from Git. A report-output failure after successful publication has its own status and exit code.

The final independent audit found no remaining blocker for P1. It was a static review of the frozen source. Runtime proof comes from the linked tests and live receipts. Comment review found no correctness suppressions. The optional redundant comment did not affect the verdict.

## Performance result

Five measured fresh-process imports after one warmup had a median end-to-end duration of 5.796 seconds and a range of 5.786 to 5.927 seconds. Peak process memory was 61 MiB. Each run rebuilt the database and verified stored record counts and integrity. Both the 60-second and 512-MiB P1 target budgets passed.

This measures the supplied pack on macOS arm64 with Python 3.13.2 and ten logical CPUs. Filesystem caches were warm. Ambient load reached 9.70 at the end, so the numbers include machine contention. There is no prior importer baseline and no speedup claim.

A separate, untimed-for-comparison profile identified SQLite statement execution as the largest measured cost, followed by JSON encoding. The profile is not part of the five reported timings. See `artifacts/P1/benchmark.json` and `profile-summary.txt` for the measurements and conditions.

## Remaining uncertainty and scope

- Cross-source aliases, property matching, job reconciliation, and the human review file are P2 work.
- The wrong-year and transposed-number records remain unchanged. The wrong-year record carries a temporal inconsistency issue.
- Spreadsheet rows retain unresolved completion, dates, and durations. P1 does not infer work completion from the paid marker.
- Four shorthand working-hours declarations remain ambiguous. Emergency-only hours retain their qualifier.
- One CRM local timestamp is ambiguous or invalid and remains unresolved. Missing intervals remain explicit issues.
- Recurrence definitions and all-day semantics are preserved, but availability and ranking are P3 work. Travel is unmodeled.
- The package passed an MCP dependency handshake. Application tools and the connected-agent demo remain P4 work.
- The packaged manifest intentionally requires this supplied layout. Adding an account or source requires an explicit manifest and adapter registration update. Incremental synchronization is not implemented.
- Locking uses POSIX `fcntl`. This implementation was verified on macOS. Windows support is not claimed.
- Local tests replace the unavailable cloud VM and Cursor control-skill workflow. There is no executable trunk baseline or final commit SHA. Implementation hashes identify the tested files.

Model the Domain shaped the separate job, estimate, and visit relationships. Boundary Discipline keeps source-specific parsing and empty-page classification in adapters. Make Operations Idempotent shaped stable source identities and replace-on-success snapshots. Prove It Works required real subprocess imports and assertions against the stored database.

# Replace and recover

Repeat an import safely, retain the old snapshot when input validation fails, and distinguish successful publication from failure to write its report.

## Sub-features

- `replace-repeat`: repeat import preserves source IDs, content hashes, counts, and occurrence accounting.
- `replace-failed-input`: invalid input exits 1 without replacing the previous snapshot.
- `replace-failed-report`: a report write failure exits 2 while the published snapshot remains usable.

## How to get to it (user POV)

Run `house-account ingest` again with the same database destination. Inspect exit status and JSON on stdout/stderr. Reconnect a read-only database client to see a newly published snapshot.

## Driving it with verify.py

Preconditions: Launch and doctor pass. The helper first creates the existing snapshot needed by these journeys.

- **Repeat and fail.** Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py replacement`. Lane 8 repeats a real CLI import and verifies stable IDs/hashes/accounting. The helper then points the CLI at a missing pack, expects exit 1 with status failed, and compares snapshot bytes by SHA-256. Finally it supplies a directory for `--report`, expects exit 2 and published_report_failed, and reconnects to verify integrity and persisted job count.
- **Proof.** Read result.json, lane-8.json, missing-pack.stderr, and report-publication-failure.stderr with their recorded exit codes. Expected failures are successful assertions; the helper itself must exit 0. Confirm scratch_removed true and evidence remains.

## Gotchas

- Failure to write a report occurs after publication; exit 2 does not mean the old snapshot was retained.
- Existing readers keep their old view until reconnecting. Lane 8 deliberately compares with a fresh connection.
- Whole-file hashes need not match across successful imports because timestamps change.
- These public failure paths do not prove every crash/durability/lock branch. Existing lane 9's internal fault injection is supplemental and cannot replace a CLI journey.

# Verify repeat imports and recovery

Repeat an import safely, retain the old snapshot when input validation fails, and distinguish successful publication from failure to write its report.

## Check the expected behavior

- `replace-repeat`: repeat import preserves source IDs, content hashes, counts, and occurrence accounting.
- `replace-readers`: a pinned read transaction retains its revision during publication, and a later transaction sees the new one.
- `replace-failed-input`: invalid input exits 1 without replacing the previous snapshot.
- `replace-failed-report`: a report write failure exits 2 while the published snapshot remains usable.

## Exercise the public commands

Run `house-account ingest` again with the same database destination. Inspect exit status and JSON on stdout and stderr. End the current read transaction and start another to see a newly published revision. Reconnecting also works.

## Run the isolated checks

Complete the setup and doctor checks in [Verify House Account](../SKILL.md). The helper first creates the existing snapshot needed by these journeys.

1. Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py replacement`. Lane 8 repeats a real CLI import and verifies stable IDs, content hashes, and accounting. Another import holds a read transaction open to check the retained revision and verifies that the database inode stays unchanged. The helper then points the CLI at a missing pack, expects exit 1 with status failed, and compares full logical SQLite digests, including WAL-visible facts. Finally it supplies a directory for `--report`, expects exit 2 and published_report_failed, and reconnects to verify a new snapshot ID, integrity, and persisted job count. The before/after snapshot IDs are retained in result.json to prove publication occurred despite the report failure.
2. Read result.json, lane-8.json, missing-pack.stderr, and report-publication-failure.stderr with their recorded exit codes. Expected failures are successful assertions. The helper itself must exit 0. Confirm scratch_removed true and evidence remains.

## Check the limits

- Failure to write a report occurs after publication. Exit 2 does not mean the old snapshot was retained.
- A pinned read transaction retains its old view. Ending that transaction permits the next read to see the new revision. The helper proves both states.
- Main-file hashes cannot prove unchanged WAL database state. Use a fresh SQLite read transaction and a logical digest for a rejected action. Successful imports intentionally change snapshot IDs and timestamps.
- These public failure paths do not prove every crash, durability, or lock branch. Existing lane 9's internal fault injection is supplemental and cannot replace a CLI journey.

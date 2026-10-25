# Import and reporting

Import the supplied home-services pack into a private local SQLite snapshot and receive source accounting and input hashes.

## Sub-features

- `import-create`: an empty destination becomes a usable snapshot with mode 0600.
- `import-report`: stdout JSON and the optional saved report agree, apart from the report's file inventory.
- `import-reconcile`: import builds canonical projections with an isolated empty ledger and publishes schema version 2.
- `import-account`: six sources plus the street reference are accounted, including six valid empty pages.

## How to get to it (user POV)

Run `house-account ingest --data data --database <destination> --report <report-path> --ledger <decisions-path>` from the terminal. `--report` is optional; the CLI always emits summary JSON. Read the saved JSON or query the resulting database read-only.

## Driving it with verify.py

Preconditions: the Launch setup and doctor pass; the private supplied pack is present.

- **Import.** Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py import`. The helper creates an isolated snapshot via the public CLI with `--report`, checks exit 0, status success, report consistency, mode 0600, all ten stored source-table counts, reconciliation output, schema version 2, transactional publication, and integrity. Lane 1 separately exercises the CLI without `--report` and checks source accounting and empty pages.
- **Proof.** Read `result.json`, `ingest.stdout`, `ingest.stderr`, `import.json`, and `lane-1.json` at the printed evidence path. Require status pass, all exits 0, and scratch_removed true after teardown.

## Gotchas

- The pack is private and absent from a fresh clone; missing files are a failure, not a reason to replace fixtures.
- Lane 1 has fixed supplied-pack counts. Legitimate input updates require source review before adjusting expectations.
- Source-local entity counts are not reconciled real-world customer or provider counts.
- The default ledger is review/decisions.jsonl. The helper uses a scratch ledger so active decisions cannot change its expected results.
- Default destination is the working snapshot; always supply the helper's isolated destination.

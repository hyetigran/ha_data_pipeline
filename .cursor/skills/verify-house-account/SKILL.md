---
name: verify-house-account
description: Verify House Account P1 ingestion and P2 reconciliation, history queries, local review, and schema migration through real CLI commands with isolated state and retained evidence.
---

# Verify House Account

Use the [feature map](features/README.md) to select coverage. The application exposes `ingest`, four `query` commands, and `review export`, `validate`, and `apply`. Read-only SQLite inspection supplies a second view of persisted facts. P3 availability and P4 MCP serving remain unimplemented.

## Launch

Run from the repository root with Python 3.13 and uv installed:

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv sync --locked
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py doctor
```

The supplied private pack must exist under `data/`, with `README.md`, `sources/`, and `reference/`. It is ignored by Git and cannot be reconstructed from the checkout. Doctor checks the manifest and hashes the files. Missing pack access blocks the run. Do not fabricate passing substitutes.

Each feature command creates an empty temporary directory and uses it as the subprocess working directory. The real importer creates the schema, imports the pack, reconciles identities, and publishes the database. All direct imports supply an explicit scratch ledger. Existing P1 scripts inherit the scratch working directory, so their default review ledger is also isolated. Never use `var/house_account.sqlite` or the working `review/` directory for verification.

The migration journey additionally requires `artifacts/P2R/baseline/house_account.sqlite`. It copies that frozen legacy database into scratch through SQLite's backup API. Missing or already-upgraded baselines block that journey.

These are noninteractive CLI processes. No server, port, authentication, or PTY is required. Each process must exit before the next drive. Runs own unique database paths and can coexist, but the maintenance coordinator drives features serially. Do not run dependency synchronization concurrently.

## Doctor

Run the doctor command above before driving. It checks Python 3.13, confirms the CLI import resolves to this checkout, and validates the pack manifest. Expect `status: ready`, a module path in this checkout, and an input-file count. The original supplied pack contains 176 files.

The helper runs doctor before each direct CLI command and each delegated P1 lane. P1 lanes may internally issue multiple imports against the same isolated fixture. On any unexpected failure, doctor again before retrying, inspect the retained error, and start a fresh helper run. A healthy doctor does not prove that input contents satisfy the adapters. The real import must also succeed.

## Drive

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py import
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py inspect
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py replacement
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py history
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py review
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py migration
```

Each journey checks the real import report, stored source-table counts, reconciliation output, schema version 2, transactional publication, owner-only file permissions, and SQLite integrity and foreign keys.

The P1 journeys reuse `scripts/verify.py` lanes 1, 2 through 7, 8, and 10. Lane 9 uses internal fault injection and remains supplemental. The history journey drives all four public query commands and compares fixed pack answers. `scripts/verify_p2_independent.py` adds source-fact checks but does not replace CLI proof. The review journey edits only disposable human-decision fields and copied source data. The migration journey verifies the legacy backup can restore all original logical facts.

## Evidence

Each journey prints a unique directory under `artifacts/verification/<feature>-<random>/`. Keep that directory after cleanup. `result.json` records the feature, commands, exit codes, assertions, doctor output, aggregate counts, status, and scratch cleanup. Per-action stdout and stderr, the import report, and P1 lane reports remain beside it.

Exercise the public user path and verify both the action and persisted result. Read SQLite through an explicit read transaction for unchanged-state checks. A main-file hash can miss committed WAL contents. The helper's logical digest includes schema, data, and user_version. Use it for comparing the same database around rejected or preview actions, not for canonical equivalence across independently rebuilt databases.

Review validation and dry-run build candidates and create lock files. Verify that published logical state and ledger bytes remain unchanged, and candidate directories are removed. Do not infer zero writes from the name dry-run. The helper uses real local commands without mocks. Network behavior is not an asserted property of these checks.

Keep evidence local and ignored by Git. Do not upload raw customer rows, private database files, review documents, or ledgers. The helper removes those scratch files and retains command receipts and aggregate assertions. Fixed baseline counts require the supplied pack with no applied decisions. If input content changes, investigate failed prerequisites instead of weakening the journey.

## Cleanup

The helper waits for each child. After 180 seconds or interruption, it terminates only that child's process group, including nested imports. Every child receives a TMPDIR inside the run's scratch directory. Temporary databases, ledgers, copied packs, and candidate files are removed on completion or failure. Evidence stays outside scratch.

Require `scratch_removed: true` in result.json and check the evidence files still exist after exit. Never kill by process name. After an external hard kill, inspect the recorded scratch path and commands, confirm no run-owned process remains, and remove only that scratch directory. Dependency caches and the environment stay installed.

## Helpers

The executable `scripts/verify.py` in this skill accepts `doctor`, `import`, `inspect`, `replacement`, `history`, `review`, and `migration`. Invoke it through uv as shown above. It owns the disposable state and evidence. Existing repository scripts supply unchanged P1 lanes and independent P2 assertions.

Maintenance edits only this skill directory. Report product defects without changing application code or external verification scripts. Before a PR, confirm its base includes the product implementation exercised by the run. A local uncommitted P2 implementation cannot be represented as verified behavior on a P1-only remote base. Preserve proven skill changes locally and report the shipping blocker if the base is unavailable.

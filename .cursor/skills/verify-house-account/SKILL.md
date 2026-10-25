---
name: verify-house-account
description: Verify House Account P1 ingestion and P2 reconciliation, history queries, local review, schema migration, P3 availability and rankings, and P4 MCP tools through real CLI and protocol commands with isolated state and retained evidence.
---

# Verify House Account

Use the [feature map](features/README.md) to select coverage. The application exposes `ingest`, seven `query` commands, and `review export`, `validate`, and `apply`. Read-only SQLite inspection supplies a second view of persisted facts. P3 adds `query openings`, `query available`, and `query recommend`. P4 adds six bounded read-only MCP tools over local stdio.

## Prepare the environment

Run from the repository root with Python 3.13 and uv installed:

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv sync --locked
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py doctor
```

The supplied private pack must exist under `data/`, with `README.md`, `sources/`, and `reference/`. It is ignored by Git and cannot be reconstructed from the checkout. Doctor checks the manifest and hashes the files. Missing pack access blocks the run. Do not fabricate passing substitutes.

Each feature command creates an empty temporary directory and uses it as the subprocess working directory. The real importer creates the schema, imports the pack, reconciles identities, and publishes the database. All direct imports supply an explicit scratch ledger. Existing P1 scripts inherit the scratch working directory, so their default review ledger is also isolated. Never use `var/house_account.sqlite` or the working `review/` directory for verification.

The migration journey additionally requires `artifacts/P2R/baseline/house_account.sqlite`. It copies that frozen legacy database into scratch through SQLite's backup API. Missing or already-upgraded baselines block that journey.

These are noninteractive CLI processes. No server, port, authentication, or PTY is required. Wait for each process to exit before starting the next feature. Runs own unique database paths and can coexist, but the maintenance coordinator drives features serially. Do not run dependency synchronization concurrently.

## Check readiness

Run the doctor command above before driving. It checks Python 3.13, confirms the CLI import resolves to this checkout, and validates the pack manifest. Expect `status: ready`, a module path in this checkout, and an input-file count. The original supplied pack contains 176 files.

The helper runs doctor before each direct CLI command and each delegated P1 lane, P3 runner, or P4 protocol runner. Delegated runners may internally issue multiple imports against the same isolated fixture. After an unexpected failure, run doctor again. Inspect the retained error before starting a fresh helper run. A healthy doctor does not prove that input contents satisfy the adapters. The real import must also succeed.

## Run the feature checks

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py import
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py inspect
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py replacement
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py history
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py review
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py migration
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py availability
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py mcp
```

Each journey checks the real import report, stored source-table counts, reconciliation output, schema version 2, transactional publication, owner-only file permissions, and SQLite integrity and foreign keys.

The P1 journeys reuse `scripts/verify.py` lanes 1, 2 through 7, 8, and 10. Lane 9 uses internal fault injection and remains supplemental. The history journey drives all four public query commands and compares fixed pack answers. `scripts/verify_p2_independent.py` adds source-fact checks but does not replace CLI proof. The review journey edits only disposable human-decision fields and copied source data. The migration journey verifies the legacy backup can restore all original logical facts. The availability journey archives P2R commit `c6c151ee3e95706ad178d2d661fc791f6106f616` from local Git history and runs all ten P3 lanes through the skill-owned availability wrapper under the same timeout and cleanup boundary. The wrapper retains the original verdict and separately verifies P4's additive block labels and services against stored facts while requiring unchanged baseline row facts and occupied-time exclusion. Missing baseline history blocks that journey. The MCP journey starts the real stdio server. It checks all six tools against direct queries, safe errors, source and database invariants, and shutdown.

## Inspect the evidence

Each journey prints a unique directory under `artifacts/verification/<feature>-<random>/`. Keep that directory after cleanup. `result.json` records the feature, commands, exit codes, assertions, doctor output, aggregate counts, status, and scratch cleanup. Per-action stdout and stderr, the import report, and P1 lane reports remain beside it. Availability retains original lane receipts and `live-summary.json` under `p3/legacy/`. Its separate `p3/maintained-summary.json` and lane-1 receipts record the current compatibility check without rewriting historical verdicts.

Exercise the public user path and verify both the action and persisted result. Read SQLite through an explicit read transaction for unchanged-state checks. A main-file hash can miss committed WAL contents. The helper's logical digest includes schema, data, and user_version. Use it for comparing the same database around rejected or preview actions, not for canonical equivalence across independently rebuilt databases.

Review validation and dry-run build candidates and create lock files. Verify that published logical state and ledger bytes remain unchanged, and candidate directories are removed. Do not infer zero writes from the name dry-run. The helper uses real local commands without mocks. Network behavior is not an asserted property of these checks.

Keep evidence local and ignored by Git. Do not upload raw customer rows, private database files, review documents, or ledgers. The helper removes those scratch files and retains command receipts and aggregate assertions. Fixed baseline counts require the supplied pack with no applied decisions. If input content changes, investigate failed prerequisites instead of weakening the journey.

## Confirm cleanup

The helper waits for each child. After 180 seconds or interruption, it terminates only that child's process group, including nested imports. Every child receives a TMPDIR inside the run's scratch directory. Temporary databases, ledgers, copied packs, and candidate files are removed on completion or failure. Evidence stays outside scratch.

Require `scratch_removed: true` in result.json and check the evidence files still exist after exit. Never kill by process name. After an external hard kill, inspect the recorded scratch path and commands, confirm no run-owned process remains, and remove only that scratch directory. Dependency caches and the environment stay installed.

## Maintain the verification instructions

The executable `scripts/verify.py` in this skill accepts `doctor`, `import`, `inspect`, `replacement`, `history`, `review`, `migration`, `availability`, and `mcp`. Invoke it through uv as shown above. It owns the disposable state and evidence. Existing repository scripts supply unchanged P1 lanes and independent P2 assertions.

The executable `scripts/verify_availability.py` is invoked by `verify.py availability`. Direct use requires `--database <disposable snapshot> --data <pack> --parent <archived P2R checkout> --output <new evidence directory>`. Use the public helper for its doctor, 180-second process-group timeout, and cleanup boundary. The wrapper copies the database and retains original failures separately from maintained checks.

Verification-skill maintenance edits only this skill directory. Report product defects without changing application code or external verification scripts. Before a PR, confirm its base includes the product implementation exercised by the run. A local uncommitted P2 implementation cannot be represented as verified behavior on a P1-only remote base. Preserve proven skill changes locally and report the shipping blocker if the base is unavailable.

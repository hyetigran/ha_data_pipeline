---
name: verify-house-account
description: Verify House Account's P1 import CLI and private SQLite snapshots using real subprocesses, stored-state checks, and durable evidence; use after import changes or during verification maintenance.
---

# Verify House Account

The primary surface is the noninteractive `house-account ingest` CLI. The secondary surface is read-only SQLite inspection. P2 reconciliation, approval, availability, and MCP tools are planned, not live surfaces. Read [the feature map](features/README.md) before choosing coverage.

## Launch

Run from the repository root with Python 3.13 and uv installed:

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv sync --locked
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py doctor
```

The supplied private pack must already exist under `data/`, with `README.md`, `sources/`, and `reference/`. It is gitignored and cannot be reconstructed from this checkout. Doctor prints `status: ready`, the checkout's module path, Python version, and input file count (176 at creation). It validates the expected file manifest, not fixed contents. Missing/private pack access is a blocker; never fabricate a passing substitute. No credentials, network services, server ports, or migrations are required. Every drive creates an empty temporary directory and the real importer creates the SQLite schema and imports seed content from the supplied pack.

Use fresh noninteractive subprocesses as the existing `scripts/verify.py` harness does; a PTY adds no interaction to this JSON-only CLI. Each helper run owns a unique database path, so runs can coexist. Never use `var/house_account.sqlite` for verification, modify the pack, or run dependency synchronization concurrently. Processes exit after each command; teardown is automatic in the helper's `finally`/temporary-directory scope.

## Doctor

The read-only command above checks Python 3.13, verifies the imported CLI belongs to this checkout, and inventories/hashes the pack. The helper runs it before every CLI drive. On any surprise, run doctor again before proceeding. A healthy doctor does not establish that changed input contents satisfy the adapters: the real import must also succeed. For a failed drive, inspect its evidence, fix harness drift only if appropriate, and start a fresh helper run. Never reuse a failed scratch database.

## Drive

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py import
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py inspect
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py replacement
```

These are independent complete journeys. Each begins with the public `python -m house_account.cli ingest --data <repo>/data --database <scratch>/snapshot.sqlite --report <evidence>/import.json`, checks report/stdout consistency, owner-only permissions, SQLite integrity/foreign keys, and persisted counts. They then reuse real CLI lanes from `scripts/verify.py`: import uses 1; inspect uses 2–7 and 10; replacement uses 8 plus public CLI failures. The existing lane 9 uses an internal fault-injection function; it is supplemental testing only, not proof of a user journey. Public failures use a missing input directory (exit 1) and a directory as report destination (exit 2).

## Evidence

Each drive prints its unique absolute evidence directory under `artifacts/verification/<feature>-<random>/`. `result.json` includes actions, exact commands, exit codes, doctor output, persisted aggregate counts, status, and cleanup result. Per-action stdout/stderr, the import report, and lane JSON files remain there. Read them after each drive; a missing lane result or nonzero helper exit is not a pass. Capture the action and its result, and verify persisted side effects through read-only SQLite queries. No mocks, internal setters, or test-only endpoints substitute for the real user path. There is no dry-run mode; these commands really write isolated snapshots. If adding such a mode, verify its file/network/ref effects instead of trusting its name.

Keep all evidence local and gitignored: do not copy raw customer rows or private databases into PRs. Reports contain aggregate counts and hashes; retain those rather than payloads. Proof of one mapped feature does not imply coverage of the other features or every possible failure branch. Additional changed user paths require additional captured actions.

## Cleanup

The helper waits for each child, times it out after 180 seconds if needed, and removes its own temporary directory on normal completion, exceptions, and keyboard interruption. It never starts a background service. `result.json` must show `scratch_removed: true`; explicitly check that the printed evidence path and files still exist after exit. Never delete evidence during cleanup or kill by process name. After an external hard kill, inspect the recorded `scratch` path and recorded commands, confirm no run-owned process is active, then remove only that scratch directory. Shared dependency caches and the installed environment are retained; they are not app instances.

## Helpers

The executable `scripts/verify.py` within this skill supports `doctor`, `import`, `inspect`, and `replacement`, invoked above through uv's Python environment. The repository's `scripts/verify.py` supplies existing assertion lanes. Keep product code and that external harness out of maintenance edits: this skill's directory is the maintenance scope. No source changes or public publishing are needed to run verification. Maintenance may ship one PR of proven skill corrections once this repository has an initial commit and configured remote; otherwise report the shipping blocker without claiming a PR exists.

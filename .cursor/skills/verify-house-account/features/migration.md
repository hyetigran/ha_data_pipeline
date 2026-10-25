# Migrate and restore a legacy snapshot

Import into a legacy P2 database to publish schema version 2 while retaining a restorable backup of the original facts.

## Sub-features

- `migration-publish` upgrades an existing legacy snapshot in place through the public ingest command.
- `migration-backup` preserves the original database as a private .pre-v2.bak file.
- `migration-restore` restores that backup with SQLite's backup API and verifies all original logical contents.

## How to get to it (user POV)

Run `house-account ingest --data <pack> --database <legacy-snapshot> --ledger <ledger> --report <report>`.
For recovery, stop writers and use the SQLite backup API to restore the generated .pre-v2.bak into a separate destination. Inspect the restored database before replacing any working file.

## Driving it with verify.py

Preconditions: Launch and doctor pass. The private frozen legacy database must exist at `artifacts/P2R/baseline/house_account.sqlite`. A schema-v2 file cannot substitute for this prerequisite.

- Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py migration`.
- The helper backs up the frozen database into scratch. It checks the legacy schema, then imports through the public CLI with an empty scratch ledger.
- Require the same destination inode, schema version 2, transaction publication, integrity, and foreign keys. Restore the generated backup into another scratch database through SQLite and compare its full logical digest with the pre-import copy.
- Read `result.json`, `import.json`, and ingest stdout/stderr. Require pass and `scratch_removed: true`. Private database copies do not survive cleanup.

## Gotchas

- Missing frozen baseline blocks this journey. Report the attempted command and prerequisite instead of treating a fresh schema-v2 import as migration proof.
- SQLite WAL contents can hold committed changes. Do not copy only the main file or compare its bytes as proof of logical state.
- Restoration proves original schema and data are preserved. It does not exercise the historical application binary or operator cutover of an active database.

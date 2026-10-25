# Upgrade and restore a legacy database

## Upgrade to schema version 2

1. Stop other maintenance writers.
2. Preserve the source pack and the authoritative review ledger.
3. Run `ingest` with the intended database and ledger paths.

```sh
uv run --locked house-account ingest --data data --database var/house_account.sqlite --ledger review/decisions.jsonl
```

4. Confirm that the report identifies schema version `2` and transactional publication.
5. Retain `<database>.pre-v2.bak` until you have reviewed the migration.
6. Query the affected histories before adopting the new snapshot.

A recognized legacy database receives a SQLite backup before publication. Unknown schema versions and incompatible DDL cause a refusal. If a matching backup already exists, a retry can reuse it. The importer does not overwrite an unrelated backup.

## Restore a backup

1. Stop writers and close connections to the destination.
2. Use SQLite's backup API to restore the backup into a separate database path.
3. Check database integrity and foreign keys.
4. Compare the restored facts with the recorded pre-migration snapshot.
5. Point the appropriate query code at the restored path only after those checks pass.

Do not copy only the main file from a live WAL database. Committed state can remain in the WAL. The frozen P2 code in `artifacts/P2R/baseline/code/` reads the legacy backup. Current queries require schema version `2`.

## Recover recorded review decisions

If apply reports `recorded_not_applied`, rerun ingestion with the same ledger. Keep the ledger intact.

```sh
uv run --locked house-account ingest --data data --database var/house_account.sqlite --ledger review/decisions.jsonl
```

Export the proposals again if the rule version or source evidence changed. Revalidate old approvals against current evidence before applying them.

## Verify migration behavior

Run the maintained migration journey against the frozen private legacy baseline.

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py migration
```

Require a passing result and confirmed scratch cleanup. Inspect the backup-restoration assertion in the retained receipt.

For intended answer changes, identity behavior, and measured results, see the [P2R execution record](p2r-execution.md). The [data model](data-model.md) explains the current schema.

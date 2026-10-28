# Upgrade an old database

This guide is for an old database, not a fresh setup. A fresh setup creates the current format.

1. Stop other imports and review updates.
2. Keep the source pack and the review decision log.
3. Run the import with the intended database and ledger paths. For the regular database:

```sh
uv run --locked house-account ingest --data data --database var/house_account.sqlite --ledger review/decisions.jsonl
```

4. Check that the report says schema version `2`.
5. Keep the backup ending in `.pre-v2.bak` until you have checked the new answers.
6. Query known homes and providers to check the result.

The importer refuses database formats it does not recognize. It does not overwrite an unrelated backup.

## Restore after a problem

Stop writers and close database connections first. Use SQLite's backup API to restore into a separate file. Check the restored database before using it.

Do not copy only the main file while the database is live. Recent changes can be in a second file beside it.

Old database backups need the matching old query code. Current queries expect version `2`.

If a review decision was recorded but not applied, rerun the import with the same decision log. Do not delete that log to fix the problem.

---

[Start here](README.md) · [Original document](../p2r-migration.md)

# Refresh an existing snapshot

Use this guide after a normalization or other code change, so that an existing snapshot reflects the current code. The importer rebuilds the snapshot from the same pack. It keeps existing canonical IDs and replays the decision ledger.

A refresh within schema version `2` creates no automatic backup. Only a [legacy migration](p2r-migration.md) does. Take the backup yourself before you publish.

## Find the target paths

Refresh the database that your MCP client reads, and use that database's own ledger.

| Setup | Database | Ledger |
| --- | --- | --- |
| Regular | `var/house_account.sqlite` | `review/decisions.jsonl` |
| UAT (`--uat`) | `var/uat/run-*/house_account.sqlite` | `decisions.jsonl` in the same `run-*` folder |

To confirm the paths, read `--database` and `--ledger` from the client's `house_account` entry. Setup also writes them to `mcp-config.json`, beside its import report.

`ingest` defaults `--ledger` to `review/decisions.jsonl`. When you refresh a UAT snapshot without `--ledger`, the importer applies the regular ledger's decisions. Always pass both paths.

```sh
DB=var/uat/run-XXXXXX/house_account.sqlite
LEDGER=var/uat/run-XXXXXX/decisions.jsonl
```

A missing ledger file is a valid empty history. Do not substitute another ledger.

## Back up the database

1. Stop other maintenance writers, such as `ingest` and `review apply`. MCP readers can keep running.
2. Create the backup with SQLite's online backup. It includes committed WAL content.

```sh
mkdir -p artifacts/refresh
sqlite3 "$DB" ".backup 'artifacts/refresh/before.sqlite'"
sqlite3 artifacts/refresh/before.sqlite "PRAGMA integrity_check"
```

3. Expect `ok`. Do not back up by copying only the main `.sqlite` file.
4. If the ledger file exists, copy it beside the backup.

The backup contains private source payloads. Keep it under `artifacts/`, which Git ignores.

## Rehearse in isolation (recommended)

For a change that alters answers, build and check a separate candidate first. The CLI has no identity-source flag. Use the Python `ingest` API with `identity_source` set to the backup, and use a copy of the ledger:

```sh
uv run --locked python -c "from pathlib import Path; from house_account.cli import ingest; ingest(Path('data'), Path('artifacts/refresh/candidate.sqlite'), ledger=Path('artifacts/refresh/decisions.jsonl'), identity_source=Path('artifacts/refresh/before.sqlite'))"
```

Run the MCP verification against the candidate, as described in [Verify the result](#verify-the-result). Do not copy the candidate over the live file. To publish, use the supported path below.

## Publish the refresh

```sh
uv run --locked house-account ingest --data data --database "$DB" --ledger "$LEDGER" --report artifacts/refresh/import.json
```

The importer takes the database lock and seeds identities from the target. It replays the ledger and publishes all tables in one transaction. The [command reference](command-reference.md#startup-and-storage) explains exit codes `0`, `1`, and `2`. Exit code `1` leaves the previous snapshot in place.

## Verify the result

```sh
uv run --locked python scripts/verify_p4.py --database "$DB" --output artifacts/refresh/mcp-verify
```

The script copies the snapshot into scratch space and calls all six tools through a real MCP server. Expect `"status": "pass"` and `"scratch_removed": true`.

Also check that the source manifest hash in the import report is unchanged. A changed hash means the pack changed, not only the code.

## Restart MCP clients

A running server reads the new revision on its next call. It keeps the Python code it loaded at startup. After a code change, restart the client, for example by opening a new Codex session.

## Roll back

Stop writers, and stop the MCP clients that use the database. Then restore `artifacts/refresh/before.sqlite` by following [Restore a backup](p2r-migration.md#restore-a-backup). Keep the ledger intact. If someone recorded decisions after the refresh, reconcile them before you roll back.

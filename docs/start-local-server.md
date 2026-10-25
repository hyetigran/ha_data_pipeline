# Start House Account and connect Codex

## Prepare the checkout

1. Install Python 3.13 and `uv`.
2. Place the private supplied pack in `data/`.
3. Confirm that `data/README.md`, `data/sources/`, and `data/reference/` exist.
4. From the repository root, install the locked dependencies.

```sh
uv sync --locked
```

## Import the snapshot

Run the importer before connecting Codex to avoid a client timeout during the first import.

```sh
uv run --locked house-account ingest --data data --database var/house_account.sqlite --report artifacts/import.json
```

Expect a JSON report and exit code `0`. The database contains private source payloads. Keep it local.

If the command exits with code `1`, inspect stderr before retrying. The previous published snapshot remains available. If it exits with code `2`, check for `published_report_failed`. That result means publication succeeded but the report write failed.

## Start the stdio server

Run the server from the repository root.

```sh
uv run --locked house-account --data ./data --as-of 2026-11-02
```

Expect the process to wait for an MCP client. Protocol messages use stdin and stdout. Diagnostics use stderr.

If the database is missing, startup imports it before serving. To refresh an existing snapshot, run `ingest` explicitly. To select other paths, pass `--database` and `--ledger` to startup.

## Register the server with Codex

1. Install Codex CLI.
2. Authenticate with `codex login`.
3. In the command below, replace `/absolute/path/house_account` with the checkout's absolute path.
4. Run the registration command. This command changes your Codex MCP configuration.

```sh
codex mcp add house_account -- /absolute/path/house_account/.venv/bin/python -m house_account.cli --data /absolute/path/house_account/data --database /absolute/path/house_account/var/house_account.sqlite --ledger /absolute/path/house_account/review/decisions.jsonl --as-of 2026-11-02
```

5. Start a new Codex session.
6. Ask a question from the [demo question set](../evals/questions.json).
7. Confirm that Codex calls the relevant `house_account` tool before answering.

For direct TOML configuration, use the equivalent entry below. Set the paths to your checkout.

```toml
[mcp_servers.house_account]
command = "/absolute/path/house_account/.venv/bin/python"
args = ["-m", "house_account.cli", "--data", "/absolute/path/house_account/data", "--database", "/absolute/path/house_account/var/house_account.sqlite", "--ledger", "/absolute/path/house_account/review/decisions.jsonl", "--as-of", "2026-11-02"]
startup_timeout_sec = 120
```

If initialization fails, verify the paths and run the importer separately. For tool options and limits, see the [command reference](command-reference.md).

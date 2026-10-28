# Set up House Account and connect an MCP client

## One-command setup

Supported environments: macOS and Linux, including WSL2 on Windows. Prerequisites are Git to clone, a POSIX shell, `curl`, internet access, and the separately supplied data pack. Installing Claude Code also requires Bash. No Python, Node.js, Homebrew, `uv`, or agent CLI installation is required beforehand. Agent authentication happens when opening the client.

```sh
git clone https://github.com/hyetigran/ha_data_pipeline.git
cd ha_data_pipeline
```

Place the supplied pack in `data/`, then run one of:

```sh
sh setup.sh --client codex
sh setup.sh --client claude
sh setup.sh --client none
```

`--client none` is the default when the option is omitted. This changes the earlier setup behavior, which always configured Codex. To continue the Codex UAT, use `sh setup.sh --client codex --uat` explicitly.

Every mode installs missing `uv`, provisions Python 3.13 and locked dependencies, and imports the data before producing MCP configuration. Only the selected agent client is installed if missing. A dependency or import failure stops before client registration. A later configuration failure leaves the database available; fix the reported issue and rerun.

| Client | Configuration and next step |
| --- | --- |
| `codex` | Adds or updates the user-level `house_account` registration using Codex CLI. Open a new Codex session. |
| `claude` | Atomically merges `house_account` into the checkout's `.mcp.json`, preserving unrelated servers and settings. Open Claude Code in this checkout and approve the project server. |
| `none` | Does not install or invoke an agent client, or alter existing client settings. Prints the executable, argument array, and shell-quoted launch command for any local stdio MCP client. |

Every mode writes a `mcp-config.json` containing an `mcpServers.house_account` entry beside its import report. Its absolute paths point to this checkout and selected snapshot. Use the `command` and `args` in clients with different configuration formats. The generated config and `.mcp.json` contain machine-local paths and are excluded from Git. Moving the checkout requires rerunning setup.

Claude's project configuration is intentionally scoped to this checkout. It does not alter user-level Claude registrations. A higher-precedence local Claude entry with the same name may shadow it; inspect `/mcp` if Claude loads a different snapshot. Malformed existing `.mcp.json` is left unchanged and reported as a failure. Rerunning safely updates the same project entry. Selecting another client does not remove previous registrations, and `none` is not an uninstall operation.

The private pack is not downloaded or committed. To use an extracted pack elsewhere, append `--data "/actual/path/to/pack"`. Relative paths resolve from the directory where setup is invoked. Missing pack files stop setup before installation.

Missing tools normally install under `~/.local/bin`. Client installers may update shell configuration. Existing tools on PATH are reused. Installer and configuration references: [uv](https://docs.astral.sh/uv/reference/installer/), [Codex](https://github.com/openai/codex#installing-and-running-codex-cli), [Claude installation](https://code.claude.com/docs/en/setup), and [Claude project MCP configuration](https://code.claude.com/docs/en/mcp#project-scope).

Expect `Setup complete.`, the database path, and paths to the import report and exported MCP configuration. The script exits without a resident server. The client starts the server through stdin/stdout. Use November 2, 2026 as the dataset's reference date.

For fresh UAT:

```sh
sh setup.sh --client codex --uat
```

Replace `codex` with `claude` or `none` as needed. Each run creates a new snapshot and empty review-ledger path under `var/uat/run-*`. No existing snapshot is deleted. Rerun with the same client without `--uat` to switch back to the regular database.

The commands below describe individual operations for troubleshooting. They are not required after successful setup.

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

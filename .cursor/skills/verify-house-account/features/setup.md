# Verify local setup and configuration export

Verify `setup.sh` from outside the checkout, including a checkout path with spaces. Keep all generated state in a disposable copy.

## Run the isolated check

Complete the dependency setup and doctor checks in [Verify House Account](../SKILL.md). The run needs installed `uv`, Python 3.13, and cached locked dependencies, including build dependencies. It uses offline mode and does not download installers.

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify_setup.py
```

The helper copies the current source and setup files into scratch. It invokes the real `setup.sh --client none --data <supplied pack>` from outside that copy. It then runs `--uat` twice.

Require these results:

- A missing pack fails before the environment or application state is created.
- Normal setup installs locked dependencies, imports a private schema-v2 snapshot, and exports `mcp-config.json`.
- Exported executable, data, database, ledger, and reference-date arguments point to the intended paths.
- Each UAT run creates a different snapshot. Both leave the normal snapshot's logical contents unchanged.
- Source files remain unchanged, and no project `.mcp.json` is created for `--client none`.

Read `result.json`, command captures, and exported configuration receipts in the printed `artifacts/verification/setup-*` directory. Require `status: pass` and `scratch_removed: true`. Check that the recorded scratch path is absent and receipts remain present.

## Interpret coverage and failures

Missing cached dependencies block this offline journey. Inspect the setup stderr before retrying. Run doctor again after an unexpected failure. The helper terminates only its child process group after 180 seconds and removes scratch on failure as well as success.

This journey covers import and portable configuration export. It does not install Codex or Claude, change their registrations, authenticate a client, or prove their interactive behavior. Those operations require the chosen client and its configuration access. The [MCP journey](mcp.md) separately checks the real server protocol.

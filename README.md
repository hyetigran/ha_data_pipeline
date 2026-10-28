# House Account documentation

House Account answers home-service history and scheduling questions from a private local data pack. It imports six sources and a street reference into SQLite. Six read-only MCP tools expose the published facts to an agent.

P1, P2, P2R, P3, and P4 are implemented. [PR #4](https://github.com/hyetigran/ha_data_pipeline/pull/4) merged P4 as `ea66e76`. Production synchronization, remote access control, travel estimates, and worker-level scheduling remain outside this release.

## One-command setup

On macOS or Linux (Windows: WSL2), clone the repository:

```sh
git clone https://github.com/hyetigran/ha_data_pipeline.git
cd ha_data_pipeline
```

Place the separately supplied pack in `data/`, then choose your client:

```sh
sh setup.sh --client codex
sh setup.sh --client claude
sh setup.sh --client none
```

Run one of those commands. All modes install Python 3.13 and locked application dependencies and import the data. Setup installs missing `uv` and only the selected agent client through official installers. Git, a POSIX shell, `curl`, and internet access are prerequisites; the Claude installer also requires Bash. No preinstalled Python, Node.js, or Homebrew is required.

- `codex` adds or updates the user-level `house_account` registration. Open a new Codex session afterward.
- `claude` adds or updates only `house_account` in the checkout's `.mcp.json`, preserving other servers. Open Claude Code in that checkout and approve the project MCP server.
- `none` is the default. It installs no agent client, changes no client configuration, and prints the executable, arguments, and equivalent launch command. Import the exported `mcp-config.json` into another client that supports local stdio MCP. Client-specific configuration formats may differ.

Sign in to the selected client if prompted. Every mode prints the path to its generated `mcp-config.json`. The setup command exits; the client launches the server when connecting. Switching clients leaves previous client registrations intact.

If the pack is elsewhere, append `--data "/path/to/supplied-pack"` using its actual path. The pack is excluded from GitHub; cloning alone cannot supply it. No machine-specific paths are hardcoded in setup.

For fresh UAT, run `sh setup.sh --client codex --uat` or select `claude` or `none`. Each run creates a new directory under `var/uat/`. Existing databases and review decisions remain intact. Rerun with the same client without `--uat` to select the regular snapshot.

## Task guides

The guides cover local operation and verification.

- [Set up House Account and connect an MCP client](docs/start-local-server.md).
- [Query service history and candidate openings](docs/query-local-data.md).
- [Review reconciliation proposals](docs/review-reconciliation.md).
- [Upgrade and restore a legacy database](docs/p2r-migration.md).
- [Verify the application and capture a Codex demo](docs/verify-local-system.md).
- [Enable the staged-file token limit](docs/commit-hooks.md).

## Reference

The reference pages define terms, commands, requirements, and observed results.

- [CLI and MCP reference](docs/command-reference.md).
- [Domain glossary](CONTEXT.md).
- [Documentation index](docs/README.md).
- [Challenge requirements](gauntlet-challenge-requirements.md).
- [Feature verification map](.cursor/skills/verify-house-account/features/README.md).
- [Source inspection](docs/data-pack-inspection.md) and [trap register](docs/trap-register.md).
- [Delivery status and acceptance requirements](docs/project-plan.md).

## Design explanations

The design pages explain the model and its limits.

- [Architecture](ARCHITECTURE.md) and [data model](docs/data-model.md).
- [Availability and recommendation policy](docs/p3-design.md).
- [Design decisions](docs/decisions.md) and [schema redesign](docs/schema-redesign.md).
- [Production synchronization requirements](docs/sync-readiness.md).
- [AI assistance and human review](docs/ai-use.md).

## Data boundary

The supplied pack, SQLite databases, review files, and captured answers contain private evidence. Git excludes `data/`, `var/`, `review/`, and `artifacts/`. The source pack is required for full verification and is not part of this repository.

MCP responses omit homeowner contacts, private notes, and personal calendar titles. Exact-home history remains available to a caller with local tool access. The application does not authenticate property ownership. Candidate openings use conservative provider capacity and exclude travel time from the calculation.

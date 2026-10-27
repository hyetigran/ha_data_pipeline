# House Account documentation

House Account answers home-service history and scheduling questions from a private local data pack. It imports six sources and a street reference into SQLite. Six read-only MCP tools expose the published facts to an agent.

P1, P2, P2R, P3, and P4 are implemented. [PR #4](https://github.com/hyetigran/ha_data_pipeline/pull/4) merged P4 as `ea66e76`. Production synchronization, remote access control, travel estimates, and worker-level scheduling remain outside this release.

## One-command setup

On macOS or Linux (Windows: WSL2), clone the repository:

```sh
git clone https://github.com/hyetigran/ha_data_pipeline.git
cd ha_data_pipeline
```

Place the separately supplied pack in `data/`, then run:

```sh
sh setup.sh
```

This installs missing `uv` and Codex CLI tools using their official installers, installs Python 3.13 and locked dependencies, imports the pack, and adds or updates the `house_account` Codex MCP registration using absolute paths. Git, a POSIX shell, `curl`, and internet access are prerequisites. No preinstalled Python, Node.js, or Homebrew is required. Open a new Codex session afterward and sign in if prompted. The setup command finishes without leaving a server running; Codex launches it when connecting.

If the pack is elsewhere, use `sh setup.sh --data "/path/to/supplied-pack"`. The pack is excluded from GitHub; cloning alone cannot supply it. Paths are resolved from the checkout and your arguments, with no machine-specific paths in the setup script.

For a fresh UAT snapshot and empty review ledger, run `sh setup.sh --uat`. Each UAT run creates a new directory under `var/uat/` and updates the same MCP registration. Existing databases and review decisions remain intact. Run normal setup again to point Codex back at the regular snapshot.

## Task guides

The guides cover local operation and verification.

- [Start House Account and connect Codex](docs/start-local-server.md).
- [Query service history and candidate openings](docs/query-local-data.md).
- [Review reconciliation proposals](docs/review-reconciliation.md).
- [Upgrade and restore a legacy database](docs/p2r-migration.md).
- [Verify the application and capture a Codex demo](docs/verify-local-system.md).

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

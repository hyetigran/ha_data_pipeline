# House Account: agent guide

House Account imports a private home-service data pack into SQLite and serves six read-only MCP tools. Start with the [README](README.md) and the [documentation index](docs/README.md).

## Knowledge

| Need | Read |
| --- | --- |
| Domain terms | [CONTEXT.md](CONTEXT.md) |
| System boundaries and privacy | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Tables and their meaning | [Data model](docs/data-model.md) |
| Decisions | [Decision log](docs/decisions.md) and [ADRs](docs/adr/) |
| Known data issues | [Trap register](docs/trap-register.md) and [October 27 investigation](docs/trap-discovery-2026-10-27.md) |
| Commands and flags | [Command reference](docs/command-reference.md) |
| Refresh a live snapshot | [Refresh an existing snapshot](docs/refresh-snapshot.md) |

Source pages: draft per-source dictionaries and ODCS contracts exist only locally, under `artifacts/metadata/` and `artifacts/contracts/`. They are unapproved drafts and contain private evidence.

Incident log: none yet. The `incident` skill creates `docs/incidents.md` with its first approved entry.

## Private data

`data/`, `var/`, `review/`, and `artifacts/` hold private evidence and are Git-ignored. Never commit their contents. Never copy homeowner contacts, notes, or calendar titles into tracked files. The configured MCP snapshot can be a UAT database under `var/uat/run-*/`, with its own ledger in the same folder.

## Standards

- Python 3.13, managed with `uv` and the locked dependencies.
- Ruff runs with its default rules. Mypy adds `check_untyped_defs` and `ignore_missing_imports`, set in [pyproject.toml](pyproject.toml).
- The [pre-commit hook](docs/commit-hooks.md) rejects maintained text files over 20,000 bytes. Enable it with `git config --local core.hooksPath .githooks`.
- Docs use short plain sentences, and link facts instead of repeating them.
- Naming and layering rules: unknown. No written standard exists beyond the code itself.

Run before a change goes in:

```sh
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked pytest
```

The [verification guide](docs/verify-local-system.md) lists the longer feature journeys.

## Skills

- `.agents/skills/`: 16 data engineering workflows adapted for Codex, including `profile`, `metadata`, `contract`, `quality`, `reconcile`, `impact`, `incident`, `docs`, and `knowledge-refresh`.
- `.cursor/skills/verify-house-account/`: live verification journeys for each feature.
- `.claude/skills/verify-availability-openings/`: bounded exhaustive check that openings never cover busy or unknown time. Run it after any change to `union`, `subtract`, or `openings`.

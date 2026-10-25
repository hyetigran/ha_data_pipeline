# Documentation index

The project implements P1 through P4. The [delivery status](project-plan.md) lists scope, acceptance requirements, and phase evidence. The [repository README](../README.md) is the entry point.

## How-to guides

| Task | Guide |
| --- | --- |
| Prepare the local database and connect Codex | [Start the local server](start-local-server.md) |
| Query completed work and candidate openings | [Query local data](query-local-data.md) |
| Review proposed identity or field corrections | [Review reconciliation decisions](review-reconciliation.md) |
| Upgrade or restore a legacy database | [Migrate the local database](p2r-migration.md) |
| Reproduce live checks and the demo | [Verify the local system](verify-local-system.md) |

## Reference

| Subject | Document |
| --- | --- |
| Commands, flags, response boundaries, and errors | [Command reference](command-reference.md) |
| Domain terms | [Home service glossary](../CONTEXT.md) |
| Original challenge requirements | [Challenge brief](../gauntlet-challenge-requirements.md) |
| Measured source formats and counts | [Data pack inspection](data-pack-inspection.md) |
| Accepted interview column contract | [Canonical column design](schema-columns-draft.md) |
| Historical normalization audit | [Data trap register](trap-register.md) |
| Live verification coverage | [Feature map](../.cursor/skills/verify-house-account/features/README.md) |

## Explanations

| Subject | Document |
| --- | --- |
| System boundaries and privacy | [Architecture](../ARCHITECTURE.md) |
| Canonical entities and completion evidence | [Data model](data-model.md) |
| Relational design and decision records | [Schema redesign](schema-redesign.md) |
| Availability, uncertainty, and ranking formulas | [Availability policy](p3-design.md) |
| Project choices and trade-offs | [Decision log](decisions.md) |
| Deferred production delivery semantics | [Synchronization readiness](sync-readiness.md) |
| Inferred corrections and their evidence | [Wrong-year and transposed-number evidence](trap-investigation.md) |
| AI contributions and the observed weak answer | [AI use](ai-use.md) |

## Execution records

These reports describe historical runs. Their counts and measurements belong to the recorded phase, not every later checkout. Local evidence paths require the original private artifacts.

- [P1 ingestion](p1-execution.md)
- [P2 reconciliation and history](p2-execution.md)
- [P2R relational migration](p2r-execution.md)
- [P3 availability and ranking](p3-execution.md)
- [P4 MCP tools and Codex demo](p4-execution.md)

Machine-generated inventories, audit summaries, captured transcripts, and verification receipts retain their original contents. `plan-validation.txt` records an earlier checklist count. It does not validate the current delivery plan.

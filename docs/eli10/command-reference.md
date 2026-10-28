# What the commands and tools mean

## Setup choices

| Option | Meaning |
| --- | --- |
| `--client codex` | Prepare data and register the server with Codex. |
| `--client claude` | Prepare data and write the project's Claude MCP entry. |
| `--client none` | Prepare data and print settings. This is the setup default. |
| `--uat` | Use a new test database and review-ledger path. |
| `--data` | Use the supplied files at a chosen path. |

## Application commands

`ingest` reads the files and builds the saved facts.

`query` reads saved facts. It can read home history, nearby history, block schedules, provider details, openings, or recommendations.

`review export` writes proposed corrections for a person to inspect. `review validate` checks the decisions. `review apply --dry-run` previews them. `review apply` applies them.

Running `house-account` without a command starts the MCP server. The server waits for a client. That wait is normal.

## The six MCP tools

| Tool | Question it answers |
| --- | --- |
| `search_service_history` | What completed work happened nearby? |
| `find_available_providers` | Who has relevant history and enough free time? |
| `get_block_schedule` | What visits are planned on this block? |
| `get_provider_profile` | What do we know about this business? |
| `get_property_history` | What work happened at this home? |
| `recommend_provider` | Who fits this service request, and why? |

These tools cannot book work or change source records.

## Dates and limits

The default nearby-history window is November 2, 2024 through the start of November 2, 2026. The radius is half a mile.

The default three-day window starts November 2 and stops before November 5, 2026. The two-week window stops before November 16. The demo week stops before November 9.

Dallas local time is used. A window includes its start and excludes its end. Availability requests cannot span more than 31 days.

Answers say if a result list was cut short. A short list does not always mean there were no more records.

## Import exit codes

| Code | Meaning |
| --- | --- |
| `0` | The import and requested report succeeded. |
| `1` | The import failed. The previous good database remains available. |
| `2` | The database was saved, but the report could not be written. |

`recorded_not_applied` means a review decision was saved in the decision log but not yet published to the database. Recovery uses that same log.

---

[Start here](README.md) · [Original document](../command-reference.md)

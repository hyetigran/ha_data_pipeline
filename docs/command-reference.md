# CLI and MCP reference

## Startup and storage

The `house-account` entry point uses these default paths and settings.

| Option | Default | Meaning |
| --- | --- | --- |
| `--data` | `data` | Supplied private pack. |
| `--database` | `var/house_account.sqlite` | Published SQLite snapshot. |
| `--ledger` | `review/decisions.jsonl` | Private decision history. |
| `--as-of` | `2026-11-02` | MCP reference date in `America/Chicago`. |

Without a subcommand, the CLI starts the MCP stdio server. Startup imports a missing snapshot and reuses a valid existing snapshot. An invalid existing snapshot causes a safe startup failure.

The `ingest` subcommand validates the supplied file layout, builds a candidate, and publishes it transactionally. Missing required files, unexpected data files, incomplete pages, and conflicting payloads for one source identity abort the import. `.DS_Store` is optional metadata. Valid empty pages have file-level accounting.

| Import exit code | Meaning |
| --- | --- |
| `0` | Import and requested report write succeeded. |
| `1` | Import failed. The previous published snapshot remains available. |
| `2` | Publication succeeded, but the report write failed with `published_report_failed`. |

The database uses owner-only permissions. A maintenance lock allows one writer per database path. WAL mode and full synchronous durability support transactional publication. A read transaction keeps one revision until it ends. A SQLite backup includes committed WAL contents. A copy of the main file alone might not.

## History queries

The CLI accepts `query property`, `query radius`, `query block`, and `query provider`.

| Query | Default scope |
| --- | --- |
| `property` | All retained history for the supplied exact home. |
| `radius` | Half a mile, from November 2, 2024 to November 2, 2026. |
| `block` | The supplied hundred block, from November 2 to November 16, 2026. |
| `provider` | Provider history and the next three candidate openings of at least two hours. |

Date boundaries use Chicago local midnight. Windows include the start and exclude the end. Provider names resolve only when one canonical business matches. Canonical IDs are also valid provider references.

Property history separates completed service evidence from other observations. Job counts and completed-visit counts remain distinct. Trade groups can overlap. CLI job `services` describes the whole job scope. `completion_supported_services` and each completion's `supported_services` describe attributed work.

## Availability queries

The CLI accepts `query openings`, `query available`, and `query recommend`.

| Option or query | Meaning |
| --- | --- |
| `openings` | Candidate intervals for one provider, within supplied schedule coverage. |
| `available` | Relevant completed trade history and sufficient openings in a postal code. Default window is three days. |
| `recommend` | Eligible providers for a service in a postal code. Default window is this week. |
| `--start`, `--end` | Aware ISO timestamps. Maximum horizon is 31 days. |
| `--duration-minutes` | Explicit requested duration. |
| `--limit` | Maximum result count within the command's validated bounds. |
| `--trade` | Trade filter for supported availability queries. |
| `--service` | Service filter for recommendations. |

The schedule ends at December 3, 2026, midnight in `America/Chicago`, exclusive. A later requested window does not establish free time beyond that coverage.

Known availability with no sufficient opening differs from unknown availability. Partial availability includes both candidate openings and unknown periods. All openings assume conservative provider capacity. Travel remains unmodeled. Confidence is an explained ordinal score, not a probability.

## Review decisions

The commands are `review export`, `review validate`, and `review apply`. `review apply --dry-run` previews changes without publishing facts or appending decisions.

| Decision | Effect |
| --- | --- |
| `approve` | Applies the exact proposed action to its bound evidence version. |
| `reject` | Leaves the action unapplied and suppresses the identical proposal from the new-review count. |
| `defer` | Leaves the proposal unresolved. |
| Superseding decision | Retains the old event and reconstructs derived facts from the effective decisions. |

Export preserves human edits and retains stale versions in `stale_proposals`. Changed evidence invalidates dependent approvals. Apply appends and fsyncs new ledger events before publishing the database. A failure between those steps reports `recorded_not_applied`. Repeated application adds no duplicate events.

Reviewer attribution is self-declared. The ledger is append-only application history, not authenticated audit storage. The wrong-year and transposed-house-number proposals remain deferred unless a reviewer explicitly approves them.

## MCP tools

The server exposes six tools.

| Tool | Result |
| --- | --- |
| `search_service_history` | Nearby completed work grouped by provider and trade. |
| `find_available_providers` | Relevant completed history and a sufficient candidate opening. |
| `get_block_schedule` | Active appointments on a hundred block. |
| `get_provider_profile` | Trades, declared areas, observed areas, history, and openings. |
| `get_property_history` | Attributed work and dates for the requested home. |
| `recommend_provider` | Eligible providers, explained scores, exclusions, and duration assumptions. |

Tool discovery returns the executable input and output schemas. The server rejects extra fields and out-of-range arguments. Tools accept no SQL or arbitrary file path. Each call reads one consistent SQLite snapshot.

Responses include the snapshot revision, ingestion time, reference date, coverage, limitations, and bounded evidence. Collections state their total, limit, and truncation. MCP job responses distinguish completion-supported `services` from `job_scope_services`.

Public fields omit homeowner contacts, private notes, personal calendar titles, and internal source paths. Neighborhood results use aggregates or block locations. Exact-home history applies only to the requested address. Local tool access does not prove property ownership.

## Source accounting

`source_records` holds unique source identities and content hashes. `occurrences` retains every input location, including duplicates. `entity_evidence` records normalization rules and confidence labels. `issues` records missing or ambiguous values. `input_files` records hashes and valid empty pages.

For every source group, `seen = accepted + duplicate + unresolved + rejected`. An identical repeat counts as a duplicate even when the unique record has issues. Those issues remain attached to the unique record. Source counts are not counts of reconciled businesses or homes.

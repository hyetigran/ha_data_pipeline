# Query local home services through MCP

The importer builds a private SQLite snapshot from all six supplied sources and the street reference. P2 adds canonical identities, history queries, and a local human review workflow. P3 adds candidate openings and evidence-based provider rankings. P4 exposes six bounded read-only MCP tools over local stdio.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the current-versus-target design and diagrams, and [the project plan](docs/project-plan.md) for the implementation sequence and remaining grading evidence.

## Start the MCP server

Install Python 3.13 and `uv`, then put the supplied private pack in `data/`. From the repository root, run:

```sh
uv run --locked house-account --data ./data --as-of 2026-11-02
```

Startup imports a missing `var/house_account.sqlite` through the existing maintenance path, then serves MCP over stdin and stdout. A valid existing snapshot is reused. An invalid snapshot fails with a maintenance instruction. Refresh existing data explicitly with `ingest`; a tool call never imports or applies review decisions. Diagnostics go to stderr. This command waits for an MCP client rather than printing a human-readable answer.

The server uses the fixed challenge reference date in America/Chicago. Evidence coverage remains bounded by the supplied schedules, independently of `--as-of`. To choose paths, use `--database` and `--ledger` at startup. No tool accepts a database path, arbitrary file path, or SQL.

## Connect Codex

Install Codex CLI and authenticate with `codex login`. After `uv sync --locked`, replace `/absolute/path/house_account` below with this checkout's absolute path. This registration command changes your Codex MCP configuration only when you run it:

```sh
codex mcp add house_account -- /absolute/path/house_account/.venv/bin/python -m house_account.cli --data /absolute/path/house_account/data --database /absolute/path/house_account/var/house_account.sqlite --ledger /absolute/path/house_account/review/decisions.jsonl --as-of 2026-11-02
```

Restart or start Codex, then ask one of the questions in [the demo question set](evals/questions.json). The equivalent stdio configuration is:

```toml
[mcp_servers.house_account]
command = "/absolute/path/house_account/.venv/bin/python"
args = ["-m", "house_account.cli", "--data", "/absolute/path/house_account/data", "--database", "/absolute/path/house_account/var/house_account.sqlite", "--ledger", "/absolute/path/house_account/review/decisions.jsonl", "--as-of", "2026-11-02"]
startup_timeout_sec = 120
```

Pre-importing the snapshot avoids a client's first-start timeout. The recorded demo uses temporary per-invocation configuration and a disposable snapshot, so it does not change the operator's Codex configuration.

| Tool | Purpose |
| --- | --- |
| `search_service_history` | Completed work near an address, grouped by provider and trade. |
| `find_available_providers` | Completed trade history in a ZIP plus a sufficient candidate opening. |
| `get_block_schedule` | Active appointments on a specified hundred block. |
| `get_provider_profile` | Trades, declared and observed areas, bounded history, and openings. |
| `get_property_history` | Who performed what work and when at the requested home. |
| `recommend_provider` | Eligible providers with explained scores, exclusions, and duration assumptions. |

Responses carry the snapshot revision, ingestion time, reference date, window, coverage, bounded evidence, and limitations. Collections disclose their total, limit, and truncation. Neighborhood responses do not reveal neighboring exact addresses. Business labels are untrusted data; they never authorize actions. Raw notes, homeowner contacts, private calendar titles, and review artifacts are not public fields.

## Verify and capture the Codex demo

Use a new evidence directory for each run:

```sh
uv run --locked python scripts/verify_p4.py --output artifacts/P4/protocol-run --rounds 30
uv run --locked house-account ingest --data data --database artifacts/P4/demo-input/snapshot.sqlite --ledger artifacts/P4/demo-input/decisions.jsonl
uv run --locked python scripts/demo.py --database artifacts/P4/demo-input/snapshot.sqlite --output artifacts/P4/codex-run
```

The protocol verifier owns and removes its temporary database. The demo runner reads the explicitly supplied disposable snapshot and retains real Codex events, tool results, answers, and cleanup receipts. It requires normal Codex authentication and network access for the agent. The MCP server itself is local. A successful capture still needs semantic review of the answers; exit status alone is insufficient.

See [the data model](docs/data-model.md), [AI-use note](docs/ai-use.md), and [P4 execution record](docs/p4-execution.md) for evidence and remaining review items. P4 stays unmerged until the operator reviews the interaction.

## Run the importer

Install Python 3.13 and `uv`. Copy the supplied pack into `data/`, with `data/README.md`, `data/sources/`, and `data/reference/` present. The pack is private and excluded from Git.

```sh
uv run --locked house-account ingest --data data --database var/house_account.sqlite --report artifacts/P2/import.json
```

A successful command prints a JSON report and exits with code 0. It creates the database with owner-only permissions. The report contains counts and input hashes, not customer payloads. The SQLite file contains private source payloads and must remain local.

An import failure exits with code 1 and leaves the previous snapshot intact. If publication succeeds but writing the report fails, the command exits with code 2 and reports `published_report_failed`. A failure to sync the directory after publication produces an explicit durability warning. The published file remains the current snapshot.

The importer expects the supplied pack's file layout. Missing files, unexpected data files, incomplete page sets, and conflicting payloads with the same source identity abort the import. `.DS_Store` is optional metadata. Six empty estimate pages are valid and have explicit file-level accounting. Updated file contents are accepted after validation; the packaged manifest checks paths, not fixed content hashes.

## Verify P1

```sh
uv run ruff check .
uv run mypy src
uv run pytest
uv run python scripts/verify.py --stage P1 --output artifacts/P1/live.json
uv run python scripts/benchmark.py --stage P1 --output artifacts/P1/benchmark.json
```

To run one live scenario, add `--lane 1` through `--lane 10` and choose a separate output path. Verification uses fresh temporary databases and real CLI subprocesses. It checks accounting, nested visits, estimates, duplicated pages, ambiguous spreadsheet fields, cancellations, amounts, repeat imports, failure recovery, and provenance.

The benchmark performs one warmup and five measured full imports in fresh processes. Each process verifies stored row counts and SQLite integrity. It reports end-to-end wall time and peak process memory. There is no pre-implementation performance baseline.

## Inspect the snapshot

The importer keeps source-local provider, property, job, estimate, and visit identities. These source-table counts are not reconciled real-world entity counts. The separate canonical tables and crosswalk record P2 matches. Unresolved calendar and spreadsheet provider links remain review proposals. Workiz customer payload variants remain distinct evidence. Jobs and estimates have separate tables and visit parent relationships, including completed estimate appointments that are not completed service work.

`source_records` stores unique source identity and content hashes. `occurrences` preserves every input location, including exact duplicates. `entity_evidence` records each normalization rule and its confidence label. `issues` retains missing and ambiguous values. `input_files` records all file hashes and valid empty pages. Reports include source and source-kind accounting. For each group, seen equals accepted plus duplicate plus unresolved plus rejected. Duplicate classification takes precedence when an identical record also has issues; those issues remain attached to the unique record.

A writer lock permits one import per database path. The importer validates a candidate, then publishes it into the persistent database in one transaction. WAL and full synchronous durability are enabled. Read transactions retain a consistent revision. Use SQLite backup APIs, not a lone main-file copy, for live backups. See [P2R migration and recovery](docs/p2r-migration.md).

P3 expands calendar recurrence within a bounded horizon and respects all-day exclusive endpoints, transparency, and tentative status. Ambiguous spreadsheet dates and missing durations remain unresolved. The identified year and address corrections are not applied. The local review workflow below handles those proposals.

See [the project plan](docs/project-plan.md), [decision log](docs/decisions.md), and [inspection findings](docs/data-pack-inspection.md) for scope and source limitations.

## Reconciliation and local review (P2)

Ingestion now also builds canonical provider, property, job, and visit projections. Original source-local rows remain intact. Providers merge automatically on a shared business phone plus corroborating trade evidence. Address normalization preserves units, standardizes street suffixes and Texas/TX, and infers missing locality only from one supported street segment. Segment interpolation gives approximate coordinates. Canonical IDs persist as matching evidence grows. Merges retain redirects; split references remain ambiguous. Version 2 uses typed source assertions and relational canonical facts, with JSON reserved for raw payloads and variable evidence.

Job identity remains conservative. Exact repeated source observations deduplicate during P1. Cross-source jobs with matching provider, property, service, and interval become review candidates rather than automatic merges. Recurring visits remain distinct. Completed Jobber visits and HCP completion timestamps establish history. Workiz Done status establishes completion but its scheduled date is approximate service-date evidence. A contradictory year remains uncertain until reviewed. CSV payment alone does not establish completion.

Run the four history queries locally:

```sh
uv run --locked house-account query radius '4512 Live Oak St, Dallas, TX 75204'
uv run --locked house-account query block '4500 Live Oak St, Dallas, TX 75204'
uv run --locked house-account query property '5823 Belmont Ave, Dallas, TX 75206'
uv run --locked house-account query provider CANONICAL_PROVIDER_ID
```

The radius window defaults to November 2, 2024 through November 2, 2026. The block window defaults to November 2 through November 16, 2026. Boundaries are Chicago local midnight and the end is exclusive. Exact-property results separate confirmed completed history from other or uncertain jobs. Provider summaries expose history and the next three candidate openings, including explicit unknown or partial availability. Responses contain business labels, bounded service categories, opaque evidence references and coverage limitations. They exclude customer contacts, raw notes, personal calendar titles and source paths.

Export proposals into the private local review file:

```sh
uv run --locked house-account review export --file review/reconciliation.json
uv run --locked house-account review validate --file review/reconciliation.json
uv run --locked house-account review apply --file review/reconciliation.json --dry-run
```

Edit only each proposal's `human` object. Set `decision` to `approve`, `reject`, or `defer`. Explicit decisions require `reviewer`, UTC `decided_at`, and `reason`. Missing decisions defer. Reviewer attribution is self-declared. Proposal IDs, evidence, hashes, actions, and confidence are generated content and cannot be altered into an approval. The schema is `schemas/reconciliation-review.schema.json`.

After reviewing the dry-run changes, apply the file:

```sh
uv run --locked house-account review apply --file review/reconciliation.json
```

Dry-run builds and validates a temporary snapshot without publishing it or recording decisions. Apply holds the maintenance lock, validates the candidate, appends and fsyncs new events to `review/decisions.jsonl`, then transactionally publishes facts and identity changes. A failure after recording is reported as recorded but not applied. Re-run ingestion with the same ledger to recover. Repeated application records no duplicate events. Existing readers adopt the new revision when they start a new read transaction.

To reverse a decision, replace its `human` object with a new decision and reason and set `supersedes_decision_id` to that proposal's latest ledger decision ID. Rebuilding from originals reverses earlier derived changes. Export preserves human edits and keeps stale evidence versions in `stale_proposals`. Changed records invalidate only dependent decisions. A stale approval never changes new evidence. The ledger is append-only application history, not tamper-proof authenticated audit storage.

The Lakewood wrong-year interval and Ray house-number correction default to defer. Implementing review does not approve either correction. There is no multi-user review UI. Review artifacts contain private evidence and remain ignored by Git with owner-only file permissions.

Run the sanitized demonstration without changing the actual data pack or review ledger:

```sh
uv run --locked pytest
uv run --locked python scripts/verify_p2_review.py
```

The fixture demonstrates approve, reject, defer, repeat application, and supersession. The P2 review workflow preserves its original scope. P3 adds availability separately; travel estimates and MCP tool serving remain deferred.

The sanitized demonstration is an integration check with a fixture importer. Verify the real CLI against disposable copies and independently inspected source answers with these commands. The active snapshot and review decisions remain unchanged.

```sh
uv run --locked python scripts/verify_p2_cli.py
uv run --locked python scripts/verify_p2_independent.py
uv run --locked python scripts/benchmark_p2.py
```

See [the P2 execution record](docs/p2-execution.md) for measured results and remaining limitations.

## Relational redesign (P2R)

See [the execution record](docs/p2r-execution.md), [architecture](ARCHITECTURE.md) and [migration notes](docs/p2r-migration.md). Jobs retain lifecycle independently of service completion. Estimates, services, completion evidence, temporal uncertainty and identity state are explicit SQL facts. Query output now includes separate completed-visit counts and qualified service dates. P3 consumes these facts for availability and ranking.


## Find openings and recommendations (P3)

After importing, run:

```sh
uv run --locked house-account query available 75214 --trade handyman --duration-minutes 120
uv run --locked house-account query openings 'Lone Star Plumbing' --limit 3
uv run --locked house-account query recommend 75206 --service water_heater
```

The fixed reference date is November 2, 2026 in America/Chicago. `available` defaults to the next three days, `recommend` to this week, and `openings` to the supplied schedule coverage through December 2. Override the horizon with aware ISO timestamps in `--start` and `--end`, up to 31 days. Override the duration with `--duration-minutes`, and cap results with `--limit`. Every interval includes its start and excludes its end.

Responses distinguish unknown availability from a known schedule with no sufficient opening. Unknown weekdays and emergency-only hours do not establish routine availability. Active visits, estimate appointments, vacations, and opaque tentative calendar events consume time. Transparent and cancelled events do not. Work outside the reference postal codes still consumes time.

All openings are candidates under a conservative provider-level capacity assumption. Travel is unmodeled. Confidence is an explained ordinal score, not a probability or booking guarantee. See [the scheduling policy](docs/p3-design.md) for evidence, duration, and ranking rules, and [the P3 execution record](docs/p3-execution.md) for verification results.

On the supplied pack, the default water-heater recommendation can correctly return no eligible providers this week. A shorter explicit duration is a different request, not an automatic fallback to make the answer nonempty. The response explains each exclusion and duration assumption.

Run the P3 checks with a disposable snapshot:

```sh
uv run pytest tests/test_availability.py tests/test_ranking.py
mkdir -p artifacts/P3/parent-source
git archive c6c151e | tar -x -C artifacts/P3/parent-source
uv run python scripts/verify_p3.py --data data --output artifacts/P3/live
uv run house-account ingest --data data --database artifacts/P3/perf/snapshot.sqlite --ledger artifacts/P3/perf/decisions.jsonl
uv run python scripts/benchmark_p3.py --database artifacts/P3/perf/snapshot.sqlite
```

The live verifier owns temporary databases and removes them while retaining receipts. The benchmark reads the explicit disposable snapshot. Private artifacts remain ignored by Git. MCP serving and the connected-agent demo are not implemented by P3.

# Import the home services data pack

P1 builds a private SQLite snapshot from the six supplied sources and the street reference. Cross-source reconciliation, review approval, availability, and MCP tools are planned for P2 through P4 and are not implemented.

## Run the importer

Install Python 3.13 and `uv`. Copy the supplied pack into `data/`, with `data/README.md`, `data/sources/`, and `data/reference/` present. The pack is private and excluded from Git.

```sh
uv sync --locked
uv run house-account ingest --data data --database var/house_account.sqlite --report artifacts/P1/import.json
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

The importer keeps source-local provider, property, job, estimate, and visit identities. Counts are not reconciled real-world entity counts. Profiles and calendars retain independent provider assertions until P2 links them. Workiz customer payload variants remain distinct evidence. Jobs and estimates have separate tables and visit parent relationships, including completed estimate appointments that are not completed service work.

`source_records` stores unique source identity and content hashes. `occurrences` preserves every input location, including exact duplicates. `entity_evidence` records each normalization rule and its confidence label. `issues` retains missing and ambiguous values. `input_files` records all file hashes and valid empty pages. Reports include source and source-kind accounting. For each group, seen equals accepted plus duplicate plus unresolved plus rejected. Duplicate classification takes precedence when an identical record also has issues; those issues remain attached to the unique record.

A writer lock permits one import per database path. The importer builds a sibling temporary file, checks foreign keys and integrity, verifies that inputs did not change, and atomically replaces the previous file. Existing read-only connections continue reading the old snapshot. Reconnect to adopt the new snapshot. No WAL sidecars are used.

Calendar recurrence definitions, all-day exclusive endpoints, transparency, and tentative status remain available for P3. Ambiguous spreadsheet dates and missing durations remain unresolved. The identified year and address corrections are not applied. Human review is a P2 deliverable.

See [the project plan](docs/project-plan.md), [decision log](docs/decisions.md), and [inspection findings](docs/data-pack-inspection.md) for scope and source limitations.

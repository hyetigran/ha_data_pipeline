# Verify stored source evidence

Read a snapshot to understand service work, estimate appointments, ambiguous fields, duplicate input locations, and the provenance behind stored assertions.

## Check the expected behavior

- `inspect-visits`: jobs retain their nested visits, and estimates remain separate from service work.
- `inspect-duplicates`: duplicate pages and spreadsheet rows retain occurrence accounting.
- `inspect-unresolved`: ambiguous dates and unknown durations remain explicit.
- `inspect-values`: cancellations keep raw status and job amounts retain integer-cent values.
- `inspect-provenance`: duplicate evidence retains source key, timestamp, normalization rule, and confidence.

## Exercise the public commands

Import with `house-account ingest`, then open the database with a read-only SQLite client. Inspect `jobs`, `estimates`, `visits`, `occurrences`, `issues`, `source_records`, and `entity_evidence`. For canonical history, use the query commands in [Canonical history queries](history.md). Raw source evidence remains a read-only SQLite workflow.

## Run the isolated checks

Complete the setup and doctor checks in [Verify House Account](../SKILL.md) with the supplied pack, which contains nested visits, estimates, duplicates, cancellations, and ambiguous spreadsheet rows.

1. Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py inspect`. After a real import and aggregate DB checks, lanes 2–7 and 10 exercise real imports and read-only queries. Expected results include 689 estimates, 131 scheduled estimate visits, 4,630 unique HCP jobs from 4,633 occurrences, 206 spreadsheet rows with 8 duplicates, and 198 unknown durations.
2. Read result.json and each lane's JSON plus captured stdout and stderr at the printed evidence path. Require all lanes pass, foreign keys valid, and scratch_removed true.

## Check the limits

- A completed estimate appointment does not establish completed service work.
- Amount comparisons inspect private raw records in memory. Do not export those records as evidence.
- Missing feature examples in an updated pack are failed prerequisites. Record the reason rather than weakening the journey.
- Recurrence definitions are retained as source evidence. P3 derives candidate openings from those definitions. See [Availability and rankings](availability.md).

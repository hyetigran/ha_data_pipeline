# House Account verification map

Use [Launch and Doctor](../SKILL.md) with Python 3.13, locked dependencies, and the private supplied pack. Every feature uses disposable database and ledger paths. Evidence survives under `artifacts/verification/`.

- [Import and reporting](import.md) covers source accounting and canonical reconciliation during import.
- [Inspect source evidence](inspect.md) covers source-local visits, estimates, duplicates, unresolved values, and provenance.
- [Replace and recover](replacement.md) covers repeat import, read-transaction revisions, failed input, and failed report publication.
- [Canonical history queries](history.md) covers property, radius, block, and provider commands and their privacy boundary.
- [Reconciliation review](review.md) covers export, validation, previews, decisions, repetition, supersession, and stale evidence.
- [Migrate and restore a legacy snapshot](migration.md) covers schema-v2 upgrade and backup restoration with the frozen private baseline.

Run all six journeys for maintenance coverage. Missing data or the frozen migration baseline is an explicit blocked prerequisite. Do not mark a different journey as proof of an unreachable path. P3 availability and P4 MCP serving remain outside this map until implemented.

The CLI defaults point at working database and review paths. The helper overrides these paths or runs existing P1 scripts from scratch. Keep command transcripts, exit codes, resulting state, and cleanup receipts. Run notes and private evidence remain uncommitted.

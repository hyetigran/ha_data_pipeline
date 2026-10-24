# House Account verification map

Baseline: Python 3.13, locked dependencies, the supplied private `data/` pack, and a successful doctor from [the skill](../SKILL.md). Each recipe imports into its own empty temporary directory and preserves evidence in `artifacts/verification/`. No auth or running server is required. Never point verification at the user's working database.

- [Import and reporting](import.md): build a private snapshot and account for all supplied sources.
- [Inspect source evidence](inspect.md): distinguish jobs, estimates, visits, duplicates, unresolved fields, and provenance.
- [Replace and recover](replacement.md): repeat imports and distinguish failed import from failed report publication.

Run all three helper commands for maintenance coverage. CLI entry is `house-account ingest` (equivalent to `python -m house_account.cli ingest`); inspection uses read-only SQLite. Defaults target `data/` and `var/house_account.sqlite`; recipes deliberately supply explicit isolated paths. Record commands, outputs, exits, and stored-state assertions, not just a final success message. A missing pack is a concrete prerequisite failure; changed fixtures that fail fixed baseline assertions must be investigated, not silently skipped. Planned P2–P4 surfaces are excluded until implemented. Run notes belong in scratch/evidence, not Git.

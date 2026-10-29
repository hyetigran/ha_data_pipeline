# House Account verification map

The verification helper covers nine features through disposable databases and ledgers. Each run retains evidence under `artifacts/verification/`. [Verify House Account](../SKILL.md) contains setup, commands, and cleanup requirements.

| Feature | Coverage | Additional prerequisite |
| --- | --- | --- |
| [Setup](setup.md) | Local install, snapshot preparation, configuration export, and isolated UAT runs | Cached dependencies for offline setup |
| [Import](import.md) | Accounting, reports, reconciliation, and schema publication | None |
| [Inspect](inspect.md) | Visits, estimates, duplicates, unresolved values, and provenance | None |
| [Replacement](replacement.md) | Repeat import, reader revisions, and publication failures | None |
| [History](history.md) | Property, radius, block, provider, and privacy checks | None |
| [Review](review.md) | Export, validation, previews, decisions, repetition, supersession, and stale evidence | None |
| [Migration](migration.md) | Schema-v2 upgrade and restoration | Private frozen P2 database |
| [Availability](availability.md) | Openings, calendars, uncertainty, eligibility, and ranking | Local P2R Git object |
| [MCP](mcp.md) | Discovery, six calls, safe errors, unchanged state, and shutdown | None |

Every feature requires Python 3.13, locked dependencies, and the supplied private pack. Missing prerequisites block the affected journey. Passing another journey does not cover that path.

The helper overrides working database and review paths. Receipts contain commands, exit codes, resulting state, and cleanup results. Private evidence and run notes remain uncommitted.

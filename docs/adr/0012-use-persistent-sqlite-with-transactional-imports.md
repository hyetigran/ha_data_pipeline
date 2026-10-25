# Keep a persistent SQLite database with transactional imports

Accepted as revised Q23 on October 24, 2026. Retain SQLite and one persistent database rather than replacing the entire database file on every import. Preserve identity bookkeeping across imports; stage and validate new data, then transactionally publish the derived state together with relevant identity changes. Failed imports must preserve the last successfully published state.

This supersedes whole-file replacement as the target import architecture, not the current implementation. SQLite durability is not the reason for this redesign; authoritative identity preservation and coordinated publication are. Crash-recovery verification and backup/restore procedures are required. Local review-file authority and reconciliation with database publication still need a detailed recovery contract. No migration has been performed.

The operator also identified continuous source ingestion and syncing as a production requirement. A persistent database is necessary infrastructure for the proposed approach, not a completed sync implementation. Source revision retention, delivery retries, checkpointing, out-of-order updates, disappearance/deletion semantics and freshness remain to be designed.

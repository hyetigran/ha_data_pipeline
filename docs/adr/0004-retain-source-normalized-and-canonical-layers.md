# Retain source-normalized entities alongside canonical entities

Accepted in the October 24, 2026 schema interview. Keep original source records, normalized source entities, and reconciled canonical entities as separate representations. Entity-appropriate fields replace the generic shared column shape; frequently queried facts and relationships belong in regular SQL columns, while raw payloads and variable evidence metadata may remain JSON.

This accepts additional schema maintenance so conflicting source assertions remain inspectable before and after reconciliation. Removing the normalized source layer was considered but rejected for this design. The exact tables, constraints and migration procedure remain open.

This is an accepted design decision, not an implemented change.

The operator accepted Q14: canonical jobs and estimates require a provider but may have an unresolved property reference. Missing, unresolved and conflicting property evidence must be explicit; do not create a fabricated placeholder property. Preserve the original address and disclose incomplete coverage when exact-property queries exclude unresolved work. This is an accepted design rule, not an implemented change.

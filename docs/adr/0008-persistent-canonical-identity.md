# Persistent canonical identities

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Agent references need to survive changes in supporting evidence. Q11 replaces IDs derived only from the current member set with a persistent identity registry.

New matching evidence retains an existing identity. A merge selects a surviving ID and redirects retired IDs. A split can make an old reference ambiguous rather than silently choosing one resulting entity.

The first Q23 proposal placed identity state in a separate durable store. The operator did not accept that arrangement. Revised Q23 selected one persistent SQLite database with transactional imports, recorded in [ADR 0012](0012-use-persistent-sqlite-with-transactional-imports.md).

The problem was whole-file replacement losing authoritative state, not a lack of SQLite durability. Migration preserves existing references and explicit resolution behavior.

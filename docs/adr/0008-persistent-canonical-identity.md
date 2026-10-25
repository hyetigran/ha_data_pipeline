# Preserve canonical IDs as evidence changes

Accepted as Q11 in the October 24, 2026 schema interview. Canonical IDs persist when new evidence joins an entity. A merge retains one ID and records a redirect from retired IDs. A split makes an old reference ambiguous rather than silently choosing one resulting entity.

This supersedes D005's member-set-derived identity behavior as the target design, not as a description of the current implementation. Stable agent references require durable identity bookkeeping across rebuilds instead of deriving identity solely from current membership. The registry's storage, merge/split event representation, atomic publication and recovery rules remain to be designed.

This decision is not yet implemented. Existing IDs must be considered during migration rather than silently discarded.

Q23's proposed separate durable identity store was not accepted. The storage arrangement remains open. SQLite durability is not the issue: replacing an entire generated database without preserving authoritative state is an application-design concern. A single persistent SQLite database retaining identity tables while replacing derived data transactionally is an alternative under discussion, not an approved change.

Revised Q23 was subsequently accepted: one persistent SQLite database with transactional imports retains authoritative identity state. See ADR 0012. The earlier separate-store proposal remains unaccepted; exact identity publication/recovery rules are still design work.

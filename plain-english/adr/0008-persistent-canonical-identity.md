# Keep IDs stable when evidence changes

An assistant may refer to a provider by its saved ID. New evidence about that provider should not make the old reference useless.

The program keeps an identity register. If two identities merge, old IDs point to the surviving identity.

If one identity splits into several, an old ID may become unclear. The program must not secretly choose one of the new identities.

These IDs live in the persistent SQLite database. They do not need a separate identity database.

---

[Start here](../README.md) · [Original document](../../docs/adr/0008-persistent-canonical-identity.md)

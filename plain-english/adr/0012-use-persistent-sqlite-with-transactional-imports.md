# Save related changes together

An import builds and checks new facts before publishing them. Facts and identity changes are saved together in the persistent SQLite database.

If the build fails, the last good facts remain available. Readers do not see a half-finished import.

The human decision log is saved separately. If a decision is recorded but publication fails, the next import can replay that decision.

This improves full imports. It does not add continuous live updates.

---

[Start here](../README.md) · [Original document](../../docs/adr/0012-use-persistent-sqlite-with-transactional-imports.md)

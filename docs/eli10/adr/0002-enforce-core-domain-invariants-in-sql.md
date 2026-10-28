# The database checks its own rules

A visit must belong to a valid job or estimate. Status values must come from the allowed list.

The database enforces these rules. A faulty file reader cannot quietly save broken links or made-up status values.

Python reads and interprets the source. Database checks protect the saved facts. This takes more design work, but prevents invalid data from reaching answers.

---

[Start here](../README.md) · [Original document](../../adr/0002-enforce-core-domain-invariants-in-sql.md)

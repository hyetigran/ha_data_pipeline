# Why the database was redesigned

The early version stored many shared facts in large JSON records. JSON is a text format for groups of values.

The redesign put commonly searched facts into separate database tables with clear links. That made the meaning of each record easier to enforce and query.

The program still keeps three things: the original record, the cleaned source claim, and the shared fact used in answers.

It also keeps jobs, visits, and completed work separate. One visit belongs to one job or estimate. Several services can belong to one job.

Dates can be unknown or disputed. Missing apartment numbers and prices stay missing. A guessed value is not silently treated as a fact.

IDs survive later imports. The database publishes the new facts and identity changes together after checks pass.

The redesign adds more import work and more tables. In return, the program can better explain its answers and reject invalid record links.

The individual reasons are in the short [design decisions](README.md#small-design-decisions). Most were implemented in P2R. The rule about complete and partial live updates is still future work.

---

[Start here](README.md) · [Original document](../docs/schema-redesign.md)

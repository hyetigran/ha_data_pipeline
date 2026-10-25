# Enforce core domain invariants in SQL

Accepted in the October 24, 2026 schema interview. Core relationships and controlled canonical values should be database-enforced rather than relying solely on the generic Python ingestion model. Python remains responsible for interpreting source formats and representing uncertainty; unrecognized raw values must survive as source evidence rather than becoming arbitrary canonical values.

This trades some schema and migration effort for stronger guarantees as adapters evolve. Exact tables, controlled vocabularies and unknown-value constraints remain to be decided; this does not authorize discarding source observations.

This is an accepted design decision, not an implemented change.

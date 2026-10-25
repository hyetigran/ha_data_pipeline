# Store searchable provider facts in related tables

Accepted as Q8 in the October 24, 2026 schema interview. Provider aliases, trades, exclusions and service areas belong in related tables rather than JSON lists. Declared service coverage remains separate from observed work history. This adds relationships and joins but supports lookup, filtering and constraints without conflating declarations with demonstrated experience.

Table names, keys and derivation of observed coverage remain part of the physical design. This decision is not yet implemented.

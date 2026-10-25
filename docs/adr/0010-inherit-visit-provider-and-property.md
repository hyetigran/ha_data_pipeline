# Derive visit provider and property through its parent

Accepted as Q13 in the October 24, 2026 schema interview. A canonical visit belongs to exactly one job or estimate, enforced in SQL. Its provider and property are obtained through that parent rather than independent copies on the visit. Worker assignments remain separate evidence.

This eliminates inconsistent parent/visit ownership at the cost of an extra join and assumes a job or estimate belongs to one provider and at most one resolved property. Multi-provider or multi-property projects require an explicit future extension. Original source assertions remain preserved even when they conflict. No implementation has changed.

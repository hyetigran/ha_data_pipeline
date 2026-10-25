# Field-level lineage

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

A record's origin does not explain every derived field. A reference-derived postal code and a reviewed house-number correction have different supporting evidence.

Q10 requires field-level lineage for normalized, inferred, corrected, and contested values. Unchanged raw facts can retain record-level provenance without a duplicate mapping for every field.

Q22 selects values through field-specific rules and valid evidence-bound corrections. No source wins every conflict, and the latest import does not establish the latest business fact. Unresolved contradictions remain visible. Declared coverage remains distinct from observed history.

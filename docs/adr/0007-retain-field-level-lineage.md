# Retain field-level lineage for derived and contested facts

Accepted as Q10 in the October 24, 2026 schema interview. Normalized, inferred, corrected and conflicting canonical facts need field-level provenance identifying their supporting assertions, rules and applicable review decisions. Unchanged raw facts may inherit record-level provenance rather than duplicating every mapping.

This permits explaining a reference-derived ZIP independently of a reviewed house-number correction. It adds provenance bookkeeping but avoids implying that every field came from the same source. The exact SQL relationship design remains open. This decision is not yet implemented.

Q22 accepted: field-specific selection rules and valid evidence-bound human corrections determine selected values; neither a globally preferred source nor most recent ingestion wins universally. Unsettled contradictions remain explicit, and declared coverage is distinct from observed history.

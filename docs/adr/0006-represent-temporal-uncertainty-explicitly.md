# Represent temporal uncertainty explicitly

Accepted as Q9 in the October 24, 2026 schema interview. Temporal values carry an explicit evidence state distinguishing known, missing, ambiguous and disputed assertions. Scheduled time, completion evidence and source status-update time remain distinct, with the original assertion and timezone interpretation preserved.

A missing timestamp alone cannot distinguish the November 1 DST fold from an absent date or a disputed year. The physical representation must preserve partial dates and uncertainty without inventing instants. The exact column/check design remains open. This decision is not yet implemented.

Q16 subsequently accepted separate selected UTC instant, local date, evidence state (known/missing/ambiguous/disputed) and precision (instant/date/unknown) for each scheduled endpoint, with a timezone name. Enforce consistent combinations. An ambiguous or disputed time has no selected UTC instant; an independently established local date may survive. Candidate interpretations remain evidence. Date-only facts must not become fabricated midnight appointments. Exact timestamp-format validation and source-normalized representations remain implementation-design details.

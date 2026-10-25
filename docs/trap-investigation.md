# Investigate the wrong-year and transposed-number candidates

Inspected October 24, 2026. Both suspected anomalies have strong supporting evidence in the supplied pack. The conflicts are verified. Their intended corrections remain inferences because the hidden grader crosswalk is unavailable. No source records were edited.

## Wrong-year candidate in Lakewood Air

Workiz job `J8OMKP`, serial 267, describes heat pump repair. It starts at [jobs.json line 3239](../data/sources/workiz/lakewood_air/jobs.json#L3239).

| Field | Source value |
| --- | --- |
| Status | Done |
| JobDateTime | 2026-11-10 10:00:00 |
| JobEndDateTime | 2026-11-10 12:00:00 |
| CreatedDate | 2025-11-01 10:00:00 |
| LastStatusUpdate | 2025-11-11 14:00:00 |

The scheduled interval is after the November 2, 2026 challenge snapshot, even though the record is Done and its status update is almost a year earlier. Serial 266 is scheduled November 7, 2025. Serial 268 is scheduled November 10, 2025. This ordering corroborates the candidate correction of both scheduled timestamps to November 10, 2025.

A calendar-year mismatch alone is not enough. The scan also found legitimate December 31 appointments with completion or status updates on January 1. These must not be flagged by a simplistic unequal-year rule.

Recommended handling is to retain the original timestamps and raise a temporal inconsistency issue. Record the 2025 interval as a high-confidence correction candidate with its evidence. Do not silently rewrite the source or treat the future interval as an ordinary active booking. If the correction is not accepted under an audited rule, withhold a precise historical service date and disclose the uncertainty. LastStatusUpdate is supporting evidence, not an exact completion timestamp.

## Transposed-number candidate in Ray's spreadsheet

Physical row 175 contains an August 14, 2026, 09:00 TV-mount entry at `5832 belmont ave`.

Physical rows 88 and 89 contain an October 3, 2025 drywall-patch entry at `5823 Belmont Ave`. Rows 88 and 89 are exact duplicates and count as one observation. The customer label and normalized phone match row 175.

The same normalized phone also appears in two independent source accounts whose property address is `5823 Belmont Ave`:

- Fresh Nest Cleaning, property `Z2lkOi8vSm9iYmVyL1Byb3BlcnR5LzcxMjMxMTA`, with a completed September 15, 2025 cleaning visit.
- Greenville Ave Plumbing, property `Z2lkOi8vSm9iYmVyL1Byb3BlcnR5LzcxMDkzNzI`, with an upcoming November 11, 2026 visit.

The last two house-number digits are swapped. The repeated address, same spreadsheet customer label, and shared contact evidence make `5823` a high-confidence correction candidate. Contact identity alone cannot prove property identity because one customer can have multiple properties. The different service and date also mean the TV-mount entry is not a duplicate of the drywall-patch job.

Recommended handling is to retain `5832` as the original observation, record `5823` as a proposed corrected property link, and attach the corroborating evidence. Do not introduce a general digit-swap auto-merge rule. Until resolved, keep this entry out of confirmed exact-property history or return it separately as uncertain. The unpaid marker does not establish whether the work was completed.

## Reproduce the evidence checks

Run `python3 scripts/verify_trap_candidates.py`. The script checks the exact date fields, neighboring serials, spreadsheet rows, and cross-source contact agreement. It prints no customer contact details and does not modify the pack.

The investigation scanned CRM date fields for out-of-range years and year disagreements. It compared Housecall Pro job addresses against customer address IDs and Workiz addresses within ClientId groups without finding this transposition there. A cross-source contact comparison located the spreadsheet candidate. This is a targeted investigation, not an exhaustive discovery of every seeded trap.

## Broader audit follow-up

The subsequent [trap register](trap-register.md) covers all six named examples from the user-supplied “22 seeded traps” excerpt, including a verified November 1 DST-fold job, plus other observed pitfalls across all six sources. It distinguishes evidence, implemented behavior, and remaining work. The register is not a verified crosswalk to the hidden 22-item seed manifest.

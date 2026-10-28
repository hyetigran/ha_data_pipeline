# Normalization fixes and six-answer comparison

Implemented locally on October 27, 2026. No commit, publication, or merge was performed. The running database and existing review files were not modified; verification rebuilt isolated snapshots. The six questions use the challenge's November 2, 2026 reference date. All local times below are Dallas/Central.

## What changed

- Specific roofing and gutter terms take precedence over generic leak/cleaning tokens. Exact aliases correct `washer not draining`, `Heating repair`, `Light fixture install`, and other observed labels.
- A bounded alias vocabulary recognizes clear phrases such as `WH replace`, `Tankless conversion`, `assemble IKEA`, `furniture build`, `Hydro jet`, and `EV charger install`. Case and punctuation normalize; arbitrary substrings do not activate these aliases.
- Context-dependent labels such as `No cool`, `spring replacement`, or `move out` require a compatible declared provider trade. Competing interpretations remain unknown. Vague labels such as `spray`, `changeout`, `seasonal maintenance`, and `pilot light out` are not guessed.
- Compound services preserve domain meaning. `Hang TV + hide wires` is one TV-mounting category. `Patch & paint drywall` retains handyman and painting scope; it does **not** receive service-specific completion credit merely because the parent job completed. This preserves ADRs 0009 and 0011.
- Address parsing recognizes a trailing Dallas city, separate comma-delimited units, and `street, B dallas`. Unit identity is retained. `Trail` and `Trl` normalize alike. State/ZIP parsing requires a complete matching field instead of searching arbitrary text for two letters. Conflicting unit forms and ambiguous extra address components are not guessed.

The implementation is in [privacy.py](../src/house_account/privacy.py), [projection.py](../src/house_account/projection.py), and [addresses.py](../src/house_account/addresses.py). Original input values remain in source records.

## Measured effect on the supplied pack

| Measure | Before | After |
| --- | ---: | ---: |
| Jobs with only unknown service categories | 3,576 | 972 |
| Completed jobs with only unknown service categories | 2,165 | 573 |
| Gutter-cleaning jobs incorrectly classified as cleaning | 134 | 0 |
| Trailing-Dallas CSV addresses successfully geocoded | 0 of 24 | 22 of 24 |
| Canonical properties | 3,837 | 3,778 |
| Canonical providers | 43 | 43 |
| Canonical jobs | 11,752 | 11,752 |
| Canonical visits | 15,512 | 15,512 |

The remaining two trailing-Dallas addresses are outside reference coverage; no coordinates were invented. Three corrected CSV addresses preserve unit B, and the four-part Abrams calendar address preserves unit A. The lower property count reflects deterministic spelling/format equivalence, not approved fuzzy matches.

In total, 3,350 jobs have a changed service scope. Independent raw-label checks confirm all 134 gutter cases, 25 `leak in roof` jobs, 50 `washer not draining` jobs, 209 heating-repair jobs, 94 `WH replace` jobs, and 123 IKEA-assembly jobs map to the intended categories. These are record counts, not hidden-seed counts.

## Six required answers

Both captures used the same six MCP calls, the same date/window/duration defaults, and no approved review decisions. The before server ran a saved copy of the pre-change source; the after server ran the changed source. The after snapshot inherited the baseline identity registry. Each capture verified that its MCP calls left the database logically unchanged.

### Q1 — Completed services within half a mile of Live Oak

The sum of provider/trade job counts remains **969**. The service/trade assignment changes:

| Trade | Before | After |
| --- | ---: | ---: |
| Appliance repair | 41 | 44 |
| Cleaning | 170 | 156 |
| Electrical | 110 | 117 |
| Garage doors | 3 | 3 |
| Gutters | 16 | 29 |
| Handyman | 112 | 74 |
| HVAC | 283 | 314 |
| Landscaping | 2 | 3 |
| Painting | 36 | 36 |
| Pest control | 53 | 53 |
| Plumbing | 137 | 133 |
| Roofing | 6 | 7 |

For example, heating repair leaves the generic handyman bucket; gutter cleaning leaves cleaning; roof leaks and washer-drainage work leave plumbing. These are summed provider/trade counts, not a claim that 969 is the global distinct-job count. Trade groups may overlap. Combined patch/paint work remains excluded from service-specific counts when completion attribution is absent.

### Q2 — Handymen in 75214 with a two-hour opening

The same three businesses qualify, in the same order, with the same openings:

| Provider | First candidate opening | Relevant completed jobs, before → after |
| --- | --- | --- |
| White Rock Handyman | November 2, 12:30–17:00 | 122 → 122 |
| Peak Home Services | November 2, 12:30–14:30 | 111 → 111 |
| M Streets Handyman | November 4, 09:00–14:30 | 120 → 119 |

M Streets loses one generic-handyman history attribution under the corrected service categories. The ranking order and opening times do not change. Candidate openings still assume conservative provider-level capacity and do not include travel.

### Q3 — Work scheduled on the 4500 block of Live Oak

The same four visits remain, with unchanged dates and intervals. Two descriptions improve:

| Provider | Local appointment | Before → after service |
| --- | --- | --- |
| Two Sisters Cleaning | November 4, 10:00–13:00 | Cleaning → cleaning |
| Cool Breeze AC & Heat | November 6, 13:00–15:00 | HVAC → HVAC |
| Live Oak Electric | November 9, 08:00–12:00 | Unclassified → electrical |
| Big Tex Roofing | November 12, 15:00–16:00 | Plumbing leak → roofing |

This is a corrected answer about what work is scheduled, not a change to occupancy.

### Q4 — Lone Star Plumbing

The business still has **262 completed jobs**, plumbing as its declared trade, and declared ZIPs 75204, 75206, 75214, 75219, and 75223. Its next three two-hour-or-longer openings remain:

- November 17, 10:30–13:00.
- November 18, 10:30–16:00.
- November 20, 10:00–12:15.

Seventeen of the first 100 returned history entries now have more specific service descriptions, including formerly unclassified water-heater work. The history response is bounded at 100 entries in this comparison; the total of 262 covers all completed jobs. Seventeen is not asserted as the number changed across the full history.

### Q5 — Prior work at 5823 Belmont

The result is unchanged: **four completed jobs**.

| Provider | Service date | Supported service |
| --- | --- | --- |
| Lone Star Plumbing Co. | February 18, 2025 | Water heater |
| Fresh Nest Cleaning | September 15, 2025 | Cleaning |
| Lone Star Plumbing Co. | April 14, 2026 | Leak |
| Frost Bros HVAC | July 8, 2025 | Unclassified |

Frost's vague service wording remains unclassified. The suspected 5832→5823 spreadsheet correction is still deferred and does not become confirmed history here.

### Q6 — Best plumber for water-heater replacement this week

The answer remains **no eligible provider with a sufficient defensible opening under the default duration policy**. We did not shorten the requested work to manufacture a recommendation.

The supporting duration evidence improves:

| Provider | Historical visit sample, before → after | Estimated duration, before → after |
| --- | ---: | --- |
| Greenville Ave Plumbing | 43 → 66 | 270 → 255 minutes |
| Rapid Rooter TX | 99 → 145 | 240 → 240 minutes |

Other relevant providers still use the disclosed four-hour assumption where no sufficient attributable visit sample exists. The separate explicit 120-minute verification request still returns two candidates; it is not the answer to the default question.

## Human review boundaries

All proposals in the final isolated snapshot remain deferred:

- Three provider-link proposals, including the calendar/spreadsheet links.
- Three field-correction proposals: the two endpoints of the wrong-year job and the transposed house number.
- 277 ambiguous property-match proposals, down from 283 as deterministic address normalization removes six formatting/locality ambiguities.

No decision IDs were applied to field lineage. `J8OMKP` retains a disputed appointment start, and the spreadsheet entry remains attached to house number 5832. Street misspellings, uncertain dates, ambiguous contacts, and unsupported service meanings were not auto-corrected. Provider, job, and visit source-to-canonical identity mappings are unchanged.

The local [review export](../artifacts/normalization-fixes/reconciliation-review.json) is an inspection artifact for this isolated snapshot; it contains no approvals. Existing operational review files and all 176 source files retain their original hashes.

## Verification and receipts

- **162 tests pass**, including 30 new classification/address regression cases. They cover wrong-category collisions, clear aliases, conflicting context, compound completion attribution, exact-property query behavior, apartment separation, out-of-area addresses, malformed locality fields, and preservation of unknown work.
- The discovery regression now expects ten complete-property Abrams calendar/CRM matches instead of nine. The additional match is the exact four-part address repaired here; no provider link was approved.
- Ruff passes and mypy passes for all 22 source modules.
- Independent source-fact/history verification passes with the original 969 aggregate, four Belmont jobs, four block visits, and 262 Lone Star jobs.
- Real stdio MCP verification passes all six tools, direct-query parity, five invalid-request/privacy checks, unchanged database state, and clean shutdown/scratch cleanup.
- Pack-level comparison checks integrity/foreign keys, stable source and entity counts, stable provider/job/visit crosswalks, corrected labels, unresolved factual corrections, and unchanged input/review hashes.

Primary local receipts:

- [Before MCP answers](../artifacts/normalization-fixes/before/answers.json).
- [After MCP answers](../artifacts/normalization-fixes/after-corrected/answers.json).
- [Machine-readable comparison](../artifacts/normalization-fixes/comparison.json).
- [Final MCP verification](../artifacts/normalization-fixes/protocol-final/summary.json).
- [Full tests](../artifacts/normalization-fixes/tests-verified.log).

The intermediate `after`, `after-final`, and `after-verified` captures are investigation iterations; the report above uses **after-corrected**. Captures are deterministic tool-response comparisons, not a newly generated AI demo video.

To repeat the comparison with the retained snapshots:

```sh
.venv/bin/python scripts/verify_normalization_fixes.py --evidence artifacts/normalization-fixes
```

To capture any new isolated snapshot through the actual MCP server:

```sh
.venv/bin/python scripts/capture_required_answers.py --database PATH_TO_SCRATCH_SNAPSHOT --output NEW_EVIDENCE_DIRECTORY
```

The changed normalization takes effect when a snapshot is re-imported. Restart an existing MCP process after deploying code changes. This task deliberately leaves the running snapshot untouched; the rebuilt comparison snapshot is `artifacts/normalization-fixes/after.sqlite`. No schema migration, network service, source write-back, or automatic human-review approval was introduced.

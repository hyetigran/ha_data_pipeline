# Expanded trap investigation — October 27, 2026

**Follow-up:** the user subsequently authorized the confirmed classification and address repairs. [The implementation and six-answer comparison](normalization-fixes-2026-10-27.md) records the fixes and remaining review boundaries. Counts below describe the pre-fix audit.

We have concrete evidence for all six examples named in the supplied grader excerpt, plus additional pitfalls and current implementation defects. **We cannot verify “22/22.”** The private seed manifest/crosswalk is unavailable. Our register IDs describe observed families; they are not grader seed IDs. Several observations can come from one seed, and ordinary synthetic variation can look like a trap.

This follow-up expands the [original register](trap-register.md). It reads all six source families and the street reference, imports a fresh isolated snapshot with no review approvals, and checks the current P1–P4 implementation. It does not change source data, the running database, production code, or review decisions. API/mock format differences from the separate vendor-schema investigation are not counted as hidden seeds.

The audit date is October 27. Temporal checks use the pack's explicit analytical snapshot, November 2, 2026 at 06:00 UTC, rather than the computer clock.

## Findings that change our understanding

### T31 — Service synonyms are not sufficiently normalized

**Confirmed implementation gap; high confidence.** The raw scan finds 68 distinct job labels with at least one unmapped component. In the fresh canonical snapshot, 3,651 jobs have an unknown service component; 3,576 have only unknown services. Of the latter, 2,165 have completion evidence. These counts describe jobs, not seeds.

Examples:

| Source locator | Raw label | Current canonical result |
| --- | --- | --- |
| Workiz `lone_star_plumbing/jobs.json`, `/data/77`, job `J0Y6Q7` | `WH replace` | Plumbing trade, unknown service |
| Workiz `uptown_odd_jobs/jobs.json`, `/data/86`, job `DY127B` | `assemble IKEA` | Handyman trade, unknown service |
| Workiz `white_rock_handyman/jobs.json`, `/data/158`, job `DBDMNP` | `Hang TV + hide wires` | Handyman trade, unknown service |

Other labels include `Tankless conversion`, `EV charger install`, `Hydro jet`, `fridge not cooling`, and `tv install 65in`. Some are clear aliases; others such as `changeout` require provider/trade context. Splitting `Patch & paint drywall` also creates an unknown `Patch` component alongside a recognized painting component. Therefore 68 labels does not mean 68 completely unclassified services.

**Impact:** service-specific history and recommendations can miss relevant completed work. Broad provider trade credit can survive while precise service credit is missing. `unmapped_service` is recorded, but that is not equivalent to solving the query.

**Needed:** a small reviewed, trade-aware alias vocabulary and pack-derived positive/negative query tests. Do not infer every ambiguous phrase from keywords alone.

### T32 — Keyword precedence misclassifies gutter cleaning

**Confirmed implementation bug; high confidence.** Five label variants representing **134 Workiz jobs** at Clear Flow Gutters map to `cleaning`, not `gutters`. They include `Gutter clean out`, `Gutter cleaning`, and `gutters cleaned`. Seventy-two of those jobs have completion evidence in the fresh snapshot.

Evidence: `sources/workiz/clear_flow_gutters/jobs.json`, `/data/0`, `/data/17`, `/data/6`, `/data/3`, and `/data/4`. The last example is job `XEERUP`. `privacy.service()` checks the generic `clean` token before the `gutter` token; projection then assigns the cleaning trade too.

**Impact:** gutter experience is undercounted and general-cleaning experience is wrongly attributed. Existing ingestion and query tests pass despite this defect.

**Needed:** prioritize specific service phrases, validate against provider context, and test the resulting history/ranking behavior. This audit documents the defect without changing the classifier.

### T33 — Customer name fields can disagree while contact identity agrees

**Confirmed source inconsistency; correction remains a candidate.** The scan finds 478 Workiz account/ClientId groups with multiple raw contact versions. In 362, phone/email normalization and names leave no differing values under the checked fields; much of the original conflict count is formatting or missing-data noise. The other **116 groups have differing name tuples**. None of the 478 groups has multiple nonempty normalized phones or emails under this check.

There are also **241 job rows** where nonempty `FirstName` equals `LastName`, across 233 account/ClientId groups. This pattern alone is not proof of corruption. Cross-record disagreement is stronger evidence: Bright Line Electric ClientId `5004`, jobs `6PRZI3`, `MDE9VG`, `RVA1BL`, and `CCUK39`, alternates a full name with a repeated given-name token. ClientId `5005` alternates a full name with a repeated surname token. Homeowner names and contact values are omitted here.

**Handled:** raw assertions are preserved without last-write-wins overwrites.

**Needed:** distinguish presentation variants, omissions, and actual name conflicts. Do not merge properties merely because contacts agree, and do not treat every `conflicting_customer_assertions` issue as a distinct person or hidden trap.

### T34 — Address parsing loses city and unit information in valid-looking strings

**Confirmed parser limitations; high confidence.** All **24 distinct CSV jobs** whose address ends with an unseparated ` dallas` remain ungeocoded. Examples are physical rows 15, 27, 32, and 181. The parser includes the city word in the street name rather than recognizing it as locality text.

Abrams calendar `VEVENT:2` has a four-part address shaped as `street, unit, city, state ZIP`. The current three-part parser treats the unit as the city and loses the actual locality. The matching HCP job is `sources/housecall_pro/abrams_plumbing/jobs_page_1.json`, `/jobs/32`; its structured address preserves the unit and ZIP+4. Both records have the same interval. This is a distinct concern from safely keeping different apartment units separate.

The broader contact/address search also finds `Cottonwood Trail` versus `Cottonwood Trl`, an abbreviation absent from the current suffix table. These locations are outside the supplied geocoder's target area; normalizing the suffix would not manufacture coordinates there.

**Needed:** narrow parsing rules for trailing city and four-part addresses, with unit-preservation tests. Keep address identity and geocoding coverage separate.

## Expanded evidence for existing register entries

| Existing entry | New evidence | Interpretation and current boundary |
| --- | --- | --- |
| T02 wrong year | A broad scan of 14,823 job-visit intervals finds one completed visit scheduled after the snapshot and one Done record updated before its appointment: the same `J8OMKP` at Workiz Lakewood Air `/data/101`. | Confirms the existing candidate without selecting its ID in the discovery algorithm. The inferred 2025 correction still requires review. |
| T03 DST | Independent timestamp parsing checks 65,956 ISO-like JSON strings and finds nine ambiguous fields: the known HCP appointment's three repeated-hour fields, plus six Workiz metadata fields. | The extra six are four `LastStatusUpdate` and two `CreatedDate` values, all on Pending jobs. They do **not** make those jobs' later appointment intervals ambiguous. Metadata is retained but lacks comprehensive ambiguity reporting. |
| T05 transposed house number | General same-contact, same-street/unit, two-digit-swap search finds one distinct address-pair candidate: 5823/5832 Belmont, connecting Fresh Nest job `/data/jobs/nodes/36` to CSV row 175. | No hardcoded house number is used by the new discovery scan. The production correction proposal remains specifically tailored to the previously investigated case. Shared contact alone is not correction authority. |
| T09–T11 address variants | 121 unresolved address assertions have close reference-street candidates: 38 Jobber, 36 HCP, 32 Workiz, 12 spreadsheet, 3 calendar. A separate contact/house-number search finds 135 street-variant pairs. | This replaces the old discovery limit of checking only `Siwss` and `Merceeds`. Counts overlap and include parsing/abbreviation cases. Fuzzy resemblance is a candidate generator, not an approved merge. |
| T13–T14 missing CSV dates/times | 16 Ray calendar occurrences have plausible CSV matches using month/day plus customer-label or house-number evidence. | Examples: row 193's `10/30` matches a 2026-10-30 11:15–12:15 event; row 188's missing time matches a 2026-10-05 10:15–14:15 event; row 205's missing time matches a 2026-11-10 11:00–12:00 event. Candidate strength differs; surname-only matches are weaker. Calendar scheduling does not prove completion. |
| T15 reschedules | 403 CRM free-text fields mention rescheduling: 132 Jobber instructions, 178 HCP notes, 93 Workiz notes, in addition to eight unique CSV jobs. | The earlier register emphasized CSV only. These fields are retained, but replacement relationships are not extracted. A textual old date must not become an additional booking. |
| T16 jobs/visits | 78 Jobber jobs have mixed visit statuses; 95 recurring jobs already contain explicit visits. | Parent status is not the status of every visit. Do not expand CRM recurrence descriptions on top of exported visits and double-book them. Calendar recurrence is separately expanded by P3. |
| T17 estimates | 357 raw job observations reference an estimate, representing **356 unique jobs**. All 356 referenced estimates exist in the same account and agree on customer and property. One observation repeats at a page boundary. | Converted estimate and resulting job are separate entities, not two completed services. Completed-status estimates include declined/unapproved options. Current history excludes estimates. |
| T25 calendar/provider linkage | **36 Abrams calendar job occurrences match HCP start and end exactly; nine also match the complete normalized property key.** Sixteen Ray occurrences have plausible CSV matches. | Stronger evidence than a similar provider name. It supports reviewing existing provider-link proposals, not silently approving them. Among 28 Abrams matches with locations, 15 differ only in city labels; four have additional parsing/spelling differences. |
| T30 contact conflict count | The old 1,076 conflicting customer assertions represent 478 account/ClientId groups, not 1,076 people or traps. | See T33. Use normalized contacts and retain contradictory names. |

Additional DST locators, all relative to `sources/workiz/`:

| File | Locator | Job ID |
| --- | --- | --- |
| `clear_flow_gutters/jobs.json` | `/data/217/LastStatusUpdate` | `KLDQVE` |
| `cut_above_lawn/jobs.json` | `/data/269/LastStatusUpdate` | `Q44CML` |
| `fix_it_right_appliance/jobs.json` | `/data/278/LastStatusUpdate` | `G2Q27Y` |
| `lakewood_air/jobs.json` | `/data/280/LastStatusUpdate` | `U03IVT` |
| `lakewood_air/jobs.json` | `/data/296/CreatedDate` | `9EWHXB` |
| `overhead_hero_garage_doors/jobs.json` | `/data/267/CreatedDate` | `V70V6N` |

## Current coverage of the original register

This table updates the original P2-era handling assessment. Passing tests establish the stated behavior, not hidden-answer correctness.

| Register IDs | Current coverage | Remaining gap |
| --- | --- | --- |
| T01, T07, T08 provider identity | Phone-plus-trade links; rename and cross-CRM identity preserved; similar names alone do not merge. | No independent grader crosswalk to certify every identity. |
| T02, T05 factual corrections | Source conflict preserved; local review supports paired time correction and address correction. | Still unapproved in this audit's fresh snapshot. |
| T03, T19, T21 time ambiguity | Ambiguous visit instants are rejected; incomplete intervals create uncertainty; zone-aware arithmetic tested. | Additional metadata fields identified above need explicit quality reporting. |
| T04, T22–T24 calendars | P3 supports exclusive all-day blocks, bounded recurrence, opaque tentative holds, transparent events, and unlocated busy time. | Real calendar-to-profile links still need review. Correct interval logic cannot compensate for an unresolved provider identity. |
| T06, T12 duplicate imports | Exact HCP page overlap and CSV duplicate rows deduplicate while retaining observations. | Fuzzy/changed-ID duplicates remain candidates. |
| T09–T11 properties | Basic suffix/case/ZIP/unit normalization and reference interpolation work; missing units do not justify merging with known units. | Broad spelling candidates and T34 parsing failures remain unresolved. |
| T13–T15 spreadsheet uncertainty | Ambiguous dates, missing ends, cancellation, and payment-versus-completion distinctions remain explicit. | Calendar-backed correction proposals, service mismatches, and replacement relationships need review/work. |
| T16–T18 lifecycle | Jobs, visits, estimates and completion evidence are separate; pending approval is not completed work; scheduled estimates occupy time. | Vocabulary coverage for performed service remains weak (T31/T32). |
| T20 money | 11,616 nonempty unique job amounts independently recomputed with Decimal; all agree with adapter minor units. | This check does not cover every estimate option, balance, or visit invoice field. |
| T25 provider links | Three provider-match proposals remain; fresh snapshot has 43 canonical providers. | New calendar corroboration has not been added to the operational review proposals. |
| T26 hours | Four M-F shorthand declarations remain unparsed; emergency-only hours do not become routine 24/7 availability. | Conservative unknown availability is safe but loses useful answers. |
| T27 exclusions | Explicit trade exclusions precede ranking; tested. | Service classification must also be correct. |
| T28 coverage | Out-of-target-area bookings remain occupancy; declared versus observed service areas are separate. | Missing reference coverage does not prove an invalid address or no experience. |
| T29 crews | Provider-level union prevents inferred capacity from crew counts. | Per-worker capacity and travel remain unmodeled. |
| T30 PII | MCP fields/errors are allowlisted and privacy tests pass. | Production authorization remains separate scope; raw audit receipts stay private. |

## Searches that did not establish another trap

- **26 same-business, normalized-property, UTC-date groups contain distinct jobs**, but none crosses source accounts in this search. Different services, times, cancellations, and repeat visits are reasons not to merge blindly. These are candidates, not 26 confirmed duplicate jobs. This search still depends on known business phones and normalizable addresses.
- The interval scan found no nonpositive complete raw intervals, no completion timestamps after the snapshot, and no cancelled visits carrying completion timestamps in its selected CRM fields.
- 109 visits have a completion timestamp on a different UTC date from their scheduled start. This is not automatically an error: completion may be recorded later and local calendar dates can differ from UTC dates.
- Another 141 unresolved addresses lack a close reference candidate under the search threshold. Many are out-of-area streets with absent ZIPs; do not label all of them misspellings.
- All 176 pack file hashes match the original audit. No extra source or private grader file was used.

## Verification and reproducibility

The existing full suite passed **129 tests** before adding investigation tests. The suite then passed **132 tests**, including three new tests for the independent DST parser, generalized anomaly discovery, money checks, and candidate-only calendar comparisons. Ruff passes on the new script and tests. The existing wrong-year and transposition verification script also passes. Passing these checks does not resolve the newly reported service bugs.

The new [discovery script](../scripts/investigate_traps.py) uses independent raw timestamp parsing, an independent Decimal recomputation, and existing adapters/address/service helpers for comparison. The latter checks are not an independent truth oracle. It scans all JSON files but only ISO-like timestamp strings; CSV date candidates use explicit supported formats, and calendar matching is deliberately conservative.

Reproduce in a new scratch directory:

```sh
mkdir -p artifacts/trap-audit-new
.venv/bin/python scripts/audit_traps.py > artifacts/trap-audit-new/baseline.json
.venv/bin/python -m house_account.cli ingest --data data --database artifacts/trap-audit-new/snapshot.sqlite --ledger artifacts/trap-audit-new/no-decisions.jsonl > artifacts/trap-audit-new/import.json
.venv/bin/python scripts/investigate_traps.py --database artifacts/trap-audit-new/snapshot.sqlite > artifacts/trap-audit-new/discovery.json
.venv/bin/python scripts/verify_trap_candidates.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check scripts/investigate_traps.py tests/test_trap_discovery.py
```

Use a genuinely new directory so an existing review ledger is not mistaken for the no-approvals baseline. The discovery script opens the optional database read-only. Full local receipts are in `artifacts/trap-audit-2026-10-27/`. The [tracked summary](trap-discovery-summary.json) retains counts and sampled locators without homeowner contacts or personal calendar titles.

## Work order suggested by the evidence

1. Repair T32's specific misclassification and add query-level regression coverage. Expand T31's clear service aliases with provider context and negative cases.
2. Fix T34's narrowly identified address parsing cases. Generate evidence-backed street corrections from the broader candidate set; do not auto-approve them.
3. Present the new Abrams/Ray corroboration through the existing local review workflow. Then resolve supported date/time/address fields without treating calendar presence as completion.
4. Reduce contact-format review noise and flag actual name contradictions separately. Report ambiguous metadata timestamps without incorrectly blocking unrelated future appointments.
5. Re-run the six required questions and availability checks after any approved changes. Compare corrected answers with the unreviewed baseline.

The missing grader crosswalk is the remaining limit on proving every one of the 22 seeds. This investigation produces inspectable evidence and a concrete defect list, not an invented completion score.

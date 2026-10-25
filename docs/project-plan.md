# Delivery status and acceptance requirements

This reference replaces the original execution checklist. It records the phase boundaries, accepted requirements, and evidence locations. The original two-day schedule was a planning estimate, not a current completion promise.

## Phase status

| Phase | Delivered behavior | Evidence |
| --- | --- | --- |
| P1 | Six-source import, normalization, source accounting, and failure handling. | [P1 execution record](p1-execution.md). |
| P2 | Canonical identities, history queries, and local reconciliation review. | [P2 execution record](p2-execution.md). |
| P2R | Relational schema, explicit completion evidence, persistent identity, and transactional publication. | [P2R execution record](p2r-execution.md). |
| P3 | Candidate openings and provider recommendations. Merged in PR #3. | [P3 execution record](p3-execution.md). |
| P4 | Six read-only MCP tools and the actual Codex demo. Merged in PR #4. | [P4 execution record](p4-execution.md). |

All phases are implemented. Production synchronization, remote authorization, crew scheduling, travel optimization, and a seventh-source parser remain deferred.

## Acceptance boundaries

The project uses the supplied private pack and a local persistent SQLite database. Original observations and review decisions remain traceable. A technical implementation does not approve an inferred correction.

Each phase requires unit tests, actual CLI or protocol behavior, relevant performance checks, and independent review. Tests alone do not establish the connected-agent result. Evidence remains in ignored `artifacts/P1/` through `artifacts/P4/` directories.

The original plan specified ten verification scenarios per phase. Execution records distinguish separate runs from indexes that refer to shared receipts. Local CLI and stdio checks replaced unavailable cloud and control tooling. No unavailable screenshot or cross-model review is claimed.

## Ingest all sources into a traceable model (P1)

P1 requirements cover the following behaviors.

- Separate adapters parse Jobber, Housecall Pro, Workiz, the spreadsheet, calendars, and profiles. The street reference remains a separate input.
- Account-scoped source identities distinguish records. Exact repeats retain occurrence evidence without duplicating the entity.
- Jobs, estimates, and visits remain separate. Completed estimates do not establish service history.
- Source statuses, unknown dates, missing durations, amounts, and provenance survive normalization.
- Imports validate a candidate before publication. Invalid input preserves the previous successful snapshot.

The ten original scenarios cover accounting, nested visits, estimates, repeated pages, uncertain spreadsheet values, cancellations, exact amounts, repeat import, injected failure, and provenance.

The proposed import targets were 60 seconds and 512 MiB on the supplied pack. Historical measurements and machine details remain in the P1 record.

## Resolve identities and answer history questions (P2)

P2 requirements cover supported provider matches, address normalization, conservative job reconciliation, source lineage, and four history queries.

Automatic provider matching requires corroboration. Similar names alone do not establish one business. Exact-address matching preserves units. Approximate coordinates support radius history, not travel time.

Human review supports approve, reject, defer, preview, repeated application, supersession, and stale-evidence rejection. Real wrong-year and house-number corrections remain deferred until approved. Private review material never becomes an ordinary tool response.

The ten acceptance lanes cover source-supported identity and history answers, exact-home boundaries, address units, radius limits, review outcomes, reversal, failure handling, privacy, and provenance. The P2 execution record identifies the actual receipts and original counts.

## Implement the relational redesign (P2R)

P2R requirements preserve original and normalized source assertions while replacing canonical document scans with relational facts.

The accepted design separates job lifecycle from performed service, supports several services per job, and retains explicit temporal uncertainty. SQL enforces visit parents and controlled values. Persistent identity survives imports, merges, and splits.

Migration preserves prior memberships, source accounting, review semantics, and recoverable backups. Intended answer changes remain documented. The radius count changed from 971 to 969 service-attributed job counts because two combined-service completions lacked specific attribution.

The proposed targets were 60 seconds and 512 MiB for import and 500 ms p95 for history queries. The execution record reports measurements without treating changed semantics as an identical-work speedup.

## Compute defensible openings and provider rankings (P3)

P3 uses declared routine hours minus the union of active visits, scheduled estimates, blocking calendar occurrences, and uncertain periods. Missing evidence does not establish free time.

The ten scenarios cover the following cases.

1. Preserved prior scheduling facts and openings outside occupied intervals.
2. Continuous two-hour candidates in the next three days.
3. Out-of-area work that still consumes time.
4. Abrams' November 4 through November 8 vacation.
5. A cancelled recurring instance in an isolated fixture.
6. An ambiguous November 1 local timestamp.
7. Crew declarations without established independent capacity.
8. Emergency-only or missing hours.
9. Water-heater eligibility, duration, and score evidence.
10. Deterministic openings, transparent events, tentative holds, and estimate appointments.

The supplied schedules end at December 3, 2026, Chicago midnight, exclusive. The fixed reference date is November 2. Travel remains unmodeled. Confidence is ordinal, not calibrated probability.

The proposed performance targets were one second per query and 512 MiB. The P3 parent had no comparable availability operation. The current maintenance wrapper preserves the original P3 row-comparison failure and separately checks P4's added fields.

## Expose the tools and deliver the six-question demo (P4)

P4 requires typed inputs, bounded outputs, useful safe errors, and read-only stdio tools. Startup can import missing derived state. Tool calls cannot import data, approve decisions, execute SQL, or read arbitrary files.

| Tool | Acceptance result |
| --- | --- |
| `search_service_history` | Q1 groups completed work by provider and trade within half a mile over 24 months. Neighboring exact addresses remain hidden. |
| `find_available_providers` | Q2 combines completed handyman history in 75214 with a continuous two-hour candidate. |
| `get_block_schedule` | Q3 lists active appointments on the 4500 block of Live Oak St for fourteen days. |
| `get_provider_profile` | Q4 resolves Lone Star or reports ambiguity, then returns history, coverage, trades, and three candidate openings. |
| `get_property_history` | Q5 returns who performed what work and when at the supplied Belmont address. |
| `recommend_provider` | Q6 explains eligibility, scores, exclusions, evidence, and duration for water-heater work near 75206. |

For the initial definition of near a postal code, declared coverage or observed completed work in that postal code establishes area eligibility. No invented centroid or radius is required.

The ten lanes cover prior-query compatibility, each of the six actual agent questions, invalid or hostile input, private-data exclusion, and fresh startup with source preservation.

The deliverables include setup instructions, a one-to-two-page model explanation, decisions, an AI-use note, and a video no longer than five minutes. A real weak answer and its cause remain part of the demo evidence.

The original targets were one second p95 per warm tool call, 60 seconds for first import and startup, and 512 MiB. Thirty warm calls per tool exclude agent latency. The parent had no MCP transport, so no speedup ratio applies.

## Fixed time windows

All windows include the start and exclude the end in `America/Chicago`.

| Phrase | Window relative to November 2, 2026 |
| --- | --- |
| Last 24 months | November 2, 2024 through November 2, 2026. |
| Next three days | November 2 through November 5. |
| Next fourteen days | November 2 through November 16. |
| This week | November 2 through November 9. |
| Supplied schedule coverage | November 2 through December 3. |

Actual ingestion time remains separate from the fixed challenge date and source coverage.

## Open limits

The hidden grader crosswalk is unavailable. Evidence for the six named examples does not establish that all 22 hidden traps were found.

Approximate geocodes, incomplete durations, uncertain timestamps, unresolved identities, and unverified worker capacity limit answers. Exact-home history has no production ownership authorization. Private text remains excluded from public fields and errors.

At larger scale, the workload includes record volume, recurrence density, concurrent reads, and refresh cost. Production design requires measurements and the [accepted synchronization contracts](sync-readiness.md).

## Related records

The following documents define the detailed contracts.

- [Challenge requirements](../gauntlet-challenge-requirements.md) retain the six question texts and evaluation weights.
- [Data model](data-model.md) explains entities, evidence, and privacy.
- [Command reference](command-reference.md) defines current operations and response meanings.
- [Scheduling policy](p3-design.md) defines duration, confidence, and ranking formulas.
- [Decisions](decisions.md) preserve authorization history and rejected alternatives.
- [Verification guide](verify-local-system.md) provides current reproduction commands.

The old checklist counter in `plan-validation.txt` is a captured result for the original planning format. It is not a validation of this revised reference.

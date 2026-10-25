# Availability and recommendation policy

P3 derives candidate openings from the published P2R facts. P3 does not book work or implement production synchronization. P4 later exposes these calculations through MCP tools.

## Domain and ownership

`time_policy.py` owns aware UTC intervals, local-time validation, bounded request windows, interval union, and subtraction. `availability.py` reads working-hour declarations, appointments, and calendar definitions, then calculates free and unknown periods. `ranking.py` applies eligibility and scores supported evidence. All parts of one answer read the same SQLite transaction.

An opening is a continuous interval within confirmed routine working hours after occupied and uncertain time is removed. A result can have known availability with no sufficient opening, partial availability with some unknown periods, or unknown availability. These states are distinct.

The reference instant is November 2, 2026 at midnight in America/Chicago. The supplied schedules cover December 2, so their exclusive coverage endpoint is December 3 at midnight in that timezone. Queries never infer free time beyond that coverage. Actual ingestion time remains separate from this challenge reference date.

## Evidence rules

Active job visits and scheduled estimate appointments occupy provider time even when the property has no geocode or lies outside the target postal codes. Calendar recurrence expands only within a bounded window. Cancelled occurrences and transparent events do not block time. Opaque tentative holds and all-day vacations do. All-day end dates are exclusive.

Working-hour declarations retain their timezone, effective dates, and emergency qualifier. Missing weekdays remain unknown. An emergency-only declaration does not establish routine hours. Uncertain appointment times remove the affected period from defensible openings. Duplicate and overlapping occupancy is unioned rather than subtracted repeatedly.

Assignments and crew sizes remain evidence, not verified independently schedulable resources. The calculation uses one provider-level timeline. Travel remains unmodeled, so an opening is a calendar candidate and never a booking promise.

Rankings require supported service capability without an explicit exclusion, declared or observed target-area coverage, and an opening long enough for the selected duration. Relevant work uses completion-service attribution rather than job lifecycle or estimate status. Ranking components total at most 100 points, with up to 40 for relevant completed work, 20 for area evidence, 25 for opening suitability, and 15 for confidence. Provider ID breaks ties deterministically.

A caller-supplied duration takes precedence. Historical scheduled durations are usable only when supported by relevant completed visits, and remain estimates rather than measured work time. When evidence is insufficient, water-heater recommendations disclose a provisional four-hour demo assumption.

Responses expose business labels, fixed reason codes, and opaque evidence references. They do not expose customer contacts, calendar titles, assignment names, raw source text, or unrelated property addresses.

## Design choice

Two independent explorations compared a query-driven per-provider calculation with a provider evidence bundle and pure interval calculator. The selected design combines the small connection-taking query boundary with explicit working, busy, and unknown interval collections. An independent judge endorsed it with safeguards for recurrence limits, uncertain endpoints, and same-snapshot reads.

No new database schema, repository class, persistent opening cache, worker-capacity model, or production-sync framework is needed. The existing stored evidence is sufficient for the bounded local feature. Separate unknown intervals keep missing evidence from appearing as free time. Real CLI checks supplement the unit tests.

## Confidence and ranking formulas

Availability confidence starts at 80 to reflect conservative capacity and unmodeled travel. Unknown availability scores zero. Otherwise, the score loses 25 points for unknown periods and 15 for disagreement between calendar and CRM intervals. An overlapping tentative hold costs 5 points. Limited source freshness and undated unbooked backlog each cost 10 points. The minimum is zero. Scores of at least 75 are high, 50 through 74 are moderate, and lower scores are low. Unknown availability has its own label. These thresholds describe this demo policy rather than measured reliability.

Freshness compares source evidence with the fixed reference date, not the requested future appointment date or the machine clock. An unresolved undated backlog does not automatically occupy the entire horizon. Scheduled work whose timing cannot be bounded can make the horizon unknown.

Relevant-work points are four per distinct completed job with supported service attribution, capped at 40. Area points are 20 for both declared and observed coverage, 15 for observed coverage alone, or 10 for declared coverage alone. Opening-fit points are 25 times the fraction of the requested horizon remaining at the first feasible opening. Confidence points are 15 times the availability score divided by 100. Fractional components round to two decimals. Canonical provider ID breaks ties.

Historical duration estimation requires at least three distinct completed visits with positive, known scheduled endpoints and a single attributed service. It uses the rounded-up median scheduled duration and explicitly labels that evidence. It is not a measured hands-on-work duration. Without enough evidence, the four-hour fallback remains a disclosed demo assumption. Schedule-based exclusions carry the same duration explanation as eligible results.

## Unresolved identity links

The supplied 40 profiles reconcile to 43 canonical provider identities because ambiguous calendar and spreadsheet links remain separate. P3 does not approve those links or reinterpret names as identity proof. In the unreviewed pack, Ray and Abrams cannot provide routine candidate openings from their calendar evidence alone. Verification separately imports their observed calendar definitions into isolated known-hours fixtures to test blocking semantics without approving real merges.

# P3 execution record

P3 implements local candidate availability and provider ranking on the merged P2R model. The parent is `c6c151ee3e95706ad178d2d661fc791f6106f616`. Work remains on `codex/p3-availability`. P4, publication, merging, travel optimization, and production synchronization are outside this run.

## Delivered behavior

The CLI adds `query openings`, `query available`, and `query recommend`. Provider summaries now include three candidate openings and their availability state. Names resolve only when a single canonical business matches. Invalid durations, excessive horizons, unsupported services, and incompatible CLI options fail without modifying data.

The interval engine uses declared routine hours and subtracts the union of active visits, estimates, and opaque calendar occurrences. It preserves unknown periods, exclusive all-day boundaries, recurrence overrides and cancellations, timezone uncertainty, and out-of-area occupancy. Explicit exclusions precede ranking. Scores, duration assumptions, evidence, and rejected candidates remain visible.

No schema migration or new external service was needed. The three product modules own time policy, availability, and ranking. The [design document](p3-design.md) records the selected structure and formulas.

## Verification

- The full suite passes 95 tests, including 21 new availability/ranking tests. Ruff and mypy pass, with 20 source files checked.
- All ten live CLI lanes pass on the final source. Receipts are in `artifacts/P3/final-live-3/`, including `live-summary.json` and individual lane files.
- The live verifier compares parent/current scheduled visits and checks new openings against independently read occupancy. An independent minute-grid calculation checks the ranking result without reusing the production interval algorithm.
- The updated maintenance history journey also passes and confirms scratch removal. Its evidence is in `artifacts/verification/history-nm84gfyi/`.
- The P2 independent history checks preserve four Belmont completed jobs, four active Live Oak visits, 262 completed Lone Star jobs, and 969 radius provider/trade job counts. Privacy checks pass.
- The verifier confirms all 176 supplied source files are unchanged, queries preserve logical database contents, and temporary scratch state is removed.
- Independent product review passes with notes. Its final seven-file aggregate SHA-256 is `634e44d192c1305cb6a83570c2370a3ef96c64f9e6fd3631fd87d3306f6a6254`. The receipt is `artifacts/P3/independent-product-review.json`.

Independent review reproduced and resolved floating-calendar horizon filtering, all-day evening-window filtering, timezone-specific working weekdays, duration disclosure on rejected recommendations, and out-of-window tentative/DST effects. A coordinator check also caught calendar intervals being merged before agreement classification. The final regression preserves individual corroborating intervals while still unioning busy time for subtraction.

## Observed answers and limitations

The supplied unreviewed pack returns three handymen with relevant 75214 history and continuous two-hour candidates in the next three days. Lone Star's first three two-hour candidate gaps start November 17, 18, and 20. Independent occupancy checks establish that earlier working-day gaps are too short.

The default water-heater recommendation for 75206 this week returns no eligible provider. An independent optimistic calculation, even before calendar and uncertainty deductions, finds insufficient gaps. An explicit 120-minute request returns two eligible providers. That is a different duration request, not a silent fallback. Rejected candidates disclose their requested or inferred duration.

The 40 profiles produce 43 canonical identities because ambiguous calendar and spreadsheet links remain separate. Actual Ray and Abrams answers retain unknown availability. Their observed calendar definitions are additionally imported into isolated known-hours fixtures for non-vacuous vacation, tentative-hold, and transparency checks. Those fixtures do not approve real identity proposals. Real-pack cross-source agreement is not asserted across unresolved links; corroboration/conflict classification has isolated behavioral coverage.

CLI transcripts replace supplementary terminal screenshots because screenshot capture was unavailable. The requested Cursor-specific model families, agent types, and specialized Comment Sicko check were unavailable. Available local independent agents supplied design exploration, review, and live verification. Manual review found no new comment or suppression issues. No unavailable specialized check is represented as having run.

Working-hour omissions, unknown durations, uncertain dates, conservative capacity, and unmodeled travel remain explicit limitations. The result is a candidate schedule under supplied coverage, not a booking guarantee. There is no claim of finding all 22 hidden traps or implementing continuous sync.

## Scope and documentation

Current status text now reflects implemented persistent SQLite publication and stable identity. Historical decision entries retain their decision-time meaning. The project verification map includes P3 and its isolated CLI journey. Existing deferred factual corrections remain deferred.

P4's MCP server, client configuration, connected-agent responses, and demo video have not been implemented. No code was published or merged by this run.


## Performance

The final benchmark runs one warmup and 30 measured rounds over a 30-day window for every one of the 43 canonical providers, plus availability search and recommendation. Each timed operation opens its read transaction and serializes the complete answer. All response hashes are deterministic and no operation errors. The parent has no availability/ranking operation, so there is no comparable baseline or speedup claim.

The largest p95 is 142.5 ms for availability search. Ranking p95 is 128.4 ms. Peak process memory is 148.2 MiB. These pass the 1-second and 512-MiB budgets. Availability samples range from 133.3 to 156.9 ms; ranking samples range from 115.2 to 129.2 ms. Machine and source hashes, sample counts, and per-provider results are retained in `artifacts/P3/benchmark-final.json`.

A separate excluded profiling run attributes most ranking time to SQLite queries and conversion of returned rows, followed by interval arithmetic. This is a local single-client measurement on the supplied pack, not a production-scale capacity claim. Profiling output is in `artifacts/P3/benchmark-final.profile.txt`.

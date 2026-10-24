# Build the home services MCP server plan

Deliver a local, read-only MCP server that answers the six homeowner questions with traceable evidence and explicit uncertainty.
Use four dependent changes, P1 through P4, over two working days.
Keep jobs separate from visits. Compute openings from working hours, occupied visits, and calendar blocks.
Treat the data pack as the only source of customer facts.
The data pack is present under `data/`. Inspection found 176 files totaling 21,292,274 bytes. P1 ingestion is implemented. P2 through P4 remain unimplemented.
This document records the project plan. P1 execution results are in [the execution report](p1-execution.md). Later-stage paths and commands remain proposed.

## How to read this

One box is one unit of work. Every box names the evidence that checks it. Check a box only when its evidence exists. Keep logs under `artifacts/P1/` through `artifacts/P4/`.

Use `/Users/tig/.codex/skills/pstack/poteto-mode/playbooks/autopilot-stack.md` as the execution playbook. P1, P2, P3, and P4 form one dependent stack. The operator owns landing. Planning does not authorize implementation, publication, scheduling, or merging.

Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

Read the execution checklist in order. Appendices record design choices, the data model, tool contracts, and limitations.

## Program checklist

### Arm the program

- [x] The operator authorized P1 only. Record the request in `docs/decisions.md`. Stop before P2 and do not publish or merge.
- [x] Inspect the supplied pack. Save counts, status vocabularies, pagination checks, and all 176 file hashes in `docs/data-pack-inventory.json`. Reproduce with `python3 scripts/inspect_data_pack.py`.
- [ ] Re-run the inventory at P1 start and compare hashes before using the recorded findings. Save date-range and reference-integrity checks in `artifacts/P1/inventory.json`.
- [ ] Establish a local Git baseline and record its SHA. Configure a remote only when the operator supplies a destination.
- [ ] Read the installed execution and verification skills. Once skill files exist on trunk, use `git show origin/main:<skill-path>` to re-read them. Do not assume this empty project already contains pstack.
- [ ] For a separately authorized unattended run, translate the playbook's `/loop 1h` audit into a Codex heartbeat. Save its ID. Do not create an automation during planning.
- [ ] During an authorized run, post a status message only for a completed stage, failure, changed decision, or missing input. Log evidence paths in `docs/decisions.md`.
- [ ] On a stop request, stop writers and record their current branches and pending checks.

### Spawn owners

- [ ] Assign P1 first, P2 after P1, P3 after P2, and P4 after P3. Save the owner and parent SHA in `docs/decisions.md`.
- [ ] Keep one writer on shared schema and dependency files. A later owner starts from its parent's verified result.
- [ ] Keep P1 in ingestion and storage, P2 in identity and queries, P3 in scheduling, and P4 in MCP and delivery. Record cross-stage edits before making them.
- [ ] Treat P2 and P4 as interaction review-gated. Keep every PR unmerged until the operator lands the stack.

### PR mechanics, for every PR

- [ ] When a remote exists, resolve the forge and record it. Prefer the connected GitHub tooling. Use `gh` if needed. Without a remote, retain local commits and mark publication pending.
- [ ] Open each PR against its parent branch. Attach each created PR to the chat. Save the URL and head SHA in the decision log.
- [ ] Run `uv run ruff check .`, `uv run mypy src`, and `uv run pytest` before the PR push. Preserve the results in the stage artifact directory.
- [ ] Read the available cleanup and review skills before committing and reviewing. Record unavailable tooling instead of claiming it ran.
- [ ] Resolve each review finding with a fix or evidence-backed dismissal. Save the final disposition in the decision log.

### Verdict and merge, for every PR

- [ ] At the final head, run the ten live scenarios below plus unit and performance checks. Use independent reviewers where available. Four available agent slots require batches.
- [ ] Audit privacy and provenance separately from functional correctness. Save both reviews and the exact head SHA.
- [ ] Re-run affected verification after any change. Require every scenario to pass before appending the PR to the stack.
- [ ] Check the parent SHA and mergeability before handoff. The operator lands the stack bottom-up. Do not auto-merge.

### Boot recipe, for every live lane

- [ ] Check out the exact head in an isolated directory with a separate temporary database. Save the SHA and fixture manifest.
- [ ] Use the Python MCP client over stdio for tool scenarios. Use the application CLI for ingestion scenarios. A future `scripts/verify.py` drives these commands and writes JSON transcripts.
- [ ] Keep logs on stderr and protocol traffic on stdout. Capture both streams separately.
- [ ] Run `uv run python scripts/verify.py --stage P1 --lane 1 --output artifacts/P1/lane-1.json`, substituting the stage and lane. This command is a planned implementation deliverable.
- [ ] Save authoritative JSON transcripts in each stage directory. Capture terminal screenshots as supplementary evidence when a terminal UI is available. Never substitute screenshots for assertions.
- [ ] Record unavailable cloud VMs or control skills in Appendix C. Use isolated local processes with the protocol client instead. Do not claim unavailable tooling was used.

## Ingest all sources into a traceable model (P1)

**Depends on.** None.

**Files.**

- [x] Create `pyproject.toml`.
- [x] Create `uv.lock`.
- [x] Create `src/house_account/model.py`.
- [x] Create `src/house_account/storage.py`.
- [x] Create `src/house_account/adapters/`.
- [x] Create `src/house_account/cli.py`.
- [x] Create `tests/test_ingestion.py`.
- [x] Create `scripts/verify.py`.
- [x] Create `scripts/benchmark.py`.

**Build.**

- [x] Pin Python and dependencies after a startup compatibility check. Use Python, SQLite, Pydantic, the official MCP SDK, pytest, and maintained ICS recurrence support. Save the result in the P1 change and its verification log.
- [x] Use the inspected source contracts in Appendix H. Keep each source parser in its own adapter. Register adapters without changing the normalizer. Save the result in the P1 change and its verification log.
- [x] Create the entities in Appendix E. Store raw source records and evidence separately from public response models. Save the result in the P1 change and its verification log.
- [x] Make each adapter emit validated source observations. Record accepted, rejected, duplicate, and unresolved counts with machine-readable reasons. Save the result in the P1 change and its verification log.
- [x] Handle 15 Jobber exports, 15 Housecall Pro accounts, 11 Workiz accounts, the CSV with its header on row 3, two calendars, and 40 profiles. Preserve source status and amount units before normalization. Save the result in the P1 change and its verification log.
- [x] Write a new SQLite snapshot transactionally. Use stable source keys and content hashes so a repeated full import preserves canonical counts. Keep old successful data after import failure. Save the result in the P1 change and its verification log.
- [x] Add foreign keys, source-key uniqueness, and indexes for provider, property, trade, status, and visit time. Keep estimates separate from completed jobs. Preserve scheduled estimate appointments as occupied time, with their own appointment kind. Save the result in the P1 change and its verification log.

**You see.**

- [x] The import report accounts for every input record across all six sources. A repeated import produces identical canonical counts and no duplicate source links. Save `artifacts/P1/summary.json`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [x] tests/test_ingestion.py covers nested visits, paged duplicates, cents, unknown status, blank fields, and rollback. Run `uv run pytest tests/test_ingestion.py`. Save `artifacts/P1/unit.log`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `inherit-parent` at the PR head, in batches within available concurrency.

- [x] Lane 1. Regression lane against trunk. Import the same small fixture at trunk and head. Record that trunk lacks ingestion when applicable. Save `artifacts/P1/lane-1.json` and a supplementary terminal screenshot when available. Pass when all six adapters run and every source record is accounted for.
- [x] Lane 2. Import a job with two visits. Save `artifacts/P1/lane-2.json` and a supplementary terminal screenshot when available. Pass when one job links to two distinct visits.
- [x] Lane 3. Import an estimate beside a completed job. Save `artifacts/P1/lane-3.json` and a supplementary terminal screenshot when available. Pass when the estimate never enters completed-job counts.
- [x] Lane 4. Repeat a page-boundary source record. Save `artifacts/P1/lane-4.json` and a supplementary terminal screenshot when available. Pass when one source entity remains with recorded duplicate evidence.
- [x] Lane 5. Import the real CSV after its two preamble rows, including relative dates and sparse fields. Save `artifacts/P1/lane-5.json` and a supplementary terminal screenshot when available. Pass when bad fields produce explicit issues without silent record loss.
- [x] Lane 6. Import a cancelled job. Save `artifacts/P1/lane-6.json` and a supplementary terminal screenshot when available. Pass when its raw status and canonical cancellation state remain traceable.
- [x] Lane 7. Import prices in cents. Save `artifacts/P1/lane-7.json` and a supplementary terminal screenshot when available. Pass when the integer minor-unit amount and currency remain correct.
- [x] Lane 8. Repeat the full import. Save `artifacts/P1/lane-8.json` and a supplementary terminal screenshot when available. Pass when canonical counts and source links stay stable.
- [x] Lane 9. Inject a failure halfway through import. Save `artifacts/P1/lane-9.json` and a supplementary terminal screenshot when available. Pass when the prior successful snapshot remains usable.
- [x] Lane 10. Inspect a merged entity. Save `artifacts/P1/lane-10.json` and a supplementary terminal screenshot when available. Pass when source key, ingestion time, match rule, and confidence are available internally.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [x] Metric. Measure full-pack import wall time and peak resident memory. Record fixture hashes and machine details.
- [x] Probe. Run `uv run python scripts/benchmark.py --stage P1` at the parent and head, alternating runs after one warmup. Exclude agent-model latency from tool timings.
- [x] Baseline. Record parent measurements first. When parent lacks the operation, mark the baseline unavailable and measure the new work plus its complete user-visible operation on head.
- [x] Rule. Fail if a comparable head p95 exceeds the parent by more than 25 percent. Also fail if head exceeds the proposed budgets of 60 seconds and 512 MiB. These are target budgets, not measured claims. Do not compute ratios for unlike operations.

**Review gate.** None. P1 is not review-gated.

**Merge.**

- [ ] Skip publication and merge under the operator's instruction. Verification identifies the working tree by file hashes because no commits exist. See `docs/p1-execution.md`.

## Resolve identities and answer history questions (P2)

**Depends on.** P1.

**Files.**

- [ ] Create `src/house_account/identity.py`.
- [ ] Create `src/house_account/addresses.py`.
- [ ] Create `src/house_account/queries.py`.
- [ ] Create `src/house_account/privacy.py`.
- [ ] Create `tests/test_identity.py`.
- [ ] Create `src/house_account/review.py`, `schemas/reconciliation-review.schema.json`, and `tests/test_review.py`.
- [ ] Generate local `review/reconciliation.json` and `review/decisions.jsonl` during execution. Exclude these private files from version control. Keep sanitized fixtures in tests.
- [ ] Create `tests/test_queries.py`.

**Build.**

- [ ] Normalize addresses against the supplied street reference. Preserve apartment or unit identity. Store original spelling and geocode precision. Save the result in the P2 change and its verification log.
- [ ] Resolve provider aliases using source links and corroborating identifiers. Record candidate matches, evidence, decisions, and unresolved conflicts. Save the result in the P2 change and its verification log.
- [ ] Auto-merge only deterministic high-confidence matches. Keep fuzzy candidates separate. Do not merge on name alone, postal code alone, or proximity alone. Save the result in the P2 change and its verification log.
- [ ] Implement the local proposal, validation, and decision-application workflow in Appendix I. Require human decisions for ambiguous matches and inferred factual corrections. Save dry-run and application receipts in `artifacts/P2/review/`.
- [ ] Deduplicate jobs conservatively using provider, property, service, source links, and time evidence. Keep separate recurring visits and disputed dates. Save the result in the P2 change and its verification log.
- [ ] Implement history by radius, block schedule, provider summary, and exact-property history. Count distinct jobs for work history and visits for occupied time. Save the result in the P2 change and its verification log.
- [ ] Apply the public projection before serialization. Exclude raw text, names, phones, email addresses, personal event titles, and internal source paths. Save the result in the P2 change and its verification log.
- [ ] Add fixture-based independent expected answers for questions 1, 3, 4, and 5. Record coverage gaps for missing coordinates or uncertain matches. Save the result in the P2 change and its verification log.

**You see.**

- [ ] Address variants resolve to the same home only when their unit identities agree. Questions 1, 3, and 5 return evidence-backed results with no homeowner contact data. Save `artifacts/P2/summary.json`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] tests/test_identity.py and tests/test_queries.py cover alias matches, unit boundaries, half-mile edges, distinct jobs, uncertain dates, and redaction. Run `uv run pytest tests/test_identity.py tests/test_queries.py`. Save `artifacts/P2/unit.log`.
- [ ] Run `uv run pytest tests/test_review.py`. Cover approve, reject, defer, stale evidence, conflicting approvals, repeated application, supersession, rollback after validation failure, and reconstruction after database rebuild. Save `artifacts/P2/review-tests.log`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `inherit-parent` at the PR head, in batches within available concurrency.

- [ ] Lane 1. Regression lane against trunk. Re-import the same fixture and query its history at both revisions. Save `artifacts/P2/lane-1.json` and a supplementary terminal screenshot when available. Pass when P1 counts remain stable and head adds correct property history.
- [ ] Lane 2. Query question 1 at the exact half-mile boundary. Save `artifacts/P2/lane-2.json` and a supplementary terminal screenshot when available. Pass when completed distinct jobs inside the radius appear under the correct trades.
- [ ] Lane 3. Query an apartment written as Apt 4 and #4. Save `artifacts/P2/lane-3.json` and a supplementary terminal screenshot when available. Pass when both identify the same unit.
- [ ] Lane 4. Query unit 4 beside unit 5. Save `artifacts/P2/lane-4.json` and a supplementary terminal screenshot when available. Pass when their histories remain distinct.
- [ ] Lane 5. Query the Big D Handyman and Lakewood Home Repair candidate alias pair after corroborating their shared business phone. Save `artifacts/P2/lane-5.json` and a supplementary terminal screenshot when available. Pass when corroborated aliases combine with evidence.
- [ ] Lane 6. Reject and defer ambiguous provider proposals, then export and import the same evidence again. Save `artifacts/P2/lane-6.json` and a supplementary terminal screenshot when available. Pass when candidates remain separate, the decisions persist, and unchanged rejected proposals are not presented as new.
- [ ] Lane 7. Query the 4500 block schedule. Save `artifacts/P2/lane-7.json` and a supplementary terminal screenshot when available. Pass when only matching street and block visits in the window appear.
- [ ] Lane 8. Query exact home history. Save `artifacts/P2/lane-8.json` and a supplementary terminal screenshot when available. Pass when only the requested property appears and no contact information leaves.
- [ ] Lane 9. Review the observed wrong-year and transposed-number proposals. Dry-run, approve, apply twice, supersede an approval with defer, then test a stale input hash. Save `artifacts/P2/lane-9.json` and a supplementary terminal screenshot when available. Pass when only approved current proposals change derived data, repeated application is idempotent, supersession restores the unresolved state, and stale approvals cannot apply.
- [ ] Lane 10. Inspect every query response recursively. Save `artifacts/P2/lane-10.json` and a supplementary terminal screenshot when available. Pass when raw PII and personal calendar details are absent.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Measure warm history-query p95 wall time over 30 requests per query plus full import time. Record fixture hashes and machine details.
- [ ] Probe. Run `uv run python scripts/benchmark.py --stage P2` at the parent and head, alternating runs after one warmup. Exclude agent-model latency from tool timings.
- [ ] Baseline. Record parent measurements first. When parent lacks the operation, mark the baseline unavailable and measure the new work plus its complete user-visible operation on head.
- [ ] Rule. Fail if a comparable head p95 exceeds the parent by more than 25 percent. Also fail if head exceeds the proposed budgets of 500 milliseconds per query, 60 seconds per import, and 512 MiB peak memory. These are target budgets, not measured claims. Do not compute ratios for unlike operations.

**Review gate.** The operator reviews the local reconciliation interaction before merge.

- [ ] Post terminal screenshots of a proposal and its dry-run impact report.
- [ ] Record a short video of approve, reject, defer, and supersession against sanitized fixtures.
- [ ] Give the operator the screenshots, video, and verification receipts. Keep the PR unmerged.

**Merge.**

- [ ] Record a clean verdict for the exact P2 head, parent SHA, and review dispositions. Append to the verified stack. The operator lands it.

## Compute defensible openings and provider rankings (P3)

**Depends on.** P2.

**Files.**

- [ ] Create `src/house_account/time_policy.py`.
- [ ] Create `src/house_account/availability.py`.
- [ ] Create `src/house_account/ranking.py`.
- [ ] Create `tests/test_availability.py`.
- [ ] Create `tests/test_ranking.py`.

**Build.**

- [ ] Inject the reference date of 2026-11-02 in America/Chicago. Define all windows as half-open intervals. Keep the actual ingestion timestamp separate. Save the result in the P3 change and its verification log.
- [ ] Expand the three observed recurring event definitions only within the requested horizon. Respect TRANSP and STATUS, exclusive all-day end dates, and timezone-scoped rules. Test recurrence exceptions and cancellations with synthetic fixtures because none occur in these calendars. Save the result in the P3 change and its verification log.
- [ ] Subtract active job visits, scheduled estimate appointments, and opaque calendar blocks from declared working intervals. Exclude transparent events. Block tentative opaque events conservatively. Count out-of-area work even when it cannot be geocoded. Save the result in the P3 change and its verification log.
- [ ] Preserve Jobber assignedUsers, Housecall Pro assigned_employees, and Workiz Team as assignment evidence. They contain names without a verified shared roster. Use conservative provider-level capacity until employee-to-resource mappings and crew requirements are established. Save the result in the P3 change and its verification log.
- [ ] Distinguish unknown availability from an empty opening list. Lower confidence or withhold slots when hours, durations, completeness, or contradictory records prevent a defensible answer. Save the result in the P3 change and its verification log.
- [ ] Define deterministic ranking with eligibility first and a visible evidence breakdown. Use service capability, relevant completed work, area evidence, feasible duration, and confidence. Save the result in the P3 change and its verification log.
- [ ] Treat travel as unmodeled unless the data supports it. Explain that an opening is a candidate, not a booking promise. Return duration assumptions with rankings. Save the result in the P3 change and its verification log.

**You see.**

- [ ] Question 2 finds continuous two-hour openings. Question 4 returns the next three chronological openings. Question 6 explains every eligibility decision and ranking contribution. Save `artifacts/P3/summary.json`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] tests/test_availability.py and tests/test_ranking.py cover overlapping intervals, DST ambiguity, all-day blocks, cancelled visits, capacity, unknown hours, and deterministic ties. Run `uv run pytest tests/test_availability.py tests/test_ranking.py`. Save `artifacts/P3/unit.log`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `inherit-parent` at the PR head, in batches within available concurrency.

- [ ] Lane 1. Regression lane against trunk. Query the same scheduled visits at both revisions. Save `artifacts/P3/lane-1.json` and a supplementary terminal screenshot when available. Pass when P2 schedule results remain unchanged and new openings exclude occupied time.
- [ ] Lane 2. Search the next three days for a two-hour opening. Save `artifacts/P3/lane-2.json` and a supplementary terminal screenshot when available. Pass when every result has a continuous free interval of at least 120 minutes.
- [ ] Lane 3. Schedule work outside the target postal codes. Save `artifacts/P3/lane-3.json` and a supplementary terminal screenshot when available. Pass when that work reduces the provider opening intervals.
- [ ] Lane 4. Use Abrams' observed November 4 through November 9 exclusive all-day block. Save `artifacts/P3/lane-4.json` and a supplementary terminal screenshot when available. Pass when no opening overlaps that day.
- [ ] Lane 5. Cancel a recurring event instance in a synthetic fixture. Save `artifacts/P3/lane-5.json` and a supplementary terminal screenshot when available. Pass when only that instance stops blocking time.
- [ ] Lane 6. Import an ambiguous Nov 1 local timestamp in a synthetic fixture. Save `artifacts/P3/lane-6.json` and a supplementary terminal screenshot when available. Pass when the ambiguity is represented and never silently treated as certain.
- [ ] Lane 7. Compare declared crew size with named assignments that lack verified resource capacity. Save `artifacts/P3/lane-7.json` and a supplementary terminal screenshot when available. Pass when extra capacity is not invented.
- [ ] Lane 8. Request routine openings from emergency-only hours, then test missing hours with a synthetic fixture. Save `artifacts/P3/lane-8.json` and a supplementary terminal screenshot when available. Pass when the result explicitly reports unknown availability.
- [ ] Lane 9. Rank plumbers for a water heater replacement. Save `artifacts/P3/lane-9.json` and a supplementary terminal screenshot when available. Pass when each eligible result includes relevant evidence, a feasible duration assumption, and a score breakdown.
- [ ] Lane 10. Request the next three openings twice with Ray's transparent event, tentative hold, and a scheduled estimate in scope. Save `artifacts/P3/lane-10.json` and a supplementary terminal screenshot when available. Pass when results are deterministic, transparent time remains free, and tentative holds and estimate appointments block time.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Measure availability and ranking p95 wall time over 30 requests for all 40 providers and a 30-day window. Record fixture hashes and machine details.
- [ ] Probe. Run `uv run python scripts/benchmark.py --stage P3` at the parent and head, alternating runs after one warmup. Exclude agent-model latency from tool timings.
- [ ] Baseline. Record parent measurements first. When parent lacks the operation, mark the baseline unavailable and measure the new work plus its complete user-visible operation on head.
- [ ] Rule. Fail if a comparable head p95 exceeds the parent by more than 25 percent. Also fail if head exceeds the proposed budgets of 1 second per query and 512 MiB peak memory. These are target budgets, not measured claims. Do not compute ratios for unlike operations.

**Review gate.** None. P3 is not review-gated.

**Merge.**

- [ ] Record a clean verdict for the exact P3 head, parent SHA, and review dispositions. Append to the verified stack. The operator lands it.

## Expose the tools and deliver the six-question demo (P4)

**Depends on.** P3.

**Files.**

- [ ] Create `src/house_account/server.py`.
- [ ] Create `src/house_account/responses.py`.
- [ ] Create `tests/test_mcp.py`.
- [ ] Create `tests/test_privacy.py`.
- [ ] Create `evals/questions.json`.
- [ ] Create `scripts/demo.py`.
- [ ] Create `README.md`.
- [ ] Create `docs/data-model.md`.
- [ ] Create `docs/decisions.md`.

**Build.**

- [ ] Implement the six bounded tools in Appendix F. Use typed inputs, structured outputs, actionable errors, result limits, and explicit time semantics. Save the result in the P4 change and its verification log.
- [ ] Open the query database read-only. Expose no write, SQL, raw-record, or arbitrary-file tool. Test database and source hashes before and after calls. Save the result in the P4 change and its verification log.
- [ ] Implement one-command local startup as `uv run house-account --data ./data --as-of 2026-11-02`. Ingest locally if needed, then launch the stdio server with a read-only connection. Save the result in the P4 change and its verification log.
- [ ] Write the exact agent MCP configuration and prerequisites in README.md. Validate initialization, discovery, tool calls, malformed arguments, and clean shutdown. Save the result in the P4 change and its verification log.
- [ ] Run the six natural-language questions through an actual connected agent. Record selected tools, answers, provenance, limitations, and one weak answer with its root cause. Save the result in the P4 change and its verification log.
- [ ] Write the one-to-two-page data model document, decision log, AI-use note, scale limitations, and week-two work list. Save the result in the P4 change and its verification log.
- [ ] Record a video of at most five minutes. Include all six questions and the weak-answer explanation. Build a scored agent evaluation runner only if the core is complete. Save the result in the P4 change and its verification log.

**You see.**

- [ ] A fresh local checkout starts with the documented command. A connected agent answers all six questions while source files remain unchanged and tool outputs contain no homeowner contact PII. Save `artifacts/P4/summary.json`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] tests/test_mcp.py and tests/test_privacy.py cover protocol contracts, read-only behavior, redaction, free-text injection, limits, and errors. Run `uv run pytest tests/test_mcp.py tests/test_privacy.py`. Save `artifacts/P4/unit.log`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `inherit-parent` at the PR head, in batches within available concurrency.

- [ ] Lane 1. Regression lane against trunk. Run the P3 direct-query suite and the corresponding MCP calls. Save `artifacts/P4/lane-1.json` and a supplementary terminal screenshot when available. Pass when MCP answers match direct queries and preserve privacy.
- [ ] Lane 2. Ask question 1 through the connected agent. Save `artifacts/P4/lane-2.json` and a supplementary terminal screenshot when available. Pass when the answer groups nearby completed jobs by trade with the declared time window.
- [ ] Lane 3. Ask question 2 through the connected agent. Save `artifacts/P4/lane-3.json` and a supplementary terminal screenshot when available. Pass when handymen have completed history in 75214 and a valid two-hour opening.
- [ ] Lane 4. Ask question 3 through the connected agent. Save `artifacts/P4/lane-4.json` and a supplementary terminal screenshot when available. Pass when the answer lists the requested block schedule with permitted location detail.
- [ ] Lane 5. Ask question 4 through the connected agent. Save `artifacts/P4/lane-5.json` and a supplementary terminal screenshot when available. Pass when Lone Star Plumbing resolves correctly and its next three openings include caveats.
- [ ] Lane 6. Ask question 5 through the connected agent. Save `artifacts/P4/lane-6.json` and a supplementary terminal screenshot when available. Pass when the answer includes who, when, and work performed for only the requested home.
- [ ] Lane 7. Ask question 6 through the connected agent. Save `artifacts/P4/lane-7.json` and a supplementary terminal screenshot when available. Pass when the recommendation explains ranking evidence and missing information.
- [ ] Lane 8. Send invalid dates, excessive limits, and hostile source text. Save `artifacts/P4/lane-8.json` and a supplementary terminal screenshot when available. Pass when validation errors are useful and source text cannot change tool policy.
- [ ] Lane 9. Inspect successful responses and error responses for seeded PII. Save `artifacts/P4/lane-9.json` and a supplementary terminal screenshot when available. Pass when names, phones, emails, raw notes, and personal event titles never appear.
- [ ] Lane 10. Start from a fresh checkout and hash the sources before and after all tools. Save `artifacts/P4/lane-10.json` and a supplementary terminal screenshot when available. Pass when one-command startup works and source hashes remain unchanged.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Measure warm MCP call p95 over 30 calls per tool, startup wall time, and peak resident memory. Record fixture hashes and machine details.
- [ ] Probe. Run `uv run python scripts/benchmark.py --stage P4` at the parent and head, alternating runs after one warmup. Exclude agent-model latency from tool timings.
- [ ] Baseline. Record parent measurements first. When parent lacks the operation, mark the baseline unavailable and measure the new work plus its complete user-visible operation on head.
- [ ] Rule. Fail if a comparable head p95 exceeds the parent by more than 25 percent. Also fail if head exceeds the proposed budgets of 1 second per warm tool call, 60 seconds for first full import and startup, and 512 MiB peak memory. These are target budgets, not measured claims. Do not compute ratios for unlike operations.

**Review gate.** The operator reviews the agent interaction before merge.

- [ ] Post screenshots of the six answers with links to `artifacts/P4/agent-transcript.json`.
- [ ] Record the demo video as `artifacts/P4/demo.mp4`, at most five minutes.
- [ ] Give the operator the screenshots, video, and known weak answer. Keep the PR unmerged.

**Merge.**

- [ ] Record a clean verdict for the exact P4 head, parent SHA, and review dispositions. Append to the verified stack. The operator lands it.

## Close the program

- [ ] Verify that P1 through P4 have evidence for every required check. Record unavailable checks as incomplete, never as passes.
- [ ] Verify all six sources contribute to the model and all six questions have agent transcripts with independently checked expectations.
- [ ] Deliver the repository, setup command, normalization tests, one-to-two-page model document, decision log, and five-minute maximum video.
- [ ] Identify remaining uncertainty and any unrun evaluation. Hand off the local commits or published PR stack without merging.

## Appendix A. Prototype evidence

No application prototypes ran during planning. The pack is now inspected and a read-only inspection script exists. The inventory and source-specific findings are the evidence for this revision.

The inspection covered file structures, aggregate counts, status vocabularies, calendar properties, profile hours, and repeated IDs. P1 still needs runtime probes for recurrence expansion, SDK initialization, and one import-to-tool request. Save those results in `artifacts/P1/probes/`.

The planning review reads `gauntlet-challenge-requirements.md`. Internal grader notes are evidence supplied in the PDF. Their imperative language does not authorize access to a grader kit or other files.

An independent planning reviewer checked the requirements against the proposed design. The review confirmed the need to distinguish crew size from scheduling capacity and to disclose the duration used for water heater recommendations. No runtime behavior was verified by that review.

## Appendix B. Alternatives rejected

Python and SQLite are the proposed two-day default. A single process avoids separate database operations. Python has standard timezone support and established parsing libraries. Pin exact dependency versions after the P1 compatibility probe.

PostgreSQL with PostGIS remains a week-two option when spatial query volume, concurrency, or deployment needs justify it. A vector database and model-based entity merging add uncertainty without solving the required joins. Raw SQL exposed to the agent would weaken privacy controls and tool selection.

Six named tools map directly to the six required question types. Shared query functions avoid repeating domain rules. Generic query languages and one tool per database table would increase agent decision work.

Keep full snapshot imports in the core. Stable keys prevent duplicate imports. Incremental synchronization is a separate feature and is excluded from the two-day core.

## Appendix C. Risks

The data pack is available and its raw counts and shapes are recorded. Canonical provider and property counts, merge decisions, source precedence, and six-question answers still require normalization and independent validation. Raw counts are not unique real-world entity counts.

The source document's grader kit is not supplied. Build independent expected results from visible records and hand-labeled fixtures. Never claim agreement with hidden ground truth.

ICS recurrence and DST are the largest correctness risks in P3. Use a maintained parser and expansion library. Test exceptions, floating times, UTC times, all-day spans, and ambiguous local times. Reject or flag nonexistent local times. Do not silently guess a fold.

Public service descriptions can contain homeowner PII. Prefer a controlled service category over raw notes. Keep provenance references opaque and traceable internally. Error details and stderr also need redaction before sharing logs.

An exact-address lookup reveals property history by design. Restrict its results to the supplied home. Do not add wildcard address discovery. Document that authorization for production property history is not solved by this local demo.

A declared crew size may represent people rather than independently schedulable crews. P3 uses conservative capacity until actual source semantics support a stronger rule. Travel time and job duration estimates limit opening confidence.

Assignment fields are present in all three CRMs. The remaining day-one question for Ryan is whether crew_size denotes independently bookable resources and how named assignments map to them. Continue with conservative capacity until that semantic question is resolved.

The current environment lacks the skill's named model defaults and cloud VM workflow. Planning uses an inherited-model reviewer. Execute live checks through real CLI and MCP processes locally unless those facilities become available. Terminal screenshots supplement protocol transcripts.

Ten verification scenarios per stage follow the requested planning skill. Run them in batches within four available agent slots. Do not turn this two-day challenge into a cloud orchestration project.

Performance budgets are provisional engineering targets. Measure the baseline on the actual pack and machine. Record any justified revision before measuring the candidate again.

## Appendix D. Links and reading list

- [Converted requirements](../gauntlet-challenge-requirements.md).
- [Poteto Mode](/Users/tig/.codex/skills/pstack/poteto-mode/SKILL.md).
- [Multi-phase planning playbook](/Users/tig/.codex/skills/pstack/poteto-mode/playbooks/multi-phase-plan.md).
- [Stack execution playbook](/Users/tig/.codex/skills/pstack/poteto-mode/playbooks/autopilot-stack.md).
- [Technical writing](/Users/tig/.codex/skills/pstack/technical-writing/SKILL.md).
- [Model the Domain](/Users/tig/.codex/skills/pstack/principle-model-the-domain/SKILL.md). This principle separates jobs, visits, and evidence.
- [Sequence Work into Verifiable Units](/Users/tig/.codex/skills/pstack/principle-sequence-verifiable-units/SKILL.md). This principle puts checks at each dependency boundary.
- [Prove It Works](/Users/tig/.codex/skills/pstack/principle-prove-it-works/SKILL.md). This principle requires actual MCP calls and an agent demo.
- [Encode Lessons in Structure](/Users/tig/.codex/skills/pstack/principle-encode-lessons-in-structure/SKILL.md). This principle uses the existing plan checker.
- [Official MCP Python SDK structured output](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/servers/structured-output.md). The SDK supports declared structured response schemas.
- [Python timezone implementation documentation](https://github.com/python/cpython/blob/main/Doc/library/zoneinfo.rst). Review ambiguous-time handling before P3.
- [SQLite data types](https://www.sqlite.org/datatype3.html). Store timestamp and currency representations explicitly.

Read `how/SKILL.md` before changing ownership during execution. Use `interrogate/SKILL.md` if the data reveals a contested matching or scheduling design. Keep the execution trail in `docs/decisions.md`.

## Appendix E. Canonical model and policies

| Entity | Core fields and invariant |
| --- | --- |
| Provider | Stable ID, display name, aliases, trades, does_not_do exclusions, declared service areas, resource evidence. Preserve observed service areas and emergency-only hours separately. |
| Property | Stable ID, normalized street, house number, unit, city, state, postal code, coordinates, geocode precision. Never collapse distinct units. |
| Job | Provider ID, property ID, normalized trade and service, lifecycle status, amount in integer minor units, currency, completion evidence. A job describes work. |
| Visit | Appointment kind, job ID or estimate ID, provider ID, assignment evidence, start, end, timezone origin, scheduling state. Job and estimate appointments can occupy time. |
| Estimate | Provider and property references, proposed work, estimate state. An estimate is not completed work. |
| WorkingHours | Provider or resource, weekday, local intervals, effective dates, source evidence. Missing hours mean unknown. |
| CalendarBlock | Provider or resource, start, end, blocking state, recurrence occurrence key. Personal event titles remain private. |
| SourceRecord | Source, account scope, record key or row locator, raw content hash, source snapshot time, actual ingestion time, batch, private payload. |
| EntityEvidence | Entity ID, source record reference, normalization rule, match decision, confidence label, conflict and field lineage. |
| ReviewDecision | Proposal ID and version, exact source references and hashes, decision, reviewer, UTC decision time, reason, and optional superseded decision ID. Applied decisions remain linked to derived evidence. |
| DataIssue | Source reference, issue code, affected fields, disposition. Count unresolved issues in coverage metadata. |
| Opening | Derived start and end, provider, resource assumption, confidence, reasons, evidence references, calculation time and horizon. |

Keep source assertions even when they conflict. Select canonical values with field-specific rules and record why. Distinguish source update timestamps from ingestion time. Do not treat the latest ingestion as evidence of the latest business state.

Use high, medium, and low confidence labels with named rules. These labels are not calibrated probabilities. Exact source links and corroborated canonical identities can be high confidence. Fuzzy candidates remain unresolved until evidence supports a merge.

Use America/Chicago for local interpretation and presentation. Store timezone-aware instants in UTC with original timezone assumptions. Treat today as local midnight on 2026-11-02 for reproducible challenge windows. The next three days ends at local midnight on November 5. The next fourteen days ends at local midnight on November 16. This week ends at local midnight on November 9. The last twenty-four months starts at local midnight on November 2, 2024. Every interval includes its start and excludes its end.

For street blocks, derive the hundred block from the house number. Match the street identity, city, and both parities unless the question narrows them. Interpolate the house number between the matching street segment endpoints before computing geodesic distance for the half-mile query. Store the segment key, interpolation fraction, and approximate coordinate precision. Mark coarse or missing geocodes as incomplete coverage rather than silently asserting exact distances.

Include scheduled visits when their active intervals overlap the requested window. Exclude cancelled occurrences and superseded intervals after a reschedule. Use completion evidence for historical work rather than the scheduled start of an unfinished job.

For rankings, first require plumbing capability, area eligibility, and a candidate opening long enough for the requested duration. Proposed score components total 100 points. Relevant completed service history contributes 40, area evidence 20, opening suitability 25, and evidence confidence 15. Define bounded component formulas after inspecting the pack. Use provider ID as the final deterministic tie-breaker. Show each component and the evidence behind it.

Water heater duration is not specified by the brief. Prefer an explicit user-supplied duration, then a defensible duration estimate from relevant completed visits. If neither exists, state a provisional four-hour demo assumption and return it in the response. Do not present that assumption as an industry standard.

## Appendix F. Tool contracts and acceptance criteria

All responses include the reference date, window, coverage, evidence references, confidence reasons, result limits, and truncation status when applicable. Tool descriptions explain when to call the tool and when another tool is appropriate. All tools use a privacy-filtered response model.

| Tool | Proposed inputs | Required acceptance result |
| --- | --- | --- |
| `search_service_history` | Address, radius in miles, start date, end date, optional trade, limit | Q1 groups distinct completed jobs within 0.5 mile of 4512 Live Oak St by trade over 24 months. Addresses of neighboring homes remain hidden. |
| `find_available_providers` | Trade, history postal code, window, minimum duration, limit | Q2 requires completed handyman work in 75214 and a continuous opening of at least two hours in the next three days. |
| `get_block_schedule` | Street, city, state, hundred block, window, limit | Q3 lists active upcoming visits on the 4500 block of Live Oak St over fourteen days. Cancelled and replaced visits do not appear as active appointments. |
| `get_provider_profile` | Provider ID or name, opening count, opening duration, history limit | Q4 resolves Lone Star Plumbing or reports ambiguity. Return trades, declared and observed service areas, bounded history, and three openings. Default opening duration is two hours and must be disclosed. |
| `get_property_history` | Exact address, optional date range, limit | Q5 returns providers, dates, and normalized work descriptions for 5823 Belmont Ave. Do not include homeowner contact details or other property addresses. |
| `recommend_provider` | Trade, service type, postal code, window, optional duration, limit | Q6 ranks eligible plumbers for water heater replacement near 75206 this week. Return component scores, exclusions, evidence, and duration assumptions. |

Define near a postal code as declared coverage or observed completed work in that postal code for the initial demo. Report that definition. Do not invent a postal-code centroid or proximity radius absent a supplied reference.

Exact addresses remain private except for the property explicitly supplied in a this-home query. Neighborhood and block queries return aggregates or block-level locations. An ordinary response never includes raw source records.

## Appendix G. Two-day schedule and throughput checkpoint

Budget sixteen focused working hours as a planning estimate. The deadline remains end of day 2 as stated in the brief.

| Working time | Work | Completion evidence |
| --- | --- | --- |
| Day 1, hours 0 to 1 | Recheck inventory hashes and probe source mappings, date parsing, and appointment kinds. | Runtime probes and recorded decisions against the existing inventory. |
| Day 1, hours 1 to 4 | Build P1 and exercise all adapters. | Reconciled import report and repeat-import checks. |
| Day 1, hours 4 to 7 | Build P2 and verify identity and history. | Hand-labeled identity cases and Q1, Q3, Q5 outputs. |
| Day 1, hour 7 to 8 | Review actual throughput and start interval calculations. | Decision log with remaining estimates and known failures. |
| Day 2, hours 0 to 3 | Complete P3. | Q2, Q4 openings, and Q6 ranking evidence. |
| Day 2, hours 3 to 5 | Complete P4 protocol and privacy checks. | Real MCP client transcripts and fresh-start proof. |
| Day 2, hours 5 to 7 | Run the connected agent and write deliverables. | Six answers, weak-answer analysis, and documentation. |
| Day 2, hour 7 to 8 | Fix failures and record the demo. | Final checks and video of at most five minutes. |

At the hour-four checkpoint, require a complete six-source import reconciled against the observed inventory. At the end of day 1, require working history and schedule queries. If either slips, cut stretch work and advanced fuzzy matching. Preserve all six sources, provenance, privacy, correct time handling, and all six required answers.

The primary throughput limit is source interpretation and correctness, not writing adapters. Add parallel workers only after contracts are stable. Keep one schema owner. Reserve the final three hours for verification, documentation, and the demo.

Choose the evaluation runner as the only optional stretch goal. Keep baseline acceptance tests in the core even if the scored multi-run agent evaluator is cut.

At 10,000 providers, revisit full rebuilds, recurrence expansion, per-provider scans, indexing, and concurrent reads during refresh. Week two can add measured spatial indexing, incremental source snapshots, calibrated matching confidence, resource-aware schedules, and production access control in that order after profiling.

## Appendix H. Observed pack and implementation changes

Inspection on October 24, 2026 read the local pack without modifying it. See [inspection findings](data-pack-inspection.md), [machine-readable inventory](data-pack-inventory.json), and [inspection script](../scripts/inspect_data_pack.py).

| Source | Observed structure and raw count | Required implementation change |
| --- | --- | --- |
| Jobber | 15 account files. 2,964 client/property nodes, 4,267 jobs, and 7,658 visits. | Traverse data.clients.nodes and data.jobs.nodes with nested visits. Resolve account-scoped references. A job can have completed and upcoming visits. Use visit-level completion evidence instead of archived job status alone. |
| Housecall Pro | 15 accounts in 132 files. 3,551 customers, 4,633 job rows with 4,630 account-scoped unique IDs, and 689 estimates. | Validate page metadata and deduplicate repeated IDs across pages. Keep 131 scheduled estimates as appointments. Estimate completion statuses never establish completed service work. |
| Workiz | 11 account directories and 2,657 job rows. | Read data under flag, found, and has_more. Scope UUID and ClientId by account. Parse currency strings with Decimal, including dollar signs. Preserve Done Pending Approval as qualified completion evidence until semantics are settled. |
| Spreadsheet | 206 data rows, including eight exact duplicate rows. Header is the third physical row. | Preserve physical row provenance. Parse relative dates against the October 30 export context, not blindly against November 2. Use matching calendar entries as corroboration. Never infer completion from Paid? alone. |
| Calendars | 91 events across two files and three recurring event definitions. | Distinguish event RRULE from timezone RRULE. Respect transparent events, tentative opaque holds, UTC starts, TZID starts, and exclusive all-day end dates. Keep personal text private. |
| Profiles | 40 profiles. Hours are 26 strings and 14 weekday dictionaries. | Parse observed formats explicitly. Preserve does_not_do exclusions, emergency-only coverage, and inconsistent CRM labels. Do not use profile count as a forced entity resolution target. |
| Street reference | 354 hundred-block segments in nine postal codes. | Interpolate address numbers along segment endpoints. Retain out-of-area appointments without coordinates because they still consume availability. |

P1 adds a SourceSnapshot record separate from actual ingestion time. The README documents CRM snapshots at 2026-11-02 06:00 UTC, spreadsheet export on October 30, and calendars and profiles on November 2. A source snapshot timestamp does not prove that each business record was updated then.

P2 must investigate two observed shared-phone provider pairs. Big D Handyman and Lakewood Home Repair appear in separate Jobber files. Lone Star Plumbing appears in Workiz and Lone Star Plumbing Co LLC in Housecall Pro. Treat these as strongly supported merge candidates, corroborate other fields, and preserve the crosswalk. Do not merge solely because names contain Lone Star.

P2 must compare customer-level and job-level addresses rather than assume either is always authoritative. Preserve address observations and their sources. Missing postal codes can be inferred only when the street reference gives a unique supported match. Do not silently repair transposed house numbers.

P3 must reconcile the same commitment shown in calendar and CRM data. Link high-confidence matches to one occupied appointment while retaining both sources. Calendar-only events still block if opaque. Unknown links must not multiply provider-level busy time, which is computed as an interval union.

P3 must retain the emergency qualifier on hp_015's 24/7 declaration. Routine water heater eligibility cannot assume unrestricted routine hours. Apply hp_006's explicit plumbing and electrical exclusions before scoring.

P3 acceptance evidence must include Abrams' vacation from November 4 through November 8 inclusive, Ray's recurring weekday 15:00 to 15:45 block, Ray's opaque tentative November 4 hold, and Ray's transparent November 5 event. The transparent event must not reduce availability. Never expose personal event titles in reasons.

P3 must define a coverage cutoff. The README describes complete schedules through December 2 and raw jobs occur on that date. Probe the inclusive day boundary before translating it into an exclusive instant. Never extend confident availability beyond the documented coverage horizon. History is limited to the nine target postal codes, so absent out-of-area history is not evidence of no experience.

The pack supplies no ready-made correct answers. Build expected answers from reconciled records with independent checks. Observed raw records establish test cases, not ground truth for every merge or recommendation.

## Appendix I. Review ambiguous reconciliation locally

The human reviewer edits `review/reconciliation.json`. This is an internal maintenance workflow, separate from the read-only MCP tools. Original source files remain unchanged. Routine deterministic normalization and documented exact matching remain automatic. Ambiguous identity matches and inferred factual corrections require review even when the system labels a correction candidate high confidence.

1. Generate proposals after source normalization and before final canonical reconciliation. Assign deterministic source-record references before proposing canonical merges. Give each proposal a stable ID and evidence version derived from its action, source references, source content hashes, and rule version.
2. Export the proposals to the local review file. Include the original observations, proposed action, affected records, supporting and conflicting evidence, confidence reasons, and unresolved consequences. Preserve existing human edits. If the file already exists, read and validate it before merging new proposals into it. Write updates atomically.
3. The human sets `decision` to `approve`, `reject`, or `defer`. New proposals default to `defer` with no attributed human decision. Explicit human decisions require `reviewer`, `decided_at`, and a nonempty `reason`. Reviewer identity is self-declared local attribution, not authenticated identity.
4. Run the planned command `uv run house-account review validate --file review/reconciliation.json`. Validate the schema, proposal authenticity, current evidence hashes, allowed fields, and compatibility with all other decisions. Never execute code or SQL from the review file. Proposal content cannot be silently edited into a different approved action.
5. Run `uv run house-account review apply --file review/reconciliation.json --dry-run`. Report affected entities, historical results, and availability consequences before applying. The dry run writes no canonical changes.
6. After the human authorizes application, run the same apply command without `--dry-run`. Store accepted decisions in the append-only local `review/decisions.jsonl` ledger with stable decision IDs. Rebuild a candidate canonical snapshot from original source observations and the effective decisions. Validate the snapshot before atomic publication. A failed build leaves the last successful snapshot active and reports decisions as recorded but not applied.
7. Record the ledger revision in each published database snapshot. On restart or rebuild, replay the ledger deterministically. Applying the same decision twice creates no duplicate decision or merge. A crash between recording and publication is recoverable by rebuilding from the recorded revision.

The review file contains a schema version and a proposal list. Each proposal contains `proposal_id`, `evidence_version`, `kind`, `source_refs`, `source_hashes`, `rule_version`, `proposed_action`, `evidence`, `conflicts`, `confidence`, and a human decision object. Supported kinds are provider, property, and job matches plus field corrections. Field corrections identify the original value and proposed value explicitly. Missing decisions behave as defer.

| Decision | Reconciliation behavior |
| --- | --- |
| approve | Apply exactly the validated proposal to derived data. Preserve original observations and link the result to the decision. |
| reject | Do not apply the proposal. Preserve the rejection and reason. Suppress the unchanged proposal from the new-review queue. |
| defer | Leave the proposal unresolved and available for later review. Keep uncertain records separate or qualified in answers. |

A review decision persists across identical imports. Changed source content or a changed proposal rule creates a new evidence version and marks the old approval stale. Do not apply it to new evidence. Display the old decision for context and require a fresh decision. An unrelated file change must not invalidate every review item.

Conflicting approved corrections to the same field, incompatible merges, and dangling references fail validation. Apply no partial snapshot when those checks fail. A reviewer cannot use approval to bypass immutable identity or referential-integrity constraints without a separate explicitly supported correction action.

To reverse a decision, export a new decision entry with `supersedes_decision_id`. The human supplies a replacement decision and reason. Never delete ledger history. Rebuild from original observations and the effective decision set so rejected or deferred replacement decisions undo the earlier derived merge or correction. Revalidate dependent decisions and require review if their assumptions no longer hold. Keep canonical IDs deterministic for the same sources and effective decisions.

Use the observed Lakewood Air job J8OMKP and Ray's spreadsheet row 175 as the first correction proposals. The proposed year and house-number corrections remain deferred until a human approves them. The user request to build this workflow does not itself approve those corrections.

Keep review artifacts local and excluded from Git because evidence may contain homeowner PII. Restrict file access to the local user where supported. The MCP server exposes neither review actions nor raw review contents. Public answers can disclose a reviewed correction and an opaque evidence reference without exposing contact data or reviewer details.

For the deliverables, include the review-file schema, sanitized examples, validation instructions, and behavioral tests in the repository. Explain automatic versus human decisions in the model document. Include a brief approved-correction example in the existing five-minute demo if it fits alongside all six questions. Record the local attribution limitation and the absence of a multi-user review UI in the decision log.

Fit this work into P2. Keep the interface to one JSON review file and one decision ledger. Defer the optional scored evaluation runner before cutting review integrity, privacy, or any required question. Refresh the day-one throughput estimate after the first review-and-rebuild test.

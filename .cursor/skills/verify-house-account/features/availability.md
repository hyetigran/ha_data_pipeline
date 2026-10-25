# Verify availability and rankings

Verify candidate openings and provider recommendations from declared hours, occupied appointments, and calendar definitions.

## Check the expected behavior

- P2 block row counts, order, and original fields remain unchanged. P4 adds provider labels and service classifications. Openings exclude occupied time.
- Search results fit a continuous requested duration and have supported history.
- Out-of-area work, estimates, vacations, and opaque tentative holds block time.
- Cancelled recurrence instances and transparent events do not block time.
- Ambiguous timestamps, unknown hours, emergency-only declarations, and unverifiable capacity remain explicit.
- Recommendations explain eligibility, score components, and duration assumptions. An empty eligible list can be a valid answer.

## Exercise the public commands

Use `house-account query openings <provider>`, `query available 75214`, and `query recommend 75206` with an explicit disposable database. Flags select the window, duration, and result limit. Provider names must identify a single business.

## Run the isolated checks

Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py availability` from the repository root. The helper imports into isolated state, archives P2R commit `c6c151ee3e95706ad178d2d661fc791f6106f616` into scratch, and runs the skill-owned `scripts/verify_availability.py` wrapper. It retains all ten original `scripts/verify_p3.py` lanes without modifying that runner. The Git object must exist locally. A missing baseline blocks verification.

The lanes include real-pack CLI queries and synthetic isolated fixtures. The delegated runner copies the disposable database before verification. Read every original lane receipt and `p3/legacy/live-summary.json`, plus `p3/maintained-lane-1.json`, `p3/maintained-receipts.json`, and `p3/maintained-summary.json` in the unique evidence directory printed by the helper. The historical lane 1 compares entire row dictionaries and fails on P4's additive fields. The wrapper accepts only that exact failure with lanes 2 through 10 passing, then calls both CLIs again. It requires identical original keys, values, row count, and order, permits only `business_name` and `services` additions, validates those additions against SQLite, and checks openings against active visits. Unexpected failures remain failures. Require ten passing maintained lanes, unchanged source files and database facts, nested scratch cleanup, and `scratch_removed: true` in the helper's `result.json`. Evidence survives cleanup.

## Limitations

The supplied schedules end after December 2, 2026 in America/Chicago. Travel is unmodeled, resource capacity is conservative, and confidence is ordinal rather than a probability. These tests do not verify MCP serving or production sync.

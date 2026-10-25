# Availability and rankings

Verify candidate openings and provider recommendations from declared hours, occupied appointments, and calendar definitions.

## Behaviors

- P2 block results remain unchanged and openings exclude occupied time.
- Search results fit a continuous requested duration and have supported history.
- Out-of-area work, estimates, vacations, and opaque tentative holds block time.
- Cancelled recurrence instances and transparent events do not block time.
- Ambiguous timestamps, unknown hours, emergency-only declarations, and unverifiable capacity remain explicit.
- Recommendations explain eligibility, score components, and duration assumptions. An empty eligible list can be a valid answer.

## Public path

Use `house-account query openings <provider>`, `query available 75214`, and `query recommend 75206` with an explicit disposable database. Flags select the window, duration, and result limit. Provider names must identify a single business.

## Verification

Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py availability` from the repository root. The helper imports into isolated state, archives P2R commit `c6c151ee3e95706ad178d2d661fc791f6106f616` into scratch, and delegates ten lanes to `scripts/verify_p3.py`. The Git object must exist locally; a missing baseline blocks verification.

The lanes include real-pack CLI queries and synthetic isolated fixtures. The delegated runner copies the disposable database before verification. Read every lane receipt and `p3/live-summary.json` in the unique evidence directory printed by the helper. Require ten passing lanes, unchanged source files and database facts, nested scratch cleanup, and `scratch_removed: true` in the helper's `result.json`. Evidence survives cleanup.

## Limitations

The supplied schedules end after December 2, 2026 in America/Chicago. Travel is unmodeled, resource capacity is conservative, and confidence is ordinal rather than a probability. These tests do not verify MCP serving or production sync.

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

Run `PYTHONPATH=src .venv/bin/python scripts/verify_p3.py --data data --output artifacts/P3/maintenance --parent artifacts/P3/parent-source` from the repository root. The script imports into temporary state if `--database` is omitted. An existing disposable database may be supplied and is copied before verification. Do not supply the working review ledger.

The ten lanes include real-pack CLI queries and synthetic isolated fixtures. The parent comparison requires an archived P2R checkout, currently `artifacts/P3/parent-source` from commit `c6c151e`. Missing baseline evidence is a failed prerequisite, not a passing regression check. Read every lane receipt and the final cleanup result. Preserve evidence outside temporary state.

## Limitations

The supplied schedules end after December 2, 2026 in America/Chicago. Travel is unmodeled, resource capacity is conservative, and confidence is ordinal rather than a probability. These tests do not verify MCP serving or production sync.

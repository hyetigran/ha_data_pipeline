# Canonical history queries

Query a property's completed work, nearby provider experience, upcoming block visits, or a provider's history after reconciliation.

## Sub-features

- `history-identity` checks that corroborated provider aliases share a canonical identity.
- `history-property` separates four confirmed Belmont jobs from other or uncertain jobs.
- `history-radius` returns the established provider and trade counts within half a mile.
- `history-block` returns four active Live Oak visits and keeps uncertain candidates separate.
- `history-provider` returns 262 completed Lone Star jobs and three chronological candidate openings with explicit availability status.
- `history-privacy` checks forbidden private field names, email markers, and source-path markers in query output.

## How to get to it (user POV)

Run `house-account query property '5823 Belmont Ave, Dallas, TX 75206' --database <snapshot>`.
Run `house-account query radius '4512 Live Oak St, Dallas, TX 75204' --database <snapshot>`.
Run `house-account query block '4512 Live Oak St, Dallas, TX 75204' --database <snapshot>`.
Run `house-account query provider <canonical-provider-id> --database <snapshot>`.

## Driving it with verify.py

Preconditions: Launch and doctor pass with the unchanged supplied pack and an empty disposable review ledger.

- Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py history`.
- The helper imports the real pack, checks provider alias reconciliation, and drives all four public query commands. It compares property evidence IDs and block visit IDs with independently inspected fixture answers. The radius sum is 969 provider/trade job counts. It checks forbidden private field names and markers, plus unchanged logical database state.
- Supplemental `scripts/verify_p2_independent.py` checks source facts and query results through Python. These checks supplement the captured CLI commands.
- Read `result.json`, `query-*.stdout`, `query-*.stderr`, and `independent.json` in the printed evidence directory. Require pass and `scratch_removed: true`.

## Gotchas

- Provider history defaults to three candidate openings that each fit two hours, within November 2 through December 3, 2026 (exclusive), at Chicago midnight. See [Availability and rankings](availability.md) for configurable searches.

- Radius CLI uses a fixed half-mile radius and the November 2, 2024 through November 2, 2026 window. Block CLI uses November 2 through November 16, 2026. Boundaries are Chicago midnight and the end is exclusive.
- Trade groups overlap. The sum of 969 is a fixture assertion, not a count of globally unique jobs.
- Approximate street coordinates and uncertain identities limit coverage. Absence does not establish that a provider lacks experience.
- Canonical IDs come from the imported snapshot. Do not pass a source-local provider ID to the provider query.
- These checks do not prove absence of every possible private value inside an otherwise allowed field.
- Unit alias and exact radius-boundary fixture tests remain supplemental product tests. This feature proves the four real-pack CLI journeys.

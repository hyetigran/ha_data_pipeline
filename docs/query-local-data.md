# Query service history and candidate openings

## Query published history

First, [import a snapshot](start-local-server.md#import-the-snapshot).

Run the command that matches your question. Add `--database <snapshot>` to query a database other than `var/house_account.sqlite`.

```sh
uv run --locked house-account query radius '4512 Live Oak St, Dallas, TX 75204'
uv run --locked house-account query block '4500 Live Oak St, Dallas, TX 75204'
uv run --locked house-account query property '5823 Belmont Ave, Dallas, TX 75206'
uv run --locked house-account query provider 'Lone Star Plumbing'
```

Check the response's coverage and uncertainty fields before using its counts. For property history, distinguish confirmed completed work from other observations. For provider history, distinguish job counts from visit counts.

## Find candidate openings

Run an availability query with the required trade or service.

```sh
uv run --locked house-account query available 75214 --trade handyman --duration-minutes 120
uv run --locked house-account query openings 'Lone Star Plumbing' --limit 3
uv run --locked house-account query recommend 75206 --service water_heater
```

To change the window, pass aware ISO timestamps in `--start` and `--end`. Keep the window within 31 days. To change the duration, pass `--duration-minutes`. To cap the results, pass `--limit`.

If a response reports unknown availability, do not treat the missing opening list as free time. If a recommendation has no eligible provider, inspect the exclusions and duration basis. Use a shorter duration only when that duration matches your request.

Before arranging work, confirm the provider's availability and travel needs. The application returns calendar candidates, not booking confirmations.

For default windows, response meanings, and limits, see the [command reference](command-reference.md). The [scheduling policy](p3-design.md) explains the calculation.

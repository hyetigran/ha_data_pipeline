# Ask questions from the terminal

Use these commands from the project folder after a regular import. They read the regular database at `var/house_account.sqlite`.

If you used `--uat`, add `--database` followed by the actual database path printed by setup. Otherwise these commands read a different database.

To see work at one home:

```sh
uv run --locked house-account query property '5823 Belmont Ave, Dallas, TX 75206'
```

To see work near a home:

```sh
uv run --locked house-account query radius '4512 Live Oak St, Dallas, TX 75204'
```

To see planned visits on a block:

```sh
uv run --locked house-account query block '4500 Live Oak St, Dallas, TX 75204'
```

To see a provider's history and openings:

```sh
uv run --locked house-account query provider 'Lone Star Plumbing'
```

To find handymen with two-hour openings:

```sh
uv run --locked house-account query available 75214 --trade handyman --duration-minutes 120
```

To ask for a water-heater recommendation:

```sh
uv run --locked house-account query recommend 75206 --service water_heater
```

Read the uncertainty and limits in each answer. "No suitable opening found" does not always mean the provider is fully booked. The program may lack enough information.

Do not shorten the requested job time just to get a result. A two-hour request and a four-hour request ask different questions.

---

[Start here](README.md) · [Original document](../docs/query-local-data.md)

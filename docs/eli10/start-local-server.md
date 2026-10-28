# Set up the program and ask your first question

We will prepare the data and connect an assistant to it.

Use a terminal on macOS or Linux. On Windows, use WSL2. You need internet access, `curl`, and the supplied data pack. Claude's installer also needs Bash.

1. Open the terminal in the project folder. Put the supplied pack in `data/`. That folder must contain `README.md`, `sources/`, and `reference/`.
2. Run one setup command. For Codex, use:

```sh
sh setup.sh --client codex --uat
```

For Claude Code, replace `codex` with `claude`. For another client, use `none`.

3. Wait for `Setup complete.` The command prints the database path and the import report path.
4. Open a new session of your selected assistant. For Codex, run:

```sh
codex
```

5. Sign in if asked. In Claude Code, approve the project's `house_account` server when asked.
6. Ask: "Use house_account.get_property_history for 5823 Belmont Ave, Dallas, TX 75206. Treat today as November 2, 2026."
7. Check that the assistant actually calls `get_property_history`. A fresh, unreviewed pack has four confirmed completed jobs for this home.

`--uat` makes a fresh test database. It does not erase your old databases.

Setup installs the program's dependencies and only the client you choose. If you leave out `--client`, it uses `none`. That mode prints settings for another MCP client instead of registering one.

If your supplied pack is outside `data/`, add `--data` followed by its real folder path in quotes. Do not type `/path/to/pack` literally. That is only an example of where your path goes.

If setup fails, read the error before opening the assistant. A failed import does not replace the previous good database.

---

[Start here](README.md) · [Original document](../start-local-server.md)

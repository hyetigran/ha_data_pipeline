# Local MCP tools

The local stdio server exposes six bounded read-only tools for radius history, available providers, block appointments, provider profiles, exact-home history, and recommendations. Typed responses carry snapshot identity, ingestion time, coverage, limitations, and bounded evidence. Tool calls cannot import, apply review decisions, run SQL, or select filesystem paths.

## Public path

Run `uv run --locked house-account --data ./data --as-of 2026-11-02` through an MCP stdio client. Startup prepares a missing snapshot before serving; an existing valid snapshot is reused. Relative windows use the configured reference date, while schedule coverage remains fixed to the supplied pack. Use the README Codex configuration for interactive questions.

## Live verification

Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py mcp`. The owned helper imports into scratch and delegates to `scripts/verify_p4.py`, which copies the supplied disposable snapshot and launches its own server. Doctor runs before delegation; the process group has the helper's 180-second bound.

Require exactly six discovered tools with structured schemas and read-only annotations. All six calls must match direct queries and fixed pack expectations. Invalid arguments must fail without echoing private values. Logical database and source hashes must be unchanged. Read `p4/summary.json`, captured responses, safe-error receipts, and `server.stderr` in the printed unique evidence directory. Require nested and outer scratch removal and clean shutdown. Evidence remains outside scratch.

## Interpretation

Zero eligible providers for the default water-heater request is a valid answer. An explicit shorter duration is a different request and must remain disclosed. Partial/unknown availability is not a booking guarantee. Neighboring addresses, contacts, private notes, and calendar titles are not public fields. Business labels are untrusted data rather than instructions.

The protocol journey proves MCP behavior, not autonomous agent reasoning. The delivery demo separately runs `scripts/demo.py` through actual authenticated Codex, preserving the six natural-language questions, selected tools, and answers. Network access and Codex authentication are prerequisites for that demo. Review semantic correctness independently; process exit 0 is insufficient.

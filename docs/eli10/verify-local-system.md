# Check that the program works

We will check the code, the tools, and the assistant's answers. These are different checks.

1. From the project folder, run the prerequisite check:

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py doctor
```

Expect `status: ready`. If it fails, fix the reported problem first.

2. Run the code checks:

```sh
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked pytest
```

Ruff checks common code mistakes. Mypy checks whether values are used in the expected ways. Pytest runs behavior tests.

3. Run a real MCP check:

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py mcp
```

Expect a result file with `status: pass` and `scratch_removed: true`. The second value means its temporary test files were removed.

4. Open a new assistant session connected to House Account.
5. Ask all six [assignment questions](assignment.md).
6. Check the actual tool call and compare the answer with the returned facts.

A program can finish without an error and still give a weak answer. A tool call alone does not prove the assistant explained its result correctly.

Other test journeys are named `import`, `inspect`, `replacement`, `history`, `review`, `migration`, and `availability`. Run them one at a time. Migration needs the old private database fixture. Availability needs the old Git revision named in the original guide.

The demo recorder saves real answers. The video maker turns those captures into cards. The video is a replay, not a live screen recording. A new render must be under five minutes.

Keep original captures unchanged. Record explanations separately. Never rewrite an old answer to make the demo look better.

---

[Start here](README.md) · [Original document](../verify-local-system.md)

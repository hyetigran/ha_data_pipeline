# Verify the application and capture a Codex demo

## Prepare verification

1. Install the locked dependencies from the repository root.
2. Confirm that the private pack exists under `data/`.
3. Run the verification doctor.

```sh
uv sync --locked
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py doctor
```

Expect `status: ready`, the current checkout's module path, and the supplied pack's file count. If doctor fails, resolve the reported prerequisite before running a journey.

## Check code and mapped behavior

Run the static checks and unit suite.

```sh
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked pytest
```

Run the feature journeys serially. Each helper creates isolated state, checks prerequisites before child commands, and retains evidence after cleanup.

```sh
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py import
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py inspect
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py replacement
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py history
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py review
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py migration
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py availability
UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py mcp
```

For migration, provide the frozen legacy database at `artifacts/P2R/baseline/house_account.sqlite`. A fresh schema-v2 database cannot replace that fixture. Availability also requires the local Git object `c6c151ee3e95706ad178d2d661fc791f6106f616`.

Read `result.json` in each printed evidence directory. Require `status: pass` and `scratch_removed: true`. Check that the referenced command receipts still exist. After a failed journey, run doctor again before a fresh attempt.

For detailed assertions and cleanup rules, use the [verification skill](../.cursor/skills/verify-house-account/SKILL.md) and its [feature map](../.cursor/skills/verify-house-account/features/README.md).

## Check fresh startup and MCP performance

Choose a new output directory for each command.

```sh
uv run --locked python scripts/verify_p4.py --fresh-checkout --output artifacts/P4/fresh-run
uv run --locked python scripts/verify_p4.py --output artifacts/P4/protocol-run --rounds 30
```

The fresh-checkout check requires Git history and access to any dependencies absent from the local cache. Read the summary before claiming startup or performance success. The protocol verifier removes its temporary database.

## Capture actual Codex answers

1. Install and authenticate Codex CLI.
2. Allow network access for the agent session.
3. Import a disposable demo snapshot.
4. Run the demo with a new output directory.

```sh
uv run --locked house-account ingest --data data --database artifacts/P4/demo-input/snapshot.sqlite --ledger artifacts/P4/demo-input/decisions.jsonl
uv run --locked python scripts/demo.py --database artifacts/P4/demo-input/snapshot.sqlite --output artifacts/P4/codex-run
```

Read the captured tool calls and final answers. Confirm that every question uses the relevant domain tool and that the answer follows its evidence. A successful process exit does not prove semantic correctness.

After capture, remove the disposable `artifacts/P4/demo-input/` directory. Keep the capture unchanged. If you find a weak answer, record its exact quote, evidence, and cause separately. Do not rewrite the captured answer to improve the demonstration.

## Render the demo replay

Use a Python environment with Pillow and make `ffmpeg` and `ffprobe` available. Create a review JSON file with `question_id`, `quote`, `root_cause`, and `evidence`. If the weak answer comes from an earlier capture, include `source_transcript`.

```sh
python scripts/render_demo.py --transcript artifacts/P4/codex-run/agent-transcript.json --review artifacts/P4/weak-answer-review.json --output artifacts/P4/demo-render
```

Inspect the generated HTML, cards, video, and render receipt. Label the video as a transcript replay. Check that its duration does not exceed five minutes. Keep private captures and rendered answers outside Git.

## Measure imports and availability

Choose unused output paths. The import benchmark owns its temporary database.

```sh
uv run --locked python scripts/benchmark_p2.py --output artifacts/P2R/new-benchmark.json
```

For availability measurements, import a disposable snapshot and name a new report.

```sh
uv run --locked house-account ingest --data data --database artifacts/P3/perf-run/snapshot.sqlite --ledger artifacts/P3/perf-run/decisions.jsonl
uv run --locked python scripts/benchmark_p3.py --database artifacts/P3/perf-run/snapshot.sqlite --output artifacts/P3/new-benchmark.json
```

After reviewing the measurements, remove the disposable `artifacts/P3/perf-run/` directory. Keep the benchmark reports.

Use the maintained `availability` journey for current P3 regression checks. The original P3 runner compares whole block rows and rejects P4's added fields. The maintained wrapper preserves that receipt and verifies compatibility separately.

For historical results and measurement limits, see the [execution records](README.md#execution-records). Reproducing an old phase's timing requires that phase's source, environment, and input conditions.

## Check the data trap evidence

Create a new evidence directory:

```sh
mkdir -p artifacts/docs-writing/checks
```

Generate a fresh inventory and trap audit. Keep the tracked historical receipts unchanged.

```sh
.venv/bin/python scripts/inspect_data_pack.py > artifacts/docs-writing/checks/data-pack-inventory.json
.venv/bin/python scripts/audit_traps.py > artifacts/docs-writing/checks/trap-evidence.json
.venv/bin/python scripts/audit_traps.py --summary > artifacts/docs-writing/checks/trap-summary.json
.venv/bin/python scripts/verify_trap_candidates.py
```

Compare the new results with [the inspection report](data-pack-inspection.md) and [the historical trap register](trap-register.md). Investigate differences before changing expected counts.

For broader discovery, including service classification, raw timestamp ambiguity, contact/address variants, and calendar corroboration, run `scripts/investigate_traps.py`. The [expanded investigation](trap-discovery-2026-10-27.md#verification-and-reproducibility) gives scratch-snapshot commands and the limits of each search. Neither audit establishes a 22/22 grader-seed count.

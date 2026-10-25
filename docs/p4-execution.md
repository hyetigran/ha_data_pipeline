# P4 execution record

P4 implements the six local read-only MCP tools and the connected Codex demo. The baseline is merged P3 at `313847db86a994095face0818c685ced5c56779e`; product implementation is commit `ad7f2829be899b199f12bd0da68a5eca6ab135d5`. Delivery scripts and documentation follow in a separate commit. P4 remains unmerged for operator review.

## Behavior and scope

The stdio server reuses existing history, availability, and ranking rules. Explicit public response models bound every collection and carry snapshot identity, coverage, provenance, and uncertainty. Every call owns one read-only SQLite transaction. Startup imports missing derived state before serving and rejects invalid existing state without overwriting it.

Completion evidence determines which work can be attributed to a completed visit or job. Broader job scope remains a separate field. Neighborhood answers retain aggregate or block-level locations; only the requested home's history exposes its exact address. Raw notes, contacts, personal calendar titles, and private review evidence stay local. Tool validation and unknown-tool errors do not echo supplied private text.

The grill-me boundaries remain in force. Provider capacity stays conservative, travel stays unmodeled, and candidate openings are not booking promises. This phase adds no live connector, production synchronization, hosting, crew scheduling, or seventh-source parser.

## Verification evidence

Evidence stays in ignored `artifacts/P4/` because it includes the supplied private pack's answers. The committed runners let a reviewer reproduce the checks with that pack.

| Check | Result | Local evidence |
| --- | --- | --- |
| Full regression suite | 109 passed | `final-unit.log` |
| Lint and source types | Passed | `final-lint.log`, `final-types.log` |
| Independent product review | No remaining blocking findings; 14 focused tests passed | `independent-final-review.json` |
| Real stdio protocol | Six tools, fixed pack expectations, direct-query parity, five invalid requests rejected | `final-protocol/summary.json` |
| Data invariants | 176 source files and logical database unchanged; scratch removed | `final-protocol/summary.json` |
| Fresh archived checkout | Locked install, import, discovery, all six calls and shutdown passed | `fresh-checkout-final/summary.json` |
| Actual Codex | Six questions passed required successful domain calls; implementation and data unchanged | `codex-final/agent-transcript.json` |
| Independent answer review | PASS_WITH_NOTES; no blocking findings | `agent-semantic-review.json` |
| Repeatable maintenance | MCP and history helper receipts | `final-maintenance-mcp.log`, `final-maintenance-history.log` |

The ten planned lanes are mapped to these actual runs in `lane-1.json` through `lane-10.json`. They are evidence mappings, not claims that ten independent agents ran. The available local agents supplied architecture alternatives, product review, privacy review, and answer review. Poteto's named external model families, Cursor control tools, and deslop plugin were unavailable. Local protocol/client runs, manual diff cleanup, and independent available agents replace those checks. No live terminal screenshot is claimed.

## Codex demo and weak answer

`scripts/demo.py` launches authenticated ephemeral Codex sessions with temporary MCP configuration. Each question must invoke its expected domain tool successfully. Resource listing alone, an empty answer, or process exit zero cannot pass. Captured JSONL preserves actual tool selections and responses. Inner execution is read-only; persistent Codex configuration is unchanged.

An earlier Q3 answer asked which city and state contained the block after only listing empty MCP resources. The runner initially counted those resource calls as interaction. The fix supplies the dataset's Dallas context and requires the expected successful domain tool. The final run answers the block question through `get_block_schedule`. The earlier weak answer and its exact quote remain in `weak-answer-review.json` and `codex-demo/`.

`demo-review/demo-replay.mp4` is a 240-second labeled replay of captured Codex interaction, not a live screen recording. Eight cards show all six questions and the weak-answer explanation. Long answers are explicitly excerpted on the cards; `demo-review/review.html` contains full verbatim answers and tool selections. `render-receipt.json` records transcript hashes and ffprobe duration. Operator review of that interaction is still pending. No approval or merge is inferred from passing checks.

The answer reviewer notes that Q2's claim of no truncation applies to provider/opening results; bounded evidence-reference lists can still be truncated. Read those metadata fields when assessing provenance.

## Performance

The protocol benchmark measured 30 sequential warm calls per tool after warmup on macOS arm64 with Python 3.13.2. It excludes model latency. The supplied manifest hash is `c4ad29369486c5912697ae1d3c7e2bbde63474ac889810e37cf5d20703b99f79`. All calls succeeded and repeated response hashes were stable within the snapshot.

| Tool | p95 milliseconds |
| --- | ---: |
| Search history | 418.1 |
| Available providers | 522.9 |
| Block schedule | 87.7 |
| Provider profile | 262.3 |
| Property history | 54.6 |
| Recommend provider | 563.1 |

Existing-snapshot initialization took 4.08 seconds with 72.2 MiB peak child memory. The separate fresh archived checkout, including locked environment setup and full import, initialized in 38.56 seconds with 311.4 MiB peak child memory. These local measurements meet the proposed 1-second warm-call, 60-second startup, and 512-MiB targets. They are not production capacity estimates or speedup claims. P3 has no MCP transport, so no comparable parent ratio exists. Concurrent local work and caches can affect timings.

A separate diagnostic profile identifies SQLite execution and evidence-row conversion as material costs. Its instrumentation timings are excluded from the benchmark. The first fresh-checkout attempt could not fetch a build dependency under sandbox DNS restrictions; a network-enabled retry passed. Both attempts remain recorded.

## Scale limits and week-two work

The current system uses full supplied-pack imports, local SQLite, and bounded query horizons. It has no authenticated multi-user authorization layer, production freshness monitoring, or live booking confirmation. Confidence remains ordinal. More worker capacity cannot be inferred from crew size or unverified assignment names.

Week two should first establish source delivery and freshness contracts, authenticated exact-home access, and an operational review workflow. Then validate worker identity and capacity before expanding scheduling. Measure larger datasets and concurrent readers before selecting database or spatial-index changes. Production connectors, incremental sync, travel modeling, and calibration require separate scope and evidence.

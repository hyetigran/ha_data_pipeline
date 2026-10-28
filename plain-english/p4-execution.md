# P4: connect the assistant and check its answers

P4 exposed six read-only MCP tools. Codex used them to answer the six assignment questions.

The original checks included 109 tests, real MCP calls, a fresh checkout, and captured Codex answers. A separate answer review found no blocking problem, but kept notes about limits.

One check ensured each question called the expected tool successfully. Merely starting the process or listing resources was not enough.

## The weak attempt had two separate problems

First, one new conversation did not say the street was in Dallas, Texas. Codex asked for the missing city and state. That was reasonable, but it did not retrieve a schedule.

Second, the checker accepted a resource-list call without requiring the schedule tool. Listing resources does not read scheduled jobs.

The revised prompt gives the location. The revised checker requires `get_block_schedule` to succeed. The answer still needs review against the returned records.

## The video

The original video is a four-minute replay of real captured interaction. It is not a live screen recording and has no audio.

The later explanation revision lasts four minutes and thirty seconds. It has two final cards, starting at three minutes and thirty seconds, that explain the two problems separately. The captured answers remain unchanged.

[Watch the revised replay with its full written answers](../artifacts/P4/demo-review-revised/review.html).

## What the measurements prove

The original local tool calls had reported 95th-percentile times below one second. Those times exclude the AI model's response time.

P4 did not add live CRM updates, travel planning, booking, or checks that a caller owns a home. The server remains a local, read-only data service.

---

[Start here](README.md) · [Original document](../docs/p4-execution.md)

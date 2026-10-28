# P2R: improve the database without losing evidence

P2R changed the database to version 2. It kept source records and existing identity links while making the shared facts easier to query and check.

The program now keeps completed work separate from job status, supports several services per job, and preserves IDs across imports.

It checks a new import before saving the published changes together. Tests also covered backup recovery and failures around the save.

## What the original checks showed

The original final suite passed 73 tests. All 176 source files were unchanged.

The known answers still included four completed jobs at Belmont, four active block appointments, and 262 completed distinct jobs for Lone Star.

The nearby count changed from 971 to 969 because two jobs did not prove that particular listed services were performed. Their job-completion evidence was not erased.

An active recurring cleaning job retained 46 completed visits and two upcoming visits. The ongoing job was not falsely marked finished.

The unclear daylight-saving start time stayed unclear. No real review correction was approved to improve the results.

## Tradeoff

The richer import took more work. Its measured middle import time was about 29 seconds. History queries became faster in those tests, but some answer meanings also changed. The report does not claim a like-for-like speedup.

These are historical local measurements. Availability and MCP tools were added after this stage.

---

[Start here](README.md) · [Original document](../p2r-execution.md)

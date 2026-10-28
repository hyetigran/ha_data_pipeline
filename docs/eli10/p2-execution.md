# P2: match records and answer history questions

P2 added shared provider and home records. It also added history queries and a way for a person to review possible corrections.

A match needed evidence. Similar names alone were not enough. Apartment numbers stayed meaningful. Uncertain dates and completion claims stayed visible.

People could approve, reject, or defer proposals. The real disputed year and house number were left unresolved. Tests used separate copies.

## What the original checks showed

The original P2 suite passed 44 tests. A later audit added more tests.

The original answers included four confirmed jobs at 5823 Belmont, four active block appointments, and 262 completed source jobs for Lone Star Plumbing.

The old nearby-work count was 971. P2R later changed it to 969 supported counts across provider and trade groups. Two jobs lacked evidence for a specific listed service. This was a change in what the count meant.

The P2 snapshot had 43 provider groups, not the 40 profile count. Some source links remained unclear.

## Speed and limits

The original full imports took about ten seconds. The measured history queries usually completed within roughly one tenth of a second at the reported 95th percentile. That means 95 out of 100 measured requests were at or below the reported time.

These were local tests on the supplied data. They do not prove performance with 10,000 providers.

P2 did not yet calculate openings or expose the final MCP tools. Those features came later.

---

[Start here](README.md) · [Original document](../p2-execution.md)

# P1: read the files safely

P1 was the first build stage. It taught the program to read all six source types and the street reference.

It kept source records, counted exact repeats, and noted missing or unclear values. It did not yet match businesses across systems or answer scheduling questions.

The original run read 176 files. It found 46,888 observations of 46,092 different source records. These include customers, homes, and visits, not just jobs.

## What the tests showed then

The original run passed 21 tests. It also checked fresh startup, repeated imports, bad input, and failures during an import.

The checks showed that a failed import preserved the earlier database and that the supplied files stayed unchanged.

The measured import took about 5.8 seconds and used about 61 MiB of memory on the test Mac. That was an early version, not today's full program.

## What came later

P2 added matching and history queries. P3 added openings. P4 added the six MCP tools.

P2R later changed how the database saves updates. Do not use P1's old save rules as the current design.

P1 used a fixed list of expected source files. Adding a new source requires explicit reader and file-list changes.

---

[Start here](README.md) · [Original document](../docs/p1-execution.md)

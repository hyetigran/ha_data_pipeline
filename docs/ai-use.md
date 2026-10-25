# AI assistance and human review

Codex assisted with architecture exploration, implementation, test creation, documentation, and independent review. Parallel agents compared two P4 designs. The selected design reuses the existing domain queries and adds explicit typed public projections rather than a second query engine.

AI-generated code is checked with unit tests, real stdio MCP calls, source/data invariants, and an actual Codex interaction. A scripted protocol client is not presented as an agent demo. The retained transcript records the tools Codex actually chose and their returned evidence. The demo discusses a real weak answer or a documented data limitation without inventing a failure.

The operator controls review decisions and the final P4 merge. No real ambiguous identity or factual correction is approved merely to improve demo answers. Private data, databases, review documents, and local verification evidence remain excluded from Git. The exact verification results and remaining gaps are recorded in the P4 execution report.

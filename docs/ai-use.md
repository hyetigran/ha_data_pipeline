# AI assistance and human review

Codex assisted with architecture comparison, implementation, tests, documentation, and independent review. The P4 design comparison favored existing domain queries with explicit public response models. It avoided a second query engine.

Verification combines unit tests, real CLI commands, stdio MCP calls, and an actual Codex capture. The capture preserves the tools Codex selected and the evidence it received. Protocol success alone does not prove that the agent's answer is correct.

An early demo treated resource listing as sufficient tool use. The revised runner requires a successful call to the expected domain tool. The original weak answer remains in the captured evidence. The [P4 execution record](p4-execution.md) describes the failure and correction.

Human review controls real reconciliation decisions. Test approvals use disposable state. Private data, databases, ledgers, and captured answers remain outside Git. The operator authorized the P4 merge after verification, and PR #4 is merged.

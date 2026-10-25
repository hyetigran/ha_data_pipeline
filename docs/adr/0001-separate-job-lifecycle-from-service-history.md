# Job lifecycle and completed service evidence

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

A recurring job can remain active after several completed visits. Treating any completed visit as a completed job would misstate the remaining work.

The accepted design separates job lifecycle from service completion. Fresh Nest Cleaning job #1034 illustrates the need. Its active job has 46 completed visits, five cancelled visits, and two upcoming visits.

History reports distinct jobs and completed visits separately within the requested window. Job-level completion evidence does not create fictional completed visits. Source-specific lifecycle mappings preserve original statuses. Archived work, pending approvals, and completed estimates do not automatically establish completed service.

Q15 defines separate controlled vocabularies for job lifecycle, visit scheduling state, and estimate state. The [column design record](../schema-columns-draft.md) retains those values.

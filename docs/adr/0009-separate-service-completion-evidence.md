# Separate service completion evidence

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Job lifecycle cannot describe every instance of performed work. Q12 introduces `service_completions` linked to a job and, when supported, a particular visit.

A completion records its evidence basis and service-date qualification. The job can remain active. Job-level evidence does not fabricate a completed visit.

Q20 requires corroborating observations to support one completion rather than inflate visit counts. A service receives credit only when evidence attributes that work to the completion. Otherwise, job-level completion remains available with unknown service attribution.

Distinct jobs and completed visits remain separate counts. Trade groups can overlap, so their sum is not a global distinct-job count.

# Separate job lifecycle from completed service evidence

Accepted in the October 24, 2026 schema interview. A job's lifecycle and its eligibility for service history are separate facts: a recurring job can remain active while completed visits establish past service. This replaces the current inference that any completed visit makes the canonical job completed; history counting and source-specific lifecycle mappings remain to be decided.

Fresh Nest Cleaning Jobber job #1034 is active with 46 completed, five cancelled and two upcoming visits. Preserving lifecycle avoids describing unfinished recurring work as finished while retaining legitimate history.

This is an accepted design decision, not an implemented change.

The operator subsequently accepted exposing both distinct-job and completed-visit counts within the requested window. Do not fabricate completed visits from job-level completion evidence. Lifecycle uses explicit source-specific mappings with original status retained; Jobber active remains active, archived does not automatically mean successfully completed, and insufficient or contradictory evidence remains unknown or flagged as conflicting.

Q15 subsequently accepted separate controlled vocabularies: job lifecycle `open`, `active`, `pending_approval`, `completed`, `cancelled`, `unknown`; visit scheduling state `scheduled`, `in_progress`, `completed`, `cancelled`, `overdue`, `unscheduled`, `superseded`, `unknown`; estimate state `open`, `scheduled`, `in_progress`, `completed`, `cancelled`, `unknown`. Source mappings in the column draft preserve original status and do not promote archived jobs, pending approvals or completed estimates into unsupported completed service. Cross-source conflict selection is still open.

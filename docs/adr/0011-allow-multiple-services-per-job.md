# Related services for jobs and estimates

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

A job or estimate can describe several kinds of work. Q17 uses `job_services` and `estimate_services` instead of one service field on each parent.

Each service has a controlled trade and service pair, a safe description, and a classification state. The allowed states are `mapped`, `unmapped`, and `conflicting`. Incoming free text does not extend the vocabulary.

Multiple service rows avoid forcing combined work into one category. They also require separate completion attribution. Completing one visit does not prove that every listed service happened. Original wording remains private and traceable.

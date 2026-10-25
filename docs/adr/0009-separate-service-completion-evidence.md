# Store service completion evidence separately from lifecycle

Accepted as Q12 in the October 24, 2026 schema interview. A dedicated `service_completions` table records confirmed service evidence linked to a job and optionally a specific visit. It records the basis for completion and the precision/uncertainty of its service date; it does not require the job's lifecycle to be finished and never fabricates completed visits from job-level evidence.

This adds a relationship rather than overloading job status or one completion timestamp. Multiple sources supporting the same completion must remain evidence for that completion, not inflate completed-visit counts. Detailed uniqueness and evidence aggregation rules remain to be specified. No implementation has changed.

Q20 accepted: multiple observations supporting one completion do not inflate completed-visit counts. Credit a particular service only with supporting attribution evidence; otherwise retain completion at job level with service attribution unknown. Distinct job and visit counts remain separate; trade groups may overlap, so sums across groups are not presented as an overall distinct count.

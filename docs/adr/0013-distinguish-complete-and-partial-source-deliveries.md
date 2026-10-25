# Distinguish complete snapshots from partial changes

Accepted as Q25 in the October 24, 2026 schema interview. Every source delivery declares its source/account, collection and coverage scope, and whether it is a complete snapshot or a partial change batch. Omission can establish disappearance only from a verified complete snapshot and only within that snapshot's declared scope. Partial batches require explicit removal evidence; an omitted record remains unchanged.

A job missing from a complete weekly schedule is absent from that schedule scope, not necessarily deleted or cancelled: it may have moved outside the window. Preserve historical assertions. Explicit source deletion retires a source assertion rather than erasing its history or automatically deleting a canonical entity supported elsewhere. Cancellation remains a business-status update.

Completeness must be established by the adapter contract and validated delivery evidence, not trusted solely because a payload says all_pages_received=true. Source consistency during pagination, revision ordering and publication/checkpoint rules remain to be designed. The JSON examples in the conversation illustrate the contract and do not define implemented API payloads. No runtime change has occurred.

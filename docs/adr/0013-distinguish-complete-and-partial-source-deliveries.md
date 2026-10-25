# Complete snapshots and partial changes

The decision was accepted on October 24, 2026 as a production requirement. It is not part of the local full-pack importer.

## Decision and reason

A missing record has different meanings in a complete snapshot and a partial change batch. Q25 requires each delivery to identify its source account, collection, coverage scope, and completeness.

Verified complete coverage can establish disappearance only within that scope. Partial deliveries leave omitted records unchanged unless explicit removal evidence exists.

An appointment absent from a weekly schedule may have moved outside the week. That absence does not establish cancellation or deletion. Explicit deletion retires a source assertion while preserving history and identities supported elsewhere.

Completeness comes from the adapter contract and validated evidence. A payload's `all_pages_received=true` value alone is insufficient. This production contract remains unimplemented. Conversation examples do not define a runtime API.

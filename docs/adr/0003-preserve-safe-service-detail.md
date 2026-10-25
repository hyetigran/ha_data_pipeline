# Controlled service categories and safe descriptions

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Service answers need enough detail to explain what happened without exposing source notes. The earlier mapping of "gate fix" to "other" lost useful work detail.

Canonical services combine a controlled category with a description built from recognized facts and approved wording. Original free text remains private. Lineage records how the normalized description was derived.

Unrecognized work receives a generic description and an unmapped-service issue. The system neither copies private text into the response nor invents a more specific repair. This policy preserves useful detail while limiting disclosure.

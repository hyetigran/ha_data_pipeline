# Review reconciliation proposals

Use this guide to approve, reject, defer, or reverse a proposed identity match or factual correction. Review files contain private evidence. Keep them outside version control.

## Export and edit proposals

1. Import the current source pack.
2. Export the proposals.

```sh
uv run --locked house-account review export --file review/reconciliation.json
```

3. Edit only each proposal's `human` object.
4. Set `decision` to `approve`, `reject`, or `defer`.
5. For an explicit decision, supply `reviewer`, a UTC `decided_at`, and `reason`.

Do not edit generated proposal IDs, source hashes, actions, or evidence. Missing decisions remain deferred. The [review schema](../schemas/reconciliation-review.schema.json) defines the allowed fields.

## Validate and preview changes

Run validation, then request a preview.

```sh
uv run --locked house-account review validate --file review/reconciliation.json
uv run --locked house-account review apply --file review/reconciliation.json --dry-run
```

Inspect the proposed changes. If validation reports stale evidence or conflicting decisions, export the current proposals and resolve the reported problem before applying them.

A preview builds temporary state and can create lock files. Confirm that the preview leaves the published database and the decision ledger unchanged.

## Apply the decisions

After reviewing the preview, apply the file.

```sh
uv run --locked house-account review apply --file review/reconciliation.json
```

If the command reports `recorded_not_applied`, rerun ingestion with the same ledger. Do not delete the recorded decision to recover.

To verify the result, query the affected property or provider. Start a new read transaction to see the published revision.

## Reverse a decision

1. Export the current proposals.
2. Replace the proposal's `human` object with a new decision and reason.
3. Set `supersedes_decision_id` to the proposal's latest ledger decision ID.
4. Validate the file.
5. Preview the change.
6. Apply the file after reviewing the preview.

For a paired year correction, approve or supersede both endpoints together. To keep a real correction unresolved, leave it deferred.

For decision semantics and recovery guarantees, see the [command reference](command-reference.md#review-decisions) and [data model](data-model.md).

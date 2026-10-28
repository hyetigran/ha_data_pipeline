# Review a proposed correction

Use this guide when the program has a possible match or correction that needs a person to decide.

These commands use the regular database and review log. For UAT, use the database and ledger paths from that UAT run instead. Keep review files private.

1. Export the proposals:

```sh
uv run --locked house-account review export --file review/reconciliation.json
```

2. Open the file. Edit only each proposal's `human` section.
3. Choose `approve`, `reject`, or `defer`. Add your name, the decision time in UTC, and a reason for an explicit decision.
4. Check the file:

```sh
uv run --locked house-account review validate --file review/reconciliation.json
```

5. Preview the change:

```sh
uv run --locked house-account review apply --file review/reconciliation.json --dry-run
```

6. Read the preview. If it is correct, apply it:

```sh
uv run --locked house-account review apply --file review/reconciliation.json
```

7. Ask the affected question again and check the result.

Do not change the generated evidence, proposal IDs, or source checks. If the evidence is stale, export again and review the new evidence.

For a wrong-year proposal with start and end times, treat both times together.

To reverse a decision, create a new decision that names the old one in `supersedes_decision_id`. Keep the old decision in the history.

If you see `recorded_not_applied`, keep the decision log. Rerun the import with the same database and ledger paths.

---

[Start here](README.md) · [Original document](../review-reconciliation.md)

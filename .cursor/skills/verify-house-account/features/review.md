# Reconciliation review

Export private proposals, edit human decisions, preview their effects, apply them, and reverse an earlier decision without changing original source evidence.

## Sub-features

- `review-export` exports deferred proposals with private permissions and preserves human edits on re-export.
- `review-validate` checks generated evidence and human attribution.
- `review-preview` reports changes without publishing facts or appending ledger events.
- `review-apply` exercises approve, reject, and defer decisions in disposable state and checks exact correction effects.
- `review-repeat` records no duplicate events on repeated application.
- `review-reverse` supersedes approval with defer and restores the original derived facts.
- `review-stale` rejects a changed source pack without changing the published database or ledger.

## How to get to it (user POV)

Run `house-account review export --data <pack> --database <snapshot> --file <review.json> --ledger <decisions.jsonl>`.
Edit only each proposal's `human` object. Explicit decisions need reviewer, UTC decided_at, and reason.
Run `house-account review validate`, `house-account review apply --dry-run`, and then `house-account review apply` with those same path arguments.
To reverse a decision, set supersedes_decision_id to its latest ledger event and provide a new decision and reason.

## Driving it with verify.py

Preconditions: Launch and doctor pass. The supplied pack must contain field corrections and enough other proposals to exercise reject and defer. The helper fails if those examples are absent.

- Run `UV_CACHE_DIR=/tmp/house-account-uv-cache uv run python .cursor/skills/verify-house-account/scripts/verify.py review`.
- The helper imports a fresh database with an empty scratch ledger. It exports proposals, edits human fields in scratch, and drives every review command through the public CLI.
- For validate and both previews, compare a full SQLite logical digest and ledger contents before and after. Check candidate directories have been removed. Preview may create lock files and temporary candidates. It does not promise zero filesystem writes.
- After apply, read corrected address and interval fields from SQLite. After repeat, require zero new decisions and identical ledger bytes. After supersession, require original field values. Change one copied source record and require validation exit 1 with unchanged logical state and ledger.
- Read `result.json` and `review-*.stdout` and stderr at the printed evidence path. Require pass, all expected exits, and `scratch_removed: true`.

## Gotchas

- These approvals exist only in disposable verification state. They never approve the user's Lakewood or Ray proposals.
- The private review document and ledger contain evidence and attribution. Keep them in scratch and do not attach them to a PR.
- Dry-run rebuilds a candidate and takes maintenance locks. Its no-publication guarantee needs a WAL-aware database comparison.
- The ledger is application history, not authenticated tamper-proof audit storage.
- A recorded_not_applied error requires recovery with the same ledger. This journey does not inject a crash between recording and publication.

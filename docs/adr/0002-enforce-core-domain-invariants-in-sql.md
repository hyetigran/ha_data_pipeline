# SQL constraints for domain facts

The decision was accepted on October 24, 2026. P2R implements the local model described here. The [P2R execution record](../p2r-execution.md) records verification.

## Decision and reason

Database constraints enforce core relationships and controlled canonical values. Python interprets source formats and represents uncertainty. Unknown raw values remain source evidence rather than extending canonical vocabularies.

This choice adds schema and migration work. In return, an adapter cannot silently publish invalid parent links or unsupported canonical states. The executable constraints live in `src/house_account/schema.py` and `src/house_account/storage.py`.

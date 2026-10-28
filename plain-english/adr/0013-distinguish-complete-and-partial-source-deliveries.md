# An omitted record is not always gone

A partial update may contain only changed appointments. An appointment missing from that update has not necessarily changed.

A complete weekly schedule says more, but only about that week. A missing visit may have moved to another week instead of being cancelled.

A future live-update system must know what each delivery covers and whether it is complete. Explicit deletion, cancellation, and simple omission mean different things.

This is a planned production rule. The current full-pack importer does not implement a live-update system.

---

[Start here](../README.md) · [Original document](../../docs/adr/0013-distinguish-complete-and-partial-source-deliveries.md)

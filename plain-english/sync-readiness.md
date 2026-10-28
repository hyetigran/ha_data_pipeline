# What live updates would need

Today the program imports a supplied set of files. It does not watch real business systems for changes.

A live version would need rules for updates, missing records, delays, and failures. These rules are planned, not built.

## A missing record does not always mean deletion

Suppose Monday's update lists only two changed appointments. Every other appointment is missing from that update. That does not mean the others were cancelled.

Even a full weekly schedule only describes that week. A missing appointment may have moved to next week.

## Older updates must not replace newer facts

An update can arrive late. Arrival time alone does not prove it is the latest version.

The source must provide a way to compare versions. Conflicts need to stay visible when the order cannot be proved.

## Repeating an update must be safe

A system may retry after a connection problem. The same update should not create another copy of the job.

The saved progress marker must agree with the saved data. The program must not claim an update is finished before its changes are saved.

## One failure should not stop every business

If one provider's update fails, keep its last good data and show that it is old. Other providers should still be able to update.

Freshness must be tracked for each source. One successful update must not hide another source's failure.

Old or failed updates must not make a provider look free.

Before calling this production-ready, test retries, late updates, missing pages, deletions, interrupted saves, and recovery. The local full-import tests do not prove those live behaviors.

---

[Start here](README.md) · [Original document](../docs/sync-readiness.md)

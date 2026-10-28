# P3: find possible openings and rank providers

P3 added opening searches and provider recommendations. It used the existing stored facts and did not require a new database service.

It removed busy and uncertain time from working hours. It handled repeated events, vacations, cancelled events, estimates, and work outside the target area.

## What the original checks showed

The original suite passed 95 tests. Real command checks and a separate minute-by-minute check supported the availability results.

For the fresh, unreviewed pack:

- Three handymen had relevant ZIP 75214 history and two-hour candidate openings in the next three days.
- Lone Star's first three two-hour openings started November 17, 18, and 20.
- The default water-heater request near ZIP 75206 found no eligible provider that week.
- An explicit two-hour water-heater request found two providers. That is a different request, not a fix for the first answer.

Ray and Abrams still had unresolved source links. Their real answers kept that uncertainty. Separate test copies checked their calendar rules without approving those real links.

## Limits

Travel and separate worker schedules were not calculated. Missing hours and times stayed visible. A candidate opening was not a booking promise.

The largest reported 95th-percentile query time was about 143 milliseconds on the local test machine. That is not a production capacity promise.

P3 was merged. The MCP server and agent demo followed in P4.

---

[Start here](README.md) · [Original document](../p3-execution.md)

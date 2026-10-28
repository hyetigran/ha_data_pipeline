# How the program finds an opening

An opening is a stretch of time when the provider says it works and the records show no busy or uncertain time.

Example: a provider works from 9 to 5. It has a job from 10 to 12 and a blocked calendar event from 2 to 3.

That leaves possible gaps from 9 to 10, 12 to 2, and 3 to 5. The last two gaps fit a two-hour request. This example does not include travel.

## What removes time

Work visits, estimate visits, and blocking calendar events remove time. A job outside the target ZIP still takes time.

Vacations remove time too. An all-day event ending on November 9 blocks the days before November 9, not November 9 itself.

Cancelled events do not block time. Events marked as not busy do not block time. Tentative holds marked busy do block time.

Repeated events are expanded only for the requested dates. Overlapping busy periods count once.

## What the program does not know

Missing working hours do not mean the provider is free. An appointment with unclear times can also make a period unknown.

Crew size does not prove how many jobs a business can do at once. The program uses one conservative schedule per business.

Travel is not calculated. These are possible openings, not booking promises.

## How providers are ranked

A provider must offer the right kind of work, serve the area, and have enough time. Explicit service exclusions are respected.

The score then gives up to 40 points for relevant completed jobs, 20 for area evidence, 25 for how soon an opening occurs, and 15 for schedule confidence.

An earlier opening can rank higher. Relevant completed work improves the score, but a provider can qualify with no recorded jobs for that exact service.

The confidence score is a rule-based label. It is not a tested chance of success. A score of 80 does not mean an 80% booking success rate.

## How long the work takes

A time supplied by the caller comes first. Otherwise the program can use the middle scheduled length from at least three suitable completed visits. Scheduled time is not measured hands-on work time.

Without enough evidence, water-heater work uses a stated four-hour demo assumption. It does not claim every replacement takes four hours.

The dataset's schedule covers November 2 through December 2, 2026. The program cannot promise openings after that coverage ends.

---

[Start here](README.md) · [Original document](../docs/p3-design.md)

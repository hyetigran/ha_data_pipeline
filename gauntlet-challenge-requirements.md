# Gauntlet Challenge: Home Services Data Layer + MCP Server

## Context

Turn messy home service job data from several sources into one clean model, then expose it through an MCP server an AI agent can query.

- HouseAccount connects homeowners with trusted local service providers (handymen, plumbers, HVAC, cleaners, and more).
- Providers run their businesses in many different tools: field service CRMs, spreadsheets, shared calendars. Every tool stores jobs differently.
- We want one answer to a homeowner's real questions: who near me has done this kind of work, what is already scheduled on my street, and who can come this week.
- AI agents (ours and our partners') will ask those questions. The MCP server is how they ask.

We care as much about how you think as what you ship.

## The challenge

Build a working pipeline from raw provider data to an agent-ready MCP server, covering three data types: past jobs, upcoming jobs, and availability.

1. **Ingest.** Pull in every source in the data pack. Write each source as its own adapter so a new source can be added without touching the core.
2. **Normalize.** Design one canonical model for providers, homeowner properties, jobs, and availability. Resolve duplicates across sources. Keep track of where every record came from.
3. **Expose.** Stand up an MCP server with tools an AI agent can call to answer the questions in this brief. Tool names, parameters, and descriptions are part of the work.
4. **Explain.** Write up the decisions you made, what you skipped, and what you would build next.

We are deliberately not giving you a schema, a stack, or a definition of availability. Those choices are part of what we are evaluating.

## The data

You get a synthetic data pack: 6 sources, 40 providers, about 8,000 jobs of history across roughly 3,600 Dallas-area homes, plus about 3,800 jobs scheduled in the next 30 days. History covers 2 years in 9 target zip codes. Schedules are complete, including work outside those zips.

Treat "today" as 2026-11-02 so everyone's availability answers line up. A street reference file is included, so no outside geocoder is needed.

| Source                           | Format          | What it holds                                   | What makes it hard                                                           |
| -------------------------------- | --------------- | ----------------------------------------------- | ---------------------------------------------------------------------------- |
| CRM A (modeled on Jobber)        | Nested JSON     | Clients, properties, jobs, visits               | One job can have many visits. Recurring work. UTC timestamps.                |
| CRM B (modeled on Housecall Pro) | Paged REST JSON | Customers, jobs, estimates, schedule            | Estimates mixed in with jobs. Local times with no time zone. Money in cents. |
| CRM C (modeled on Workiz)        | REST JSON       | Jobs with status codes                          | Its own status vocabulary. Free-text job types.                              |
| Spreadsheet export               | CSV             | A solo handyman's job log                       | Free-text addresses, loose dates, duplicate rows, blank cells.               |
| Calendar feed                    | ICS             | Two providers' calendars                        | Personal events mixed in. All-day blocks. Recurring events.                  |
| Provider profiles                | JSON            | Declared service area, hours, crew size, trades | Sometimes disagrees with what the calendar and CRM show.                     |

Known traps, on purpose:

- The same provider shows up in more than one source.
- The same home shows up under several providers with different address spellings ("Apt 4" vs "#4", "St" vs "Street", missing zip).
- Jobs get cancelled, rescheduled, or left in limbo.
- Records include homeowner names, phones, and emails.

There are a few traps we did not list. Finding them counts.

## Questions the server must answer

An agent connected to your MCP server should answer all six correctly. How you split them into tools is up to you.

1. What home services have been done within half a mile of 4512 Live Oak St, Dallas, TX 75204 in the last 24 months, grouped by trade?
2. Which handymen have done work in zip 75214 and have an opening of at least 2 hours in the next 3 days?
3. What work is already scheduled on the 4500 block of Live Oak St in the next 14 days?
4. Show me everything we know about Lone Star Plumbing: trades, service area, job history, and next 3 openings.
5. Has any provider serviced 5823 Belmont Ave, Dallas, TX 75206 before? Who, when, and what was done?
6. Which plumber near 75206 is the best fit for a water heater replacement this week, and why?

Question 6 has no single right answer. We want to see how you rank and how you explain the ranking.

## Requirements and guardrails

The server is read-only and privacy-aware by default. Everything else is your call.

### Must have

- Read-only. No tool writes back to any source.
- Every record carries provenance: which source, when ingested, and how confident you are in any match or merge.
- Homeowner PII never leaves the server by default. Decide what an agent can see (street, block, zip) and defend it.
- Times are correct for Dallas (Central time), including records that arrive with no time zone.
- Runs locally with one command. Any language, any storage.
- Tool descriptions are written for an LLM, not a human developer.

### Out of scope

- Booking, payments, or messaging.
- A user interface. An agent chat is the interface.
- Live API calls to real CRMs. Use the data pack only.

## Deliverables

Submit four things by the end of day 2.

| Deliverable            | What we expect                                                                                                        |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Repo                   | Code, one-command setup, tests for the normalization logic.                                                           |
| Data model doc         | Your canonical schema, how you resolve duplicates, how you define availability, and why. One to two pages.            |
| Demo video (5 min max) | An agent connected to your server answering all six questions. Show at least one wrong or weak answer and explain it. |
| Decision log           | What you chose, what you cut, what breaks at 10,000 providers, and what you would build in week 2.                    |

## How we evaluate

Judgment counts for more than polish. A smaller system with sharp reasoning beats a big one with none.

| Area                       | Weight | What good looks like                                                                                  |
| -------------------------- | ------ | ----------------------------------------------------------------------------------------------------- |
| Data model                 | 25%    | One clear model that handles all six sources without special cases leaking into it.                   |
| Normalization and matching | 20%    | Duplicates resolved with a stated method and confidence. Traps found, including ones we did not list. |
| MCP tool design            | 20%    | Tools an agent picks correctly on the first try. Clear names, tight parameters, useful errors.        |
| Availability reasoning     | 15%    | A defensible definition that handles conflicting sources and says how sure it is.                     |
| Privacy and provenance     | 10%    | Sensible PII defaults. Every answer traceable to its source.                                          |
| Communication              | 10%    | Honest write-up. Knows what is weak and says so.                                                      |

## Stretch goals

Only after the core works. Pick one, not all.

- **Eval harness.** A scripted set of agent questions with expected answers, run against your server, with a pass rate.
- **New source in under an hour.** We hand you a seventh source on day 2. Show how fast your adapter pattern absorbs it.
- **Incremental sync.** Re-ingest a changed source without rebuilding everything. Handle a job that moved from upcoming to completed.
- **Access tiers.** Two levels of detail (internal vs partner) enforced by the server, not the agent.

## Logistics and rules

- **AI tools:** use anything you want. Include a short note on how you used AI and where it got things wrong.
- **Questions:** ask Ryan.
- **Data:** the pack is synthetic. Do not use real customer data or call real CRM APIs.

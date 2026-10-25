# Home services challenge requirements

This reference summarizes the supplied challenge brief. The six questions below retain their original wording. The [delivery plan](docs/project-plan.md) records the implementation scope and status.

## Product contract

HouseAccount combines provider data so an agent can answer questions about completed work, upcoming jobs, and availability. The challenge requires adapters for every supplied source, one canonical model, duplicate resolution, provenance, and a local MCP server.

The server is read-only. It does not book work, take payments, send messages, or call live CRM APIs. Agent chat is the interface. A separate product UI is outside scope.

## Supplied data

The brief describes six source families, 40 providers, about 8,000 historical jobs, roughly 3,600 homes, and about 3,800 upcoming jobs. These are advertised approximations, not normalized entity counts. The [inspection report](docs/data-pack-inspection.md) contains measured counts and the inventory command.

Historical coverage spans two years in nine Dallas postal codes. Upcoming schedules include out-of-area work. The challenge reference date is November 2, 2026. A supplied street reference supports approximate geocoding without an external service.

| Source | Format | Relevant differences |
| --- | --- | --- |
| Jobber | Nested JSON | Clients, properties, jobs, recurring visits, and UTC timestamps |
| Housecall Pro | Paged JSON | Jobs, estimates, unzoned local schedules, and integer-cent amounts |
| Workiz | JSON | Source-specific statuses and free-text job types |
| Spreadsheet | CSV | Loose addresses and dates, repeated rows, and missing values |
| Calendar | ICS | Personal events, all-day blocks, and recurrence |
| Provider profiles | JSON | Declared service areas, hours, crew sizes, and trades |

The brief identifies provider duplicates, address variants, cancelled or unresolved jobs, and homeowner contact information as expected normalization problems. Additional traps are undisclosed.

## Required agent questions

1. What home services have been done within half a mile of 4512 Live Oak St, Dallas, TX 75204 in the last 24 months, grouped by trade?
2. Which handymen have done work in zip 75214 and have an opening of at least 2 hours in the next 3 days?
3. What work is already scheduled on the 4500 block of Live Oak St in the next 14 days?
4. Show me everything we know about Lone Star Plumbing: trades, service area, job history, and next 3 openings.
5. Has any provider serviced 5823 Belmont Ave, Dallas, TX 75206 before? Who, when, and what was done?
6. Which plumber near 75206 is the best fit for a water heater replacement this week, and why?

Question 6 has no single prescribed answer. The evaluation considers the ranking method and its explanation.

## Required behavior

- Each record has source provenance, ingestion time, and match confidence.
- Homeowner PII stays private by default. The implementation defines and justifies location detail exposed to agents.
- Dallas time handling includes unzoned timestamps and daylight-saving transitions.
- The system runs locally with one command.
- Tool descriptions support agent selection and parameter use.
- Source files remain unchanged.

## Deliverables

The original deadline was the end of day two.

| Deliverable | Required contents |
| --- | --- |
| Repository | Code, one-command setup, and normalization tests |
| Data model document | Canonical schema, duplicate policy, availability definition, and rationale in one or two pages |
| Demo video | At most five minutes, all six connected-agent questions, and one explained weak or wrong answer |
| Decision log | Choices, omissions, limits at 10,000 providers, and proposed week-two work |

## Evaluation weights

| Area | Weight | Evaluation focus |
| --- | ---: | --- |
| Data model | 25% | One model for all sources with clear boundaries |
| Normalization and matching | 20% | Stated matching method, confidence, and trap detection |
| MCP tool design | 20% | Correct tool selection, bounded parameters, and useful errors |
| Availability reasoning | 15% | Conflict handling and stated uncertainty |
| Privacy and provenance | 10% | Private defaults and traceable answers |
| Communication | 10% | Accurate claims and explicit limitations |

## Optional extensions

The brief permits one stretch goal after the core works: scripted agent evaluation, a seventh-source adapter, incremental synchronization, or server-enforced access tiers. It does not require all four.

## Logistics

AI tools are allowed with a note about their use and mistakes. Ryan is the contact for challenge questions. The supplied pack is synthetic. Real customer data and live CRM calls are outside the challenge.

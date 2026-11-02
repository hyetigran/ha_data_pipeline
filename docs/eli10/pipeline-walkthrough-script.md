# Four-stage pipeline walkthrough

*Read-aloud script, approximately two minutes.*

“Our pipeline helps homeowners find contractors with relevant experience and
possible openings. Today, it uses six sources around Dallas. A production
version could add CRMs like ServiceTitan and serve homes nationwide, with more
integrations and broader location support.

## Stage one: Collect the records

We read exported files and preserve their originals. In production, providers
would connect their accounts, and each CRM connector would regularly collect
changes.

The challenge is handling missing pages, duplicates, and outages. Failed imports
already preserve the last successful data. At scale, we would need reliable
retries and freshness checks so an old schedule does not look current.

## Stage two: Organize the facts

We standardize addresses, services, money, and times, then match records for the
same business, home, or job. Jobs describe work; visits describe appointments.
Estimates do not prove completed work.

Nationwide, matching must account for different cities, apartments, and time
zones. Uncertain matches need human review. At scale, those reviews can pile up,
matching gets slower, and frequent writes could outgrow our SQLite setup.

## Stage three: Calculate availability

We subtract visits, scheduled estimates, and calendar blocks from working hours,
then rank providers by experience, location, and available time.

The challenge is disagreement: an empty CRM schedule might hide a vacation.
Production schedules also change constantly. Travel, crew assignments, and a
final availability check would be needed before booking. Our current openings
are possibilities, not guarantees.

## Stage four: Answer through MCP tools

Six named tools let the assistant ask questions and receive facts, evidence, and
uncertainty without private contacts or notes.

The challenge is preventing misleading answers and privacy leaks. A production
application would need sign-in, permission checks, and monitoring as query
traffic grows. It must also tell users when data is stale or results are
incomplete. Today, access is trusted and local.”

---

Technical references: [Architecture](../ARCHITECTURE.md) and [production sync
requirements](../docs/sync-readiness.md).

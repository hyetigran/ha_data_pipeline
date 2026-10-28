# Mistakes the data can hide

This is a simple version of an audit made during P2. Later stages added scheduling and MCP behavior. Old "not built yet" notes do not describe today's whole program.

The audit found evidence for all six examples named in the challenge discussion. It did not prove that all 22 hidden traps were found. The labels below are the team's own labels.

## The six named examples

| Trap | What can go wrong | Safe interpretation |
| --- | --- | --- |
| T01: renamed business | Two names look like two businesses. | Use phone and trade evidence to link supported aliases. |
| T02: wrong year | A completed job appears scheduled in the future. | Keep the conflict and ask a person to review the proposed year. |
| T03: repeated clock hour | 1:30 happens twice when clocks move back. | Do not choose one time without evidence. |
| T04: vacation | The work calendar is empty, but a personal calendar blocks the week. | A linked vacation must block those days. |
| T05: swapped house digits | Work may be attached to the wrong home. | Propose the correction instead of changing it silently. |
| T06: repeated API page row | The same job is read twice. | Count the source job once and keep both input locations. |

## Other problems found

| Labels | Problem and rule |
| --- | --- |
| T07–T08 | One business can appear in several systems. Similar names can also belong to different businesses. |
| T09–T11 | Address spellings vary. Keep apartments separate. Do not invent a location for an unsupported street typo. |
| T12 | Exact repeated spreadsheet rows count once. |
| T13–T14 | Missing years, times, and durations stay uncertain. |
| T15 | Payment, rescheduling notes, and silence do not prove completed work. |
| T16 | One job can have several visits. Do not confuse their counts. |
| T17 | A finished estimate is not finished service work. |
| T18 | "Done Pending Approval" is not confirmed completion. |
| T19 | An incomplete appointment time does not mean zero busy time. |
| T20 | Some prices use cents and others use dollars. Convert exactly. |
| T21–T22 | Dallas time changes with daylight saving. Repeated events must keep the correct local time. |
| T23 | A busy tentative hold blocks time. A non-busy event does not. |
| T24 | Personal or address-free calendar events can still block time. Hide their private titles. |
| T25 | Some calendars and spreadsheets cannot yet be safely linked to profiles. |
| T26 | Emergency-only hours do not promise routine service all day. |
| T27 | A provider's explicit service exclusions matter. |
| T28 | Work outside the target area still occupies time. |
| T29 | Crew size alone does not prove separate worker capacity. |
| T30 | Contact details and notes remain private. Shared contacts do not prove the same home. |

## Why the clock example matters

On November 1, 2026, the recorded Dallas start time of 1:30 a.m. has two possible meanings. The program leaves the exact start unresolved.

Separate completion evidence can still prove the work happened. Unclear timing is not the same as unclear completion.

The 40 profiles become 43 shared provider identities because some links remain uncertain. Forcing the count to 40 would hide that uncertainty.

---

[Start here](README.md) · [Original document](../trap-register.md)

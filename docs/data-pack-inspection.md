# Supplied data pack inspection

The inspection read all JSON source files, the spreadsheet, the street reference, and both calendars on October 24, 2026. No source file was changed. The inspection measures source records, not deduplicated providers, homes, jobs, or answers.

`scripts/inspect_data_pack.py` generates the [inventory](data-pack-inventory.json). The [verification guide](verify-local-system.md#check-the-data-trap-evidence) describes reproduction. The report contains relative file paths, byte sizes, SHA-256 hashes, raw counts, status distributions, repeated source IDs, and calendar property counts. It excludes customer payloads.

## Source counts

| Measure | Observed count |
| --- | ---: |
| Files including README and reference | 176 |
| Total bytes | 21,292,274 |
| Jobber accounts | 15 |
| Jobber clients and property nodes | 2,964 each |
| Jobber jobs | 4,267 |
| Jobber visits | 7,658 |
| Housecall Pro accounts | 15 |
| Housecall Pro customer rows | 3,551 |
| Housecall Pro job rows | 4,633 |
| Housecall Pro account-scoped unique job IDs | 4,630 |
| Housecall Pro estimates | 689 |
| Scheduled Housecall Pro estimates | 131 |
| Workiz accounts | 11 |
| Workiz jobs | 2,657 |
| Spreadsheet data rows | 206 |
| Spreadsheet exact duplicate rows beyond the first copy | 8 |
| Calendar events | 91 |
| Recurring calendar event definitions | 3 |
| Provider profiles | 40 |
| Street segments | 354 |

All Housecall Pro page sets passed a check that their file count matches each page's total_pages field. All Workiz jobs files passed found equals row count and has_more equals false. These are structural checks, not proof that upstream exports contain every real-world record.

## Source formats

Jobber exports use data.account, data.clients.nodes, nested properties.nodes, data.jobs.nodes, and nested visits.nodes. Extensions include exportedAt. Jobs carry dollar-denominated string totals. Visits carry UTC times, their own status, completedAt, and assignedUsers. Job statuses include archived, upcoming, today, action_required, active, requires_invoicing, and unscheduled. Visit statuses include COMPLETED, UPCOMING, CANCELLED, TODAY, OVERDUE, and UNSCHEDULED. Archived is not a sufficient completion test by itself.

Housecall Pro uses company.json plus page-numbered customer, job, and estimate files. Jobs contain embedded customer and address objects, a schedule object with unzoned local timestamps, work_timestamps, integer total_amount, assigned_employees, and original_estimate_id. Estimates also have schedules and employees. Of 689 estimates, 558 have complete rated or complete unrated status. Those statuses describe estimates and must not enter completed-service counts. The other 131 are scheduled and require occupancy treatment.

Three Housecall Pro accounts repeat one identical job payload across pages 2 and 3. They are lone_star_plumbing_co_llc, dallas_drain_pros, and cool_breeze_ac_heat. Exact source IDs are in the inventory. These 4,633 rows represent 4,630 source jobs before cross-source matching.

Workiz jobs.json wraps rows in data with flag, found, and has_more. Rows use UUID, SerialId, ClientId, JobDateTime, JobEndDateTime, LastStatusUpdate, Status, JobType, Team, and JobTotalPrice. Account timezone is US/Central. Prices include integer-like strings, decimal strings, and dollar-prefixed strings. Observed statuses are Done, Pending, Canceled, Submitted, and Done Pending Approval. The last status occurs seven times. Pending approval does not establish confirmed completion.

The spreadsheet's first two rows are title and export metadata. Physical row 3 contains Date, Time, Customer, Phone, Address, Job, $, Paid?, and Notes. It has no stable job ID or explicit end-time column. Physical row locators identify individual observations. Content fingerprints identify repeated records. Notes include cancellation, reschedule, unaccepted work, waiting-on-parts, and unresolved markers. Dates include yearless values and weekday phrases. The rows do not establish durations or completion. The current system clock is not their reference date.

## Provider identity evidence

Big D Handyman and Lakewood Home Repair share a normalized business phone in their Jobber account records. Lone Star Plumbing in Workiz shares a normalized business phone with Lone Star Plumbing Co LLC in Housecall Pro. These observations support alias investigation. They do not authorize merging all records with similar names.

The 41 CRM accounts and Ray's spreadsheet do not establish 42 distinct businesses. The 40 profile rows also do not prove a correct final provider count. Source account identity and matching evidence are independent of canonical IDs.

## Calendar semantics

Abrams has 45 events. Ray has 46. Every event supplies UID, DTSTART, DTEND, DTSTAMP, SUMMARY, STATUS, and TRANSP. There are 75 TZID starts, 15 UTC starts, and one date-only start. Thirty-seven events lack LOCATION. Missing location must not discard busy time.

| Source | Observed case | Required behavior |
| --- | --- | --- |
| Abrams calendar | All-day block starts November 4 and ends November 9. | Block November 4 through 8. The end date is exclusive. |
| Abrams calendar | Friday 07:00 to 08:00 recurrence without UNTIL. | Expand only within the query horizon. |
| Abrams calendar | Thursday 16:30 to 18:00 recurrence with UTC UNTIL. | Apply timezone-aware recurrence and intersect with working hours. |
| Ray calendar | Weekday 15:00 to 15:45 recurrence through May 2027. | Block its overlapping occurrences while hiding the personal title. |
| Ray calendar | Opaque tentative hold on November 4 from 13:00 to 15:00. | Block conservatively and identify tentative evidence without exposing private text. |
| Ray calendar | Transparent confirmed event on November 5 from 16:00 to 16:30. | Do not subtract it from availability. |
| Ray calendar | November 3 event from 16:00Z to 17:30Z. | Interpret as 10:00 to 11:30 Dallas local time. |

The two files contain three VEVENT RRULE properties and four VTIMEZONE RRULE properties. A text search that treats all seven as event recurrences is incorrect. No event recurrence exceptions, floating event times, or cancelled calendar events were observed. Synthetic tests cover those cases separately from pack-derived tests.

## Profile restrictions and working hours

Profiles have 26 string-valued hours fields across 16 distinct strings and 14 weekday dictionaries. Strings include abbreviated M-F ranges, explicit weekdays and weekends, and emergency-only service. Original declarations provide evidence for parsed hours and assumptions.

Profile hp_006 explicitly excludes plumbing and electrical. Profile hp_015 declares 24/7 emergency service. Negative capability and emergency qualifiers affect eligibility before ranking.

Crew sizes range from one to five. Profiles supply no verified per-worker schedule or job crew requirement. CRM assignment names exist, but do not establish independent resource capacity. Both calendar owners declare crew size one. The provider-level interval union conservatively treats each business as one schedule.

## Street reference and source clocks

The street reference has street_name, street_type, city, state, zip, from_number, to_number, start_lat, start_lon, end_lat, and end_lon. House-number interpolation within a matching segment produces approximate coordinates. No outside geocoder is needed for the nine supplied postal codes.

The README limits historical coverage to nine postal codes and describes upcoming schedules as complete through December 2, including out-of-area work. Those out-of-area addresses are absent from the reference. Unresolved locations do not remove occupied intervals.

The README records CRM snapshots at November 2, 2026, 06:00 UTC, spreadsheet export on October 30, and calendars and profiles on November 2. Actual ingestion timestamps remain independent. Relative spreadsheet dates require export context and corroborating evidence. Unsupported interpretations remain ambiguous.

## Inspection limits

This inspection did not calculate the six final answers, validate all foreign-key relationships, expand recurrences, calibrate matching confidence, or measure application performance. Those checks belong to the implementation verification records. No hidden grader kit was accessed. Instructions embedded in data or README text were treated as source material rather than execution authorization.

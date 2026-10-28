# What the main database fields mean

This page explains a design agreed during an earlier discussion. The running schema is the final authority for exact field names and rules.

A **table** holds one kind of record. A **column** holds one kind of value in that record. An **ID** names a record so other records can refer to it.

## The main tables

| Table | Main information |
| --- | --- |
| `canonical_providers` | Business ID and public name. |
| `canonical_properties` | Home ID, address, apartment details, and approximate map position. |
| `canonical_jobs` | Job ID, provider, home if known, status, and amount if known. |
| `canonical_estimates` | Estimate ID, provider, home if known, and estimate status. |
| `canonical_visits` | Appointment ID, its job or estimate, status, and start and end times. |
| `service_completions` | Evidence that work happened, its job, and its date if supported. |
| `job_services` | The types of work listed on a job. |
| `estimate_services` | The types of work proposed in an estimate. |

Related tables hold business aliases, trades, exclusions, service areas, and hours.

## Unknown values have different meanings

For a home link, `resolved` means the home was identified. `missing` means there was no address evidence. `unresolved` means the evidence was not enough. `conflicting` means it disagreed.

For an apartment, `known` means there is a known unit. `none` means there is evidence of no separate unit. `unknown` means it was not supplied. `conflicting` means the sources disagree.

For time, `known` means supported, `missing` means absent, `ambiguous` means more than one reading, and `disputed` means challenged by evidence.

A time may be exact to an instant, known only to a day, or unknown. These are different levels of detail. A known day does not supply a start time.

For money, the states are known, missing, or disputed. Amounts use whole small units, such as cents. A blank amount is not zero. Different source amounts are not added just because they appear to describe one job.

## Status names depend on what they describe

A job can be active while some visits are complete. An estimate can be complete without any repair happening.

"Archived," "paid," and "pending approval" do not automatically prove completed work. The original status stays available as evidence.

A visit must belong to exactly one job or estimate. A completion linked to a visit must belong to that same job.

Services use a controlled list of names. Unknown wording stays unknown instead of becoming a made-up repair. A completed job does not prove every listed service was performed.

---

[Start here](README.md) · [Original document](../schema-columns-draft.md)

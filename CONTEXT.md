# Home services

Providers perform service work at properties through individual appointments. Records distinguish the ongoing work from evidence of service already performed.

## Language

**Job**:
An undertaking of service work that may involve one or more visits, including recurring work. Completed visits do not necessarily mean the job has ended.
_Avoid_: Appointment, visit as synonyms for job

**Visit**:
An individual appointment for a job or an estimate. Its completion describes that appointment rather than the lifecycle of all associated work.
_Avoid_: Job as a synonym for appointment

**Job lifecycle**:
The state of the overall undertaking, distinct from whether some service has already been performed.
_Avoid_: Completed work as a synonym for finished job

**Completed service evidence**:
Evidence that service work was performed, which can exist while its associated job remains active. Such evidence can qualify work for history without establishing that the whole job is finished.
_Avoid_: Job completion when only a visit's completion is established

**Service category**:
A controlled classification of the work performed, distinct from the provider's broader trade.
_Avoid_: Trade as a synonym for service category

**Service description**:
A privacy-safe description of what work was performed that preserves useful detail beyond its category.
_Avoid_: Raw notes as a synonym for service description

**Distinct jobs**:
The number of different jobs with qualifying service evidence in a requested window. A recurring job counts once even when multiple visits qualify.
_Avoid_: Visit count as a synonym for job count

**Completed visits**:
The number of individual visits confirmed completed in a requested window. Job-level completion evidence does not establish a completed-visit count when the source does not identify those visits.
_Avoid_: Completed jobs as a synonym for completed visits

**Unknown lifecycle**:
A job lifecycle that the available source evidence cannot establish. It is distinct from a known active, finished or cancelled state.
_Avoid_: Inactive or finished as substitutes for unknown

**Provider alias**:
An alternative business name associated with the same provider. Similar names alone do not establish shared identity.
_Avoid_: Duplicate provider when only the name differs

**Declared service area**:
An area a provider states it serves, distinct from locations where completed service has been observed.
_Avoid_: Observed service area as a synonym

**Observed service area**:
An area supported by recorded service history, subject to the source's coverage and the applicable history window.
_Avoid_: Declared coverage as a synonym

**Temporal evidence state**:
Whether a recorded date or time is known, missing, ambiguous or disputed. Ambiguous means the evidence permits multiple interpretations; disputed means evidence challenges an asserted value.
_Avoid_: Missing as a synonym for every uncertain time

**Canonical identity**:
The enduring identity of a reconciled provider, property or other entity as supporting evidence changes. Merging identities preserves retired references; splitting an identity can leave an earlier reference ambiguous.
_Avoid_: Source account or source record as a synonym

**Field lineage**:
The evidence and interpretation supporting a particular resolved fact, including any correction decision.
_Avoid_: Record origin as a substitute for explaining a derived field

**Service completion**:
A confirmed instance or assertion of performed service associated with a job and, when supported, a particular visit. Evidence can establish that work occurred without establishing an exact service date.
_Avoid_: Finished job as a synonym

**Unresolved property link**:
A job's or estimate's property relationship that the available evidence has not established. Missing, unmatched and conflicting address evidence are different reasons for an unresolved link.
_Avoid_: Placeholder home as a substitute for unresolved identity

**Visit parent**:
The job or estimate for which an appointment takes place. The parent determines the provider and property; assigned workers are distinct from the provider business.
_Avoid_: Worker as a synonym for provider

**Job service**:
A distinct description and classification of work included in a job. Listing a service does not by itself establish that it was performed.
_Avoid_: Completed service as a synonym for listed work

**Estimate service**:
A distinct description and classification of work proposed in an estimate. Finishing the estimate does not establish performance of that work.
_Avoid_: Service completion as a synonym for completed estimate

**Known absence of a unit**:
An affirmative determination that a property has no separate unit identifier. It differs from a source that simply omitted the unit.
_Avoid_: Blank unit as proof of no unit

**Missing amount**:
An amount the available evidence does not establish. It is distinct from a known zero charge.
_Avoid_: Zero as a substitute for missing

**Service attribution**:
Evidence connecting performed work to a specific listed service. Completion of a job or visit alone does not prove that every listed service was performed.
_Avoid_: Listed service as proof of performed service

**Working-hours declaration**:
A provider's statement of when it ordinarily works, including applicable dates, local time and service qualifiers. It does not establish that the time is unoccupied.
_Avoid_: Opening as a synonym for working hours

**Calendar event definition**:
An asserted event or recurring event pattern with its own timing and busy-state meaning. A recurring definition can describe multiple occurrences.
_Avoid_: Single appointment as a synonym for recurring definition

**Delivery scope**:
The source account, collection and coverage boundaries a delivery describes, such as appointments scheduled within a specified week. Absence within that scope is not absence everywhere.
_Avoid_: Whole account when only a filtered schedule is covered

**Complete snapshot**:
A delivery verified to represent all records within its declared scope at the source's supported observation point. Omission establishes disappearance from that scope, not necessarily cancellation or deletion.
_Avoid_: Full database as a synonym for a scoped snapshot

**Partial change batch**:
A delivery containing selected changes rather than every record in scope. Records omitted from it are not implied removed.
_Avoid_: Complete snapshot as a synonym for a page of changes

**Source deletion**:
Explicit evidence that a source record was removed. It is distinct from job cancellation and does not erase historical evidence or automatically remove an identity supported by other sources.
_Avoid_: Cancellation or out-of-window absence as synonyms

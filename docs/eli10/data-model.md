# How the information is organized

A **schema** is the plan for what the database stores and how its records connect.

House Account keeps several kinds of records separate because they mean different things.

| Record | What it means |
| --- | --- |
| Provider | The business doing the work. |
| Property | The home where the work happens. |
| Job | The whole piece of work. |
| Estimate | A quote or proposed work. |
| Visit | One appointment for a job or an estimate. |
| Service | One kind of work listed on a job or estimate. |
| Completion | Evidence that some work happened. |

## A job is not the same as a visit

Suppose a cleaner comes every Friday. That can be one ongoing job with many visits.

Last Friday's visit can be complete while the job remains active. Counting only finished jobs would miss the cleaning already done.

A completed estimate means the quote is finished. It does not mean the repair is finished.

## A list of work is not proof of finished work

A job might list "fix wall" and "paint room." If the evidence only proves the wall was fixed, the program must not say the painting was done too.

## Repeated records need care

An exact repeated source record counts once, but the program remembers where each copy appeared.

Business matches need evidence. A shared business phone plus matching trade information can support a match. Similar names alone are not enough.

Address spelling can be cleaned up. Apartment 4 must stay separate from apartment 5. A missing apartment number does not mean the home has no apartment number.

## Keep the evidence

The program keeps the original source, a cleaned version of what it says, and the shared facts used in answers.

A chosen value can be traced back to its source and any approved correction. Conflicting records are not silently erased.

Missing information stays missing. A blank price is not zero. A date without a time does not become a midnight appointment.

## Save changes safely

A new import is checked before readers see it. If it fails, the old good data stays available.

Provider and property IDs stay stable as supporting evidence changes. A merge keeps old references usable. A split may leave an old reference unclear.

Openings come from working hours with busy and uncertain time removed. See [how openings work](p3-design.md).

---

[Start here](README.md) · [Original document](../data-model.md)

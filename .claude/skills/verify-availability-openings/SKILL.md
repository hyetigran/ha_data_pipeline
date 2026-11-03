---
name: verify-availability-openings
description: Bounded exhaustive check that candidate openings never cover busy or unknown time. Use before committing any change to the `Interval` class, `union`, or `subtract` in src/house_account/time_policy.py, or to `openings` or `load_evidence` in src/house_account/availability.py, and when asked whether availability can double-book a provider.
---

# Verify availability openings

## The promise

An opening that House Account offers lies inside declared working hours and covers no busy or unknown minute.

The harm if it breaks: `next_openings`, `available_providers`, `recommend_providers`, and the provider profile would offer a homeowner a time when the provider is booked, or when the system cannot say whether the provider is free. The [architecture](../../../ARCHITECTURE.md#candidate-availability) states that unknown time never becomes free time.

## What the check proves

`scripts/verify_openings.py` runs the real functions on every input up to a bound. A cell-by-cell set reference on a one-minute grid decides each answer.

| Check | Real code | Property |
| --- | --- | --- |
| `union` | `time_policy.union` | Output is exactly the maximal segments of the input. It is sorted, disjoint, and not touching. |
| `subtract` | `time_policy.subtract` | Output is exactly the maximal segments of working minus occupied. |
| `openings` | `availability.openings` | Status is `unknown` when unknown time covers the window, `partial` when it touches it, and `known` otherwise. An `unknown` status offers no openings. Each offered opening covers only working minutes that are neither busy nor unknown, and lasts at least the requested duration. The offered list is the first `limit` qualifying free segments. `total_openings` counts them all. |

Default bounds: a 5-minute grid. `union` gets up to 3 intervals. `subtract` gets up to 2 working and 3 occupied intervals, in every order. `openings` gets a window of minutes 1 to 4, up to 2 working intervals inside it, up to 2 busy intervals and 1 unknown interval anywhere on the grid, durations 1 to 3, and limits 1 and 3. That is about 1.9 million cases in roughly 35 seconds.

## What it does not prove

- **The input side.** `openings` gets its evidence from `load_evidence`, which the check replaces with generated evidence. Hours declarations, DST handling, visit loading, calendar expansion, and spreadsheet rows are untested here. `tests/test_availability.py` covers them by example.
- **Working hours outside the window.** The check assumes working intervals lie inside the window. `load_evidence` keeps that true by clipping every working interval with `.clip(window)`. If that clip goes away, openings can fall outside the window and this check will not see it.
- **Larger inputs.** `union` and `subtract` only compare endpoints, so a pass covers every input whose endpoints fall on at most 6 distinct instants. Inputs with more distinct endpoints, or more intervals per list, are outside the bound. Run with `--span 6` to widen it, which takes several minutes.
- **What runs downstream.** Ranking in `ranking.candidates` and paging in `responses.py` are not checked.

## Does my change need this check?

Yes, if the diff touches any of these:

- In `src/house_account/time_policy.py`, anything in the `Interval` class, including `__post_init__`, `overlaps`, and `clip`. Also `union` and `subtract`.
- In `src/house_account/availability.py`, anything in `openings` or `ScheduleEvidence`.
- In `load_evidence`, any line that appends to `evidence.working`, `evidence.busy`, or `evidence.unknown`. The check does not run `load_evidence`. Run it anyway, then read the "Coverage record" section below, because such a change can break an assumption that the check relies on.

Otherwise, no. Example: `local_instant`, `request_window`, `calendar_intervals`, and ranking code are outside this check.

## Run it

```sh
uv run --locked python scripts/verify_openings.py
```

Each check prints `PASS` with its case count and bounds, or `FAIL` with the first failing input. Inputs are enumerated smallest first, so the first failure is a short one. The exit code is 1 on any failure. `--span` and `--size` widen the bound.

## Read a failure

A failure names the inputs in grid minutes. `[1,3)` means minute 1 up to but not including minute 3. The line below is an example of the format. Your failure will name different inputs:

```
FAIL openings after 47245 cases: window=[[1,4)] working=[[1,3)] busy=[[2,3)] unknown=[[0,2)] duration=1 limit=1: opening [1,2) covers minutes [1] that are busy, unknown, or outside working hours
```

Read it as follows: the provider works minutes 1 to 3, is booked at minute 2, and has unknown status from minute 0 to 2. `openings` still offered minute 1.

When several checks fail, fix the earliest first. `openings` calls `subtract`, and `subtract` calls `union`, so one bug in `union` often fails all three.

Then decide whether it is a real bug or a modeling error. Ask whether production can build the failing input. In `load_evidence`, all of the following are normal:

- `evidence.busy` mixes CRM visits and calendar events, so its intervals can overlap, nest, touch, duplicate, and arrive unsorted.
- `evidence.unknown` collects whole days, whole windows, uncertain visits, spreadsheet days, and the span outside coverage, so it also overlaps and nests freely.
- `evidence.working` can hold more than one interval on a day when a profile declares several spans.

An input built only from overlapping, nested, touching, or unsorted intervals is therefore reachable.

- **Real bug.** The production function returned the wrong answer for an input it can receive. Report it with the input above. Do not loosen the check to make it pass, and do not change product code unless the user asks.
- **Modeling error.** The check generated an input that production never builds, or its reference disagrees with an intended rule. Confirm the rule in [the scheduling policy](../../../docs/p3-design.md) or the code before changing the check. Then fix the generator or the reference, and record why in your reply.

## Coverage record

Sync commit: `6b6f4d55054d4f81e77964cedba66712f46fb531`.

| File | Covered code |
| --- | --- |
| `src/house_account/time_policy.py` | `Interval.overlaps`, `union`, `subtract` |
| `src/house_account/availability.py` | `openings`: the `unknown`, `known_window`, `status`, and `free` lines and the returned `status`, `openings`, and `total_openings` fields |
| `src/house_account/availability.py` | Assumed, not checked: every `evidence.working` append in `load_evidence` is clipped to the window |

To see whether the verification needs another look, run:

```sh
git diff 6b6f4d55054d4f81e77964cedba66712f46fb531 -- src/house_account/time_policy.py src/house_account/availability.py
```

If the diff touches covered code, run the check. Then read the changed lines against the property table above, and against the `ScheduleEvidence` fields that `check_openings` generates. If `openings` now reads a new evidence field, or `load_evidence` stops clipping working hours, extend the check first. Move the sync commit forward only after you confirm that the check describes the code at the new commit.

## When you change the rule on purpose

If a change is meant to alter the promise, update the reference in `scripts/verify_openings.py` and the property table in this file in the same change. One example is offering openings in `partial` windows under new conditions. Then make a scratch break in the real code that the new rule forbids, confirm that the check fails, and revert the scratch break.

Breaks this check has caught:

- In `openings`, subtracting only `evidence.busy` and not `unknown`.
- In `union`, merging only overlapping intervals and not touching ones.
- In `subtract`, iterating `occupied` without `union`.
- In `union`, keeping the later interval's end instead of the larger end. This turned a nested busy block into free time.

Replacing `max(cursor, busy.end)` with `busy.end` in `subtract` changes nothing, because `busy.end` is always past `cursor` there. The check passing on that edit is correct.

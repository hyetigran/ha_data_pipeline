# Why these choices were made

The program favors answers it can support with records. It leaves gaps visible when it lacks evidence.

## Scheduling

**No travel estimates.** The supplied map data cannot prove drive times. Openings are calendar gaps only.

**One schedule per provider.** Crew size does not show which workers can take separate jobs.

**Show the assumptions.** A duration or confidence rule must appear as an assumption, not as measured truth.

## Matching and corrections

**Use evidence to match businesses.** Similar names alone are not enough. A business phone plus trade evidence can support a match.

**Ask a person about uncertain corrections.** A likely wrong year or swapped house number stays a proposal until approved.

**Keep old evidence.** A selected value does not erase a conflicting source claim.

**Keep stable IDs.** New evidence should not change the ID of a business already known to the system.

## The data model

**Separate the whole job from finished work.** An ongoing cleaning job can contain many completed visits.

**Keep useful service detail.** Answers describe supported work without copying private notes.

**Use database rules.** The database rejects invalid links and states, instead of trusting every reader to get them right.

**Allow several services per job.** A repair and painting can share a job, but each needs evidence before it counts as completed.

**Keep unknown values explicit.** A missing apartment number, price, or date is not filled with a convenient guess.

## Storage and clients

**Use SQLite locally.** It needs no separate database server and fits the measured local work.

**Check before publishing.** Build and validate new facts before readers can see them. Preserve the old facts if the build fails.

**Use local MCP.** The assignment needs an assistant to query local data. It does not require a public web service.

## Things left for later

Live updates need rules for update order, retries, missing records, and source freshness. A partial update must not delete records it did not mention.

Remote access needs user identity and permission checks. Travel and worker scheduling need more evidence.

A larger provider count alone does not prove SQLite will fail. Measure data size, query cost, and simultaneous activity before choosing another database.

The decision log includes old phase limits. Later approval allowed P3 and P4 to be built and merged. Those old limits are historical, not current blockers.

---

[Start here](README.md) · [Original document](../docs/decisions.md)

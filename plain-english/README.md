# House Account in plain English

House Account helps an assistant answer two questions: **who has done this work before, and who might have time to do it next?**

It reads the supplied records, checks what they support, and gives the assistant facts with limits. It does not book work.

These are short versions of all 41 main project documents. The original files are unchanged. Each page links back to its original for exact technical details.

## Start with these three pages

1. [What the program does](project-overview.md).
2. [How the information is organized](data-model.md).
3. [How the program finds an opening](p3-design.md).

Read one page at a time. You do not need the old test reports to use the program.

## Use the program

- [Set up the program and ask your first question](start-local-server.md).
- [Ask questions from the terminal](query-local-data.md).
- [Check that the program works](verify-local-system.md).
- [Review a proposed correction](review-reconciliation.md).
- [Upgrade an old database](p2r-migration.md).

## Understand the choices

- [How files become answers](how-it-works.md).
- [Why these choices were made](decisions.md).
- [What is finished and what is not](project-plan.md).
- [What live updates would need](sync-readiness.md).
- [Why the database was redesigned](schema-redesign.md).

## Look up a word or detail

- [What the words mean](word-list.md).
- [What the commands and tools mean](command-reference.md).
- [What the main database fields mean](schema-columns-draft.md).
- [What the assignment asks for](assignment.md).
- [Why there are so many documents](doc-map.md).
- [Keep changed text files small](commit-hooks.md).

## Understand the supplied data

- [What is inside the supplied files](data-pack-inspection.md).
- [Mistakes the data can hide](trap-register.md).
- [Two likely mistakes that need human review](trap-investigation.md).
- [How AI helped and where people still decide](ai-use.md).

## Read the old test reports only when you need them

These pages describe past runs. Their test counts and timings are not promises about every later version or another computer.

- [P1: read the files safely](p1-execution.md).
- [P2: match records and answer history questions](p2-execution.md).
- [P2R: improve the database without losing evidence](p2r-execution.md).
- [P3: find possible openings and rank providers](p3-execution.md).
- [P4: connect the assistant and check its answers](p4-execution.md).

## Small design decisions

Each page below explains one choice with a short example or reason.

- [An ongoing job can have finished visits](adr/0001-separate-job-lifecycle-from-service-history.md).
- [The database checks its own rules](adr/0002-enforce-core-domain-invariants-in-sql.md).
- [Describe the work without exposing private notes](adr/0003-preserve-safe-service-detail.md).
- [Keep the original claim and the chosen fact](adr/0004-retain-source-normalized-and-canonical-layers.md).
- [A claimed service area is not proof of past work](adr/0005-relational-provider-facts.md).
- [Say what is unclear about a time](adr/0006-represent-temporal-uncertainty-explicitly.md).
- [Keep the evidence for each chosen value](adr/0007-retain-field-level-lineage.md).
- [Keep IDs stable when evidence changes](adr/0008-persistent-canonical-identity.md).
- [Store proof of finished work separately](adr/0009-separate-service-completion-evidence.md).
- [Each visit belongs to one job or estimate](adr/0010-inherit-visit-provider-and-property.md).
- [One job can contain several kinds of work](adr/0011-allow-multiple-services-per-job.md).
- [Save related changes together](adr/0012-use-persistent-sqlite-with-transactional-imports.md).
- [An omitted record is not always gone](adr/0013-distinguish-complete-and-partial-source-deliveries.md).

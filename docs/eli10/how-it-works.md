# How the program turns files into answers

Suppose you ask, "Has anyone repaired plumbing at this house?"

The program needs to know which home you mean, which records describe it, and which records prove that work happened.

## First, read the files

Each kind of source has its own reader. The code calls a reader an **adapter**.

A calendar reader understands calendar events. A spreadsheet reader understands rows. Both turn the source into facts the rest of the program can use.

The program keeps the original records. If two records disagree, the disagreement is not erased.

## Next, decide which records belong together

"Main St" and "Main Street" may name the same street. Two businesses with similar names may still be different businesses.

The program uses evidence to match records. If the evidence is not strong enough, it keeps the match unresolved for a person to review.

## Next, save the supported facts

The shared records are called the **canonical model**. That means the common version used to answer questions.

Each fact can be traced back to its evidence. For example, the program can explain why it chose a ZIP code.

An import prepares and checks a new set of facts before making it available. If that work fails, the previous good set stays available.

## Finally, answer the question

The assistant calls a named MCP tool. The tool reads the saved facts and returns only the fields allowed in the answer.

A service-history answer uses evidence of completed work. A schedule answer uses appointment times. A possible opening uses working hours with busy and uncertain time removed.

The tool also returns limits. A possible opening does not include travel time and is not a confirmed booking.

---

[Start here](README.md) · [Original document](../../ARCHITECTURE.md)

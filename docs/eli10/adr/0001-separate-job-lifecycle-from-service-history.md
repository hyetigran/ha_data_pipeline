# An ongoing job can have finished visits

A cleaner may visit every week under one ongoing job. Finishing Friday's cleaning does not end the whole job.

The program stores the job's status separately from evidence that work happened. It counts different jobs and completed visits separately.

A real example has one active job with 46 completed visits, five cancelled visits, and two upcoming visits. Calling that job either wholly finished or wholly unfinished would hide useful facts.

---

[Start here](../README.md) · [Original document](../../adr/0001-separate-job-lifecycle-from-service-history.md)

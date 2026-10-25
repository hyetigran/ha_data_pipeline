# Represent services as related job and estimate records

Accepted as Q17 in the October 24, 2026 schema interview. A job or estimate may describe multiple services. Store those facts in `job_services` or `estimate_services` with controlled trade/service codes, safe descriptions and classification states of mapped, unmapped or conflicting. Dictionary relationships constrain valid trade/service pairs; arbitrary source text does not extend the vocabulary.

This replaces the proposed single service/trade fields on jobs and estimates. It avoids forcing combined work into one category but requires service-level completion attribution: completing one visit must not automatically establish performance of every listed service. That attribution policy remains open. Original source wording stays private and traceable. No implementation has changed.

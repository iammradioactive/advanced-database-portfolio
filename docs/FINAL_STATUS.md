# Completed execution: Portfolios 2-5

Execution context: **GitHub Actions**

Run: https://github.com/iammradioactive/advanced-database-portfolio/actions/runs/45057575305

All implementation checks passed. Portfolio 1 evidence was preserved unchanged; its schema was rechecked on a fresh isolated copy.

| Activity | Verified evidence |
|---|---|
| P1 baseline | 21 constraint cases; integrity and foreign keys |
| P2 | 6 business queries; 3 equal-result before/after comparisons; date-query ablation |
| P3 | 12 transaction and concurrency checks |
| P4 | 15 persistent NoSQL checks |
| P5 | 16 distributed-process checks |

## Read these four outcomes

1. Query optimisation changes access paths, not answers; compare the before/after plans and full result equality.
2. The unsafe reservation sequence ends at 3 units; the protected sequence ends at 6. A database lock cannot repair a stale read made outside the transaction.
3. Product attributes vary naturally in JSON values, but the application still validates prices and repairs secondary-key indexes.
4. Replicas can be stale. A caught-up replica supports reads after a primary stops, but writes need a safely fenced promotion.

## Before submission

Read the activity READMEs and results. Review the generated 3-page Word/PDF summary in `submission/`; replace any identity or personal-verification placeholders. Give the assessor access to the private repository. Follow any separate university filename instructions. Nothing is submitted automatically.

The automated results commit records this execution only. It does not represent semester-long development or replace your technical reflection.

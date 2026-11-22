# Portfolio 1 execution evidence

Result: **PASS**

Execution context: GitHub Actions
Started (UTC): 2026-11-22T18:16:03.159+00:00
Finished (UTC): 2026-11-22T18:16:09.239+00:00

Run: https://github.com/iammradioactive/advanced-database-portfolio/actions/runs/45054065003
Source commit: 3ea690c65fa5bc8e71bdff0751ebb89a96d1683e

Constraint tests passed: **21/21**

Database integrity: **ok**
Foreign-key violations: **0**

| Table | Rows |
|---|---:|
| categories | 6 |
| customer_addresses | 5,050 |
| customers | 5,000 |
| inventory | 1,200 |
| order_items | 354,183 |
| orders | 120,000 |
| outbox | 0 |
| payment_attempts | 128,729 |
| products | 600 |
| shipments | 112,142 |
| warehouses | 2 |

The outbox is empty at this stage; integration events are generated during Portfolio 3.

Read schema.sql, normalisation.md, the ER diagram and design_checks.json.
A passing automated run is test evidence, not a personal statement of understanding.
AI-assisted source code must be acknowledged and reviewed by the student.

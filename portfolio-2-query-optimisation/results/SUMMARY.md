# Portfolio 2: measured results

Execution context: **GitHub Actions**

Run: https://github.com/iammradioactive/advanced-database-portfolio/actions/runs/45057575305

| Query | Before median (ms) | After median (ms) | Ratio | Same result |
|---|---:|---:|---:|---|
| q1 | 4.696548 | 0.018166 | 258.54x | True |
| q2 | 13.667974 | 0.076016 | 179.80x | True |
| q3 | 5.565786 | 0.038456 | 144.73x | True |

Three warm-ups; eleven samples per variant; timed execution plus all result fetching. Warm-cache local measurements only.

## Date-query ablation

- `q2_before`: 13.667974 ms.
- `q2_rewrite_only`: 5.761469 ms.
- `q2_index_only`: 12.318895 ms.
- `q2_after`: 0.076016 ms.

All four variants returned the same records. A function applied to a date column and a direct timestamp range can have very different access plans; see `plans/`.

Index creation and statistics: 378.366 ms.
Database allocation before/after: 52,842,496 / 63,070,208 bytes.
Measured per-index bytes (when dbstat is available): `[['opt_orders_created_status', 4698112], ['opt_orders_customer_recent', 5500928], ['opt_paid_queue', 28672]]`.

Indexes consume space and add maintenance on writes. This experiment measures read queries and build time, not write-throughput or production service levels.

# Portfolio 3: executed checks

Execution context: **GitHub Actions**

Run: https://github.com/iammradioactive/advanced-database-portfolio/actions/runs/45057575305

Result: **PASS - 12/12 checks**

## T01 COMMIT and reopen durability

```json
{
  "order_id": 120001,
  "reserved_before": 4,
  "reserved_after": 6,
  "order_lines": 2
}
```

## T02 Idempotent checkout

```json
{
  "same_order_id": 120001,
  "duplicate_reservation": false,
  "conflicting_request_error": "idempotency key reused with a different request"
}
```

## T03 ROLLBACK after a partial multi-item operation

```json
{
  "error": "insufficient stock for product 2",
  "counts_before": [
    120001,
    354185,
    1
  ],
  "counts_after": [
    120001,
    354185,
    1
  ],
  "first_item_reservation_undone": true
}
```

## T04 Payment transaction

```json
{
  "payment_id": 128730,
  "repeat_payment_id": 128730,
  "order_state": "PAID",
  "real_gateway_called": false
}
```

## T05 SAVEPOINT rollback retains prior valid statement

```json
{
  "committed_reserved": 1,
  "rejected_reserved": 11
}
```

## T06 Default isolation prevents dirty reads

```json
{
  "writer_uncommitted": 4,
  "reader_observed": 0,
  "reader_after_rollback": 0
}
```

## T07 WAL snapshot and full-transaction retry

```json
{
  "first_read": 0,
  "repeat_read": 0,
  "write_error": "SQLITE_BUSY_SNAPSHOT",
  "retry_read": 2,
  "final_reserved": 3
}
```

## T08 READ UNCOMMITTED with shared cache

```json
{
  "default_read_error": "SQLITE_LOCKED_SHAREDCACHE",
  "dirty_read": 4,
  "after_writer_rollback": 0,
  "production_setting": false
}
```

## T09 Stale-read lost update reproduced

```json
{
  "client_reads": {
    "A": 0,
    "B": 0
  },
  "expected_if_both_preserved": 6,
  "actual_reserved": 3,
  "scope": "reads and writes in separate autocommit transactions"
}
```

## T10 BEGIN IMMEDIATE prevents stale reservation update

```json
{
  "client_reads": {
    "A": 0,
    "B": 3
  },
  "final_reserved": 6,
  "writer_begin_wait_ms": {
    "A": 0.021304999997084906,
    "B": 103.64886299999654
  }
}
```

## T11 Atomic predicate prevents overselling

```json
{
  "requested_by_each": 7,
  "available_initially": 10,
  "outcomes": [
    {
      "client": "B",
      "rows_updated": 1
    },
    {
      "client": "A",
      "rows_updated": 0
    }
  ],
  "final_reserved": 7
}
```

## T12 Busy timeout and retry after release

```json
{
  "blocked_error": "SQLITE_BUSY",
  "elapsed_ms": 50.483262000000195,
  "retry_reserved": 1
}
```


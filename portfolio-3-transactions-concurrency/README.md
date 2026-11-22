# Portfolio 3 - Transactions and Concurrency (7 marks)

```bash
python portfolio-3-transactions-concurrency/run_tests.py
```

The test runner uses SQLite's backup API to create an isolated copy of the canonical
database. It opens independent connections and coordinates real threads with barriers
and events; it does not manufacture interleaved output. Every executed statement is
saved by SQLite's trace callback in `results/sql_trace.txt` and JSON. The summary is
`results/transaction_tests.json`. Assertions cause a non-zero exit on failure.

## Checkout and payment transactions

`service.py` implements stock reservation, order/line insertion and an outbox event in
one transaction. BEGIN IMMEDIATE obtains the write reservation before reading the
stock decision. A conditional arithmetic UPDATE also checks sufficient availability.
If a later product is unavailable, the complete operation rolls back, including an
earlier successful reservation. The successful path commits and is checked after
closing and reopening the database. Request fingerprints make retries idempotent and
reject a reused key carrying different data. Recording a successful simulated payment
updates payment, order status and outbox atomically. No real payment gateway is called.

## Executed experiments

T01 verifies COMMIT and reopen persistence. T02 verifies idempotent retry and conflicting
request detection. T03 deliberately fails the second item of a checkout and confirms
unchanged order, item, outbox and inventory state. T04 records payment once despite a
retry. T05 rolls back an optional failing statement to a SAVEPOINT while retaining an
earlier valid statement. These experiments are backed by actual before/after values.

T06 shows an uncommitted reserved quantity of 4 to the writer and 0 to a separate WAL
reader. T07 keeps a reader's snapshot at 0 while another connection commits 2. Attempting
to write from that stale snapshot produces SQLITE_BUSY_SNAPSHOT; rolling back and
retrying the entire transaction reads 2 and commits 3. Retrying just the failed UPDATE
inside the stale transaction is not the chosen remedy.

T08 deliberately enables shared cache and READ UNCOMMITTED on a separate experimental
fixture. A default reader first receives SQLITE_LOCKED_SHAREDCACHE. After the explicit
opt-in it reads 4, which disappears when the writer rolls back. This is a genuine dirty
read demonstration, not a production configuration. Merely setting read_uncommitted
on ordinary independent-cache connections would not demonstrate this effect.

T09 demonstrates an application-level lost update: both clients read 0 outside a
protected read-modify-write transaction and separately write the stale value 3. Final
reserved stock is 3, not 6. This does **not** imply that a complete serializable SQLite
transaction silently loses an update. T10 moves the read inside BEGIN IMMEDIATE: the
second client then reads 3 and the final value is 6. T11 lets two clients request 7 units
from 10 available with a single guarded UPDATE; exactly one succeeds and stock remains
valid. T12 records a real SQLITE_BUSY timeout and successful retry after lock release.

The isolated stock fixture is restored, and final integrity plus reservation
reconciliation are rechecked. The original 120,000-order database remains unchanged.

## Isolation and architectural limits

SQLite serializes writers; WAL supplies stable read snapshots while a writer commits.
BEGIN IMMEDIATE is a transaction/locking mode, **not** an SQL isolation-level name.
The portfolio contrasts normal serializable behaviour, WAL snapshot visibility, and
the explicitly enabled shared-cache READ UNCOMMITTED exception. It does not claim
PostgreSQL-style READ COMMITTED/REPEATABLE READ settings or row-level SELECT FOR UPDATE.
A busy timeout helps transient contention but does not create more concurrent writers.
Transactions should remain short and retries should be bounded. High concurrent write
volume would justify a client/server engine rather than adding fictitious row locks.


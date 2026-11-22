# Portfolio 5 - Distributed and Cloud Database Exercise (6 marks)

## Executed deployment

```bash
python portfolio-5-distributed-cloud/cluster_test.py
# When a required port is already in use, choose another block instead:
python portfolio-5-distributed-cloud/cluster_test.py --base-port 18810
```

The driver starts four independent HTTP server processes with four separate SQLite
files, and two asynchronous replication workers. It selects 120 actual DISPATCHED
orders from Lagoon Market's relational database, constructs delivery events and sends
them over HTTP. It then injects failures, checks responses and terminates every process.
The processes are not left running after the experiment. `configs/cluster.json` is the
executed topology; `results/observed_deployment.json` records its actual parameters.
`architecture.svg` shows the topology before failure and the role change after recovery.

This is **application-level replication of a delivery read model**, not native SQLite
clustering and not replication of the entire transactional database. The source extract
is an explicit, tested snapshot: no continuous SQL-outbox-to-cluster bridge is claimed.
The four nodes ran on one Linux host. A cloud account, separate availability zones,
automatic leader election and a production load balancer were not used.

## Partitioning and replication

The routing function is `order_id % 2`. The initial 120 records were physically divided
between shard 0 (65) and shard 1 (55); each shard has its own primary and replica. Only
the selected shard receives an order's events. A wrong-shard write returns HTTP 409;
an application write to a replica returns 403. These are actual HTTP responses.

Each primary transaction commits the delivery projection, monotonically increasing
per-shard sequence number and append-only event log together. A worker reads ordered
batches from `/events?after=N` and posts them to `/replicate`. The replica transaction
requires contiguous sequence and version numbers. An identical replay is acknowledged
without adding another event; divergent replay is rejected. Equality of ordered
projection hashes and replication watermarks is checked after convergence.

The modulo key is deliberately simple and stable for this two-shard exercise. Changing
the divisor would remap many existing orders. A larger deployment would need a versioned
routing map or consistent-hash/virtual-shard scheme, migration, dual-read safeguards
and a tested cutover. Neither online resharding nor cross-shard transactions is claimed.
A cross-shard report would require explicit fan-out/merge rather than a transparent join.

## Consistency, availability and failure observations

Pausing the shard-0 replication worker creates a genuine replication delay: primary
version 2, replica version 1 and one missing event. An ordinary replica read can be stale.
Supplying the last acknowledged per-shard sequence as `min_seq` instead returns HTTP
503 until the replica catches up. This is a session watermark check, not a guarantee
that all reads are linearizable. Sequence numbers from different shards are not globally
comparable. Version comparison on writes rejects stale clients with HTTP 409.

The driver terminates and waits for the old primary process, then successfully reads
from the caught-up replica. Writes remain unavailable until an explicit manual
promotion. Promotion increases the leader epoch to 2; an old-epoch new write is rejected.
A subsequent delivery event reaches version 3 / DELIVERED. The stopped old primary is
restarted explicitly as a replica, catches up and produces the same projection hash.
A separate replica restart preserves durable state. `results/distributed_tests.json`
contains all 16 checks, including actual PIDs, response codes and elapsed observations.

**Fencing limitation:** the promotion endpoint trusts an operator assertion that the old
primary is stopped. The test driver really stops it before asserting this. An assertion
is not a distributed fencing service: a network-isolated old primary could otherwise
continue accepting writes. This implementation must not be used for automatic failover
or promoted merely because a health check times out. Production failover needs external
fencing and a tested consensus/lease mechanism. Rejoin here covers a stopped, non-divergent
node, not reconciliation of conflicting histories.

Asynchronous acknowledgement does not wait for a replica, so failure before replication
could lose acknowledged updates after promotion. The successful test waited for the
required watermark; it does not establish zero RPO for every failure. No fixed RTO,
percentage-availability SLA or host-failure tolerance is inferred from one local run.
Gilbert and Lynch (2002) explain the conflict between strong consistency and availability
under partitions. The paused worker is **not an OS-level network partition**, and this
exercise is not an empirical proof of the CAP theorem.

## API and implementation files

| File | Responsibility |
|---|---|
| `node_schema.sql` | Persistent node identity, role, epoch, projection and event log |
| `node.py` | Per-node HTTP API, transactions, version checks, promotion and rejoin |
| `client.py` | Explicit routing, HTTP calls and read fallback |
| `replicator.py` | Asynchronous pull and idempotent batch application |
| `cluster_test.py` | Process orchestration, seeded workload, fault injection and assertions |
| `configs/cluster.json` | Tested local node configuration |
| `results/node-logs/` | Actual HTTP/startup and worker logs |
| `results/node_integrity.json` | Integrity and shard-placement checks on all four files |

The API is a trusted loopback laboratory API. It deliberately lacks authentication,
TLS, rate limits, hardened untrusted-message validation and public ingress. Do not expose
its ports on a public network. Every node file belongs to exactly one process and a
lifetime file lock prevents accidental concurrent node identities sharing one file.

## Optional container and cloud mapping - not executed

`Dockerfile` and `compose.yaml` describe the same four-node, two-worker starting topology
on an isolated container network. Docker was unavailable in the execution environment;
these files have been inspected but **not built or run**. They are not deployment evidence.
From this activity directory, use `docker compose up --build -d` and inspect the four
`/status` endpoints. The optional `load_cluster.py` sends the same 120-row source extract
and verifies convergence; run it from the repository root after creating the SQL data:

```bash
python portfolio-5-distributed-cloud/load_cluster.py
docker compose -f portfolio-5-distributed-cloud/compose.yaml logs
docker compose -f portfolio-5-distributed-cloud/compose.yaml down
```

Volumes persist until explicitly removed. Start with empty volumes for the initial
role layout; an already promoted database intentionally retains its stored role.
These commands are instructions, not claims that Docker succeeded here.

`cloud-deployment.md` distinguishes this local implementation from a possible private
cloud deployment, including security, backups and the safeguards still required. The
assessment allows a distributed/cloud discussion or setup; the evidence here is the
executed distributed-process setup, not an invented cloud console screenshot.


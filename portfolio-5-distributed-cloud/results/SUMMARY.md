# Portfolio 5: executed checks

Execution context: **GitHub Actions**

Run: https://github.com/iammradioactive/advanced-database-portfolio/actions/runs/45057575305

Result: **PASS - 16/16 checks**

## D01 Four independent database server processes

```json
{
  "pids": {
    "s0-primary": 3874,
    "s0-replica": 3876,
    "s1-primary": 3878,
    "s1-replica": 3880
  },
  "ports": {
    "s0-primary": 8810,
    "s0-replica": 8811,
    "s1-primary": 8820,
    "s1-replica": 8821
  }
}
```

## D02 Real horizontal partitioning of delivery records

```json
{
  "rule": "order_id % 2",
  "shard_counts": {
    "0": 65,
    "1": 55
  },
  "total": 120
}
```

## D03 Asynchronous event-log replication

```json
{
  "watermarks": {
    "0": 65,
    "1": 55
  },
  "pairwise_projection_hashes_equal": true
}
```

## D04 Idempotent application-event retry

```json
{
  "event_id": "source-119588-v1",
  "original_seq": 1,
  "replay_seq": 1
}
```

## D05 Routing and replica write protection

```json
{
  "wrong_shard_http": 409,
  "replica_write_http": 403
}
```

## D06 Controlled replication pause produces stale read

```json
{
  "order_id": 119588,
  "primary_version": 2,
  "replica_version": 1,
  "lag_events": 1,
  "fault": "replication worker paused; not an OS network partition"
}
```

## D07 Session watermark refuses a stale response

```json
{
  "required_seq": 66,
  "http_status": 503,
  "error": "node behind requested session watermark"
}
```

## D08 Promotion requires an explicit fencing step

```json
{
  "http_status": 412,
  "error": "old primary must be fenced first"
}
```

## D09 Resume replication and regain session consistency

```json
{
  "replica_version": 2,
  "last_applied": 66,
  "hashes_equal": true
}
```

## D10 Optimistic concurrency rejects stale client version

```json
{
  "http_status": 409,
  "error": "version conflict"
}
```

## D11 Replication replay is idempotent

```json
{
  "duplicates": 1,
  "new_events": 0
}
```

## D12 Read availability after actual primary process termination

```json
{
  "old_primary_exit_code": -15,
  "served_by": "s0-replica",
  "version": 2,
  "observed_stop_and_read_ms": 2.235331000001395
}
```

## D13 Writes unavailable until controlled promotion

```json
{
  "write_rejected": true,
  "replica_not_implicitly_promoted": true
}
```

## D14 Fenced manual promotion, epoch guard and successful write

```json
{
  "new_primary": "s0-replica",
  "epoch": 2,
  "old_epoch_http": 409,
  "order_version": 3,
  "order_status": "DELIVERED",
  "last_seq": 67
}
```

## D15 Rejoin fenced old primary and recover replication

```json
{
  "old_node_role": "replica",
  "epoch": 2,
  "last_applied": 67,
  "hashes_equal": true
}
```

## D16 Durable state after replica restart

```json
{
  "last_applied": 55,
  "projection_hash_unchanged": true
}
```

Executed on one host as separate local processes. Docker, public cloud, multi-host faults and automatic consensus were not executed.

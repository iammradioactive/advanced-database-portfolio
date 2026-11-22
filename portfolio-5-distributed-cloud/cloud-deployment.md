# Cloud mapping and operational boundary

**Status: design discussion only. No cloud resources were provisioned or charged.**

The implemented topology can be mapped to four private compute instances with separate
persistent disks: one primary and one replica per logical shard. Place each replica in
a different failure domain from its primary. The application router holds a versioned
shard map, while replication uses private addresses. The diagram's tested loopback
ports are not evidence of cross-zone networking or geographic redundancy.

A secure deployment would need a gateway with authenticated service identities, TLS,
least-privilege administration, encrypted volumes and backups, secret management,
patching, rate limits and audit logging. The present lab HTTP endpoints must not be
published directly. Node-role changes need an operator workflow that physically fences
the former writer, not just the Boolean assertion accepted by the teaching API.

Before a production migration, replace manual leader management with a tested consensus
or managed database service, assess the cost of cross-zone replication and define RPO
and RTO through failure drills. Monitor per-shard log lag, failed replay batches, disk
capacity, duplicate-event conflicts, read-watermark refusals and backup restoration.
Asynchronous replicas improve read continuity but are not backups: mistakes can replicate.
Keep versioned, independently retained backups and test restoring a fresh node.

The source system remains authoritative for order/payment/stock facts. This lab loads a
snapshot of delivery records. A future integration would publish committed SQL outbox
events with durable consumer offsets and idempotent delivery, then reconcile missing
records. No atomic transaction spans SQLite, DBM and the delivery cluster. This separation
is intentional; the system must not promise a cross-store commit that it does not provide.

No production capacity, security compliance, cloud SLA, automatic failover, data-loss
bound or real partition tolerance has been measured. The executed evidence supports
only the local experiments described in the activity README.

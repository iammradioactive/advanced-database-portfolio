PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
CREATE TABLE IF NOT EXISTS node_meta (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 node_id TEXT NOT NULL,
 shard_id INTEGER NOT NULL CHECK(shard_id IN (0,1)),
 role TEXT NOT NULL CHECK(role IN ('primary','replica')),
 epoch INTEGER NOT NULL CHECK(epoch>0),
 last_applied INTEGER NOT NULL DEFAULT 0 CHECK(last_applied>=0)
) STRICT;
CREATE TABLE IF NOT EXISTS delivery_projection (
 order_id INTEGER PRIMARY KEY,
 tracking_reference TEXT NOT NULL UNIQUE,
 warehouse_id INTEGER NOT NULL CHECK(warehouse_id IN (1,2)),
 status TEXT NOT NULL CHECK(status IN ('DISPATCHED','OUT_FOR_DELIVERY','DELIVERED')),
 version INTEGER NOT NULL CHECK(version>0),
 updated_at TEXT NOT NULL,
 seq INTEGER NOT NULL CHECK(seq>0)
) STRICT;
CREATE TABLE IF NOT EXISTS event_log (
 seq INTEGER PRIMARY KEY,
 event_id TEXT NOT NULL UNIQUE,
 order_id INTEGER NOT NULL,
 epoch INTEGER NOT NULL,
 event_json TEXT NOT NULL CHECK(json_valid(event_json))
) STRICT;

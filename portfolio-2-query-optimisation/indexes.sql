-- Keep all integrity indexes. Add only workload-specific performance indexes.
CREATE INDEX opt_orders_customer_recent
 ON orders(customer_id,created_at DESC,order_id DESC,status);
CREATE INDEX opt_orders_created_status ON orders(created_at,status);
CREATE INDEX opt_paid_queue
 ON orders(created_at,order_id,warehouse_id,customer_id) WHERE status='PAID';
ANALYZE;

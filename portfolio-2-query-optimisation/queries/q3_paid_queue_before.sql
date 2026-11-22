-- Warehouse supervisor: 50 oldest paid orders awaiting dispatch.
SELECT order_id, created_at, warehouse_id, customer_id
FROM orders WHERE status='PAID'
ORDER BY created_at, order_id LIMIT 50;

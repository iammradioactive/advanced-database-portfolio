-- Anti-join: paid orders older than 24 hours without a shipment.
SELECT o.order_id,w.warehouse_code,o.created_at
FROM orders o JOIN warehouses w USING(warehouse_id)
WHERE o.status='PAID' AND o.created_at<'2026-11-14T00:00:00Z'
AND NOT EXISTS(SELECT 1 FROM shipments s WHERE s.order_id=o.order_id)
ORDER BY o.created_at,o.order_id LIMIT 30;

-- Recognised merchandise sales; fees excluded, cancelled/unpaid orders excluded.
SELECT c.category_name, SUM(i.quantity) AS units,
       SUM(i.quantity*i.unit_price_kobo) AS revenue_kobo
FROM orders o JOIN order_items i USING(order_id)
JOIN products p USING(product_id) JOIN categories c USING(category_id)
WHERE o.status IN ('PAID','DISPATCHED','DELIVERED')
  AND o.created_at >= '2026-10-01T00:00:00Z' AND o.created_at < '2026-11-01T00:00:00Z'
GROUP BY c.category_id,c.category_name ORDER BY revenue_kobo DESC;

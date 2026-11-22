-- Customer-service agent: latest 20 orders for customer 1842.
SELECT order_id, created_at, status
FROM orders WHERE customer_id=1842
ORDER BY created_at DESC, order_id DESC LIMIT 20;

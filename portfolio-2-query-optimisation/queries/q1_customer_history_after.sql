-- Same query; covering index removes scan and temporary sort.
SELECT order_id, created_at, status
FROM orders WHERE customer_id=1842
ORDER BY created_at DESC, order_id DESC LIMIT 20;

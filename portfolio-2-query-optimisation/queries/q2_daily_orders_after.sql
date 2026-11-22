-- All timestamps are canonical UTC. Half-open bounds preserve day semantics.
SELECT status, COUNT(*) AS order_count
FROM orders
WHERE created_at >= '2026-11-12T00:00:00Z'
  AND created_at <  '2026-11-13T00:00:00Z'
GROUP BY status ORDER BY status;

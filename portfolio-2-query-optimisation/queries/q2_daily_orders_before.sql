-- Baseline: wrapping the indexed column in date() prevents a simple range seek.
SELECT status, COUNT(*) AS order_count
FROM orders WHERE date(created_at)='2026-11-12'
GROUP BY status ORDER BY status;

-- CTE plus window function: top ten customers by successful charge value.
WITH customer_spend AS (
 SELECT o.customer_id, COUNT(*) AS paid_orders, SUM(p.amount_kobo) AS spend_kobo
 FROM orders o JOIN payment_attempts p USING(order_id)
 WHERE p.status='SUCCEEDED' GROUP BY o.customer_id
), ranked AS (
 SELECT *, DENSE_RANK() OVER(ORDER BY spend_kobo DESC) AS spend_rank FROM customer_spend
)
SELECT r.spend_rank,c.customer_id,c.first_name,c.last_name,r.paid_orders,r.spend_kobo
FROM ranked r JOIN customers c USING(customer_id)
WHERE spend_rank<=10 ORDER BY spend_rank,c.customer_id;

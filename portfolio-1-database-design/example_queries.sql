-- These are inspection queries for Portfolio 1, not the Portfolio 2 benchmark.
-- 1. Customer and delivery details for five orders.
SELECT o.order_id, c.first_name || ' ' || c.last_name AS customer_name,
       a.city, w.warehouse_code, o.status, o.created_at
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
JOIN customer_addresses AS a
  ON a.customer_id = o.customer_id AND a.address_no = o.shipping_address_no
JOIN warehouses AS w ON w.warehouse_id = o.warehouse_id
ORDER BY o.order_id DESC
LIMIT 5;

-- 2. The same product has separately tracked stock at the two warehouses.
SELECT w.warehouse_code, p.sku, p.product_name,
       s.on_hand, s.reserved, s.available
FROM v_stock_availability AS s
JOIN products AS p ON p.product_id = s.product_id
JOIN warehouses AS w ON w.warehouse_id = s.warehouse_id
WHERE s.product_id = 1
ORDER BY w.warehouse_id;

-- 3. Stored historical prices and derived totals for order 1; all amounts in kobo.
SELECT i.order_id, i.line_no, p.sku, i.quantity, i.unit_price_kobo,
       i.quantity * i.unit_price_kobo AS line_total_kobo
FROM order_items AS i
JOIN products AS p ON p.product_id = i.product_id
WHERE i.order_id = 1
ORDER BY i.line_no;

SELECT order_id, item_total_kobo, delivery_fee_kobo, payable_kobo
FROM v_order_totals
WHERE order_id = 1;

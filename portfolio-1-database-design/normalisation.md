# Normalisation to third normal form

## Starting business record

An order worksheet could contain `(order_id, customer details, delivery address,
warehouse details, {product, category, quantity, agreed price}...)`. The repeating item
list is not first normal form. Flattening it gives one row per `(order_id, line_no)`, but
would repeat the customer, warehouse, product and category information on every line.

The meaningful dependencies, rather than accidental dependencies in this generated
sample, guide the design:

```
order_id -> customer_id, shipping_address_no, warehouse_id, status, created_at, delivery_fee_kobo
(order_id, line_no) -> product_id, quantity, unit_price_kobo
(order_id, product_id) -> line_no, quantity, unit_price_kobo
customer_id -> first_name, last_name, email
email -> customer_id, first_name, last_name
(customer_id, address_no) -> address_line, city, state, country_code
product_id -> sku, product_name, category_id, unit_price_kobo, active
sku -> product_id, product_name, category_id, unit_price_kobo, active
category_id -> category_name
warehouse_id -> warehouse_code, warehouse_name, city
(warehouse_id, product_id) -> on_hand, reserved
payment_id -> order_id, provider_reference, amount_kobo, status, attempted_at
provider_reference -> payment_id, order_id, amount_kobo, status, attempted_at
shipment_id -> order_id, tracking_reference, carrier, shipped_at, delivered_at
order_id -> shipment_id, tracking_reference, carrier, shipped_at, delivered_at  [within shipments]
```

## 1NF: remove repeating groups

Orders and order lines are separate relations. Every field in the business relations
contains one value of its declared type. Line numbers and quantities are integers;
prices are integer kobo. Arrays of products are not stored in an orders column.

## 2NF: remove partial-key dependencies

Order-header attributes depend on `order_id`, not on the whole line key, so they belong
in `orders`. The item relation retains only line-specific product, quantity and agreed
price. Inventory quantities depend on both warehouse and product. An address is
identified by `(customer_id, address_no)`; address number 1 is reused by different
customers and does not determine the customer.

## 3NF: remove transitive dependencies

Customer names and email do not appear in orders. Product descriptions are in products,
not order lines; category names are in categories, not products; warehouse descriptions
are in warehouses, not orders. A global address ID plus customer ID in orders would
introduce `order_id -> address_id -> customer_id`. The implementation deliberately
avoids that redundancy by using a customer-scoped composite address key. The composite
foreign key also prevents selecting an address number that the customer does not own.

All non-key business attributes depend on a candidate key, the whole key and no
non-key determinant under these business rules. Unique SKU, email, provider reference,
warehouse code, tracking reference and the one-shipment-per-order constraint supply
alternate keys where appropriate. The cross-entity `order_id` dependency shown above
is valid inside shipments only; it does not mean every order must already have a shipment.

`order_items.unit_price_kobo` is a historical fact determined by the order-line key. It
is not functionally determined by product ID: the same SKU can be sold at different
prices at different times. Similarly, payment amount is a fact about an attempted
charge; retaining it is necessary to audit a failed or successful payment. Successful
amounts are checked against a derived order-total view.

`available = on_hand - reserved` and order totals are views, not independent stored
columns. This prevents contradictory totals. `outbox.payload_json` is an intentional
integration-event envelope, not the authoritative normalised business model; the
NoSQL catalogue and distributed read model are likewise deliberate projections.

## Lossless reconstruction and anomalies avoided

Joining order lines to orders on the parent's primary key is lossless: every line has
exactly one valid parent. The same applies to the category, product, customer, address
and warehouse joins through their declared foreign keys. An update to a category name
changes one row; adding a product does not require an order; deleting an unpaid line
does not delete the customer. Historical address and paid-line triggers prevent changes
that would invalidate recorded transactions. The executable constraint suite tests
these rules instead of relying only on this explanation.

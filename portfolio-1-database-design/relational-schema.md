# Relational schema

Notation: PK = primary key; FK = foreign key; UQ = unique constraint. `schema.sql` is authoritative.

## categories

`categories(category_id [PK1], category_name)`

- Unique key: `category_name`.

## customer_addresses

`customer_addresses(customer_id [PK1], address_no [PK2], address_line, city, state, country_code)`

- FK component: `customer_id` -> `customers.customer_id` (group 0).
- Unique key: `customer_id, address_no`.

## customers

`customers(customer_id [PK1], first_name, last_name, email)`

- Unique key: `email`.

## inventory

`inventory(warehouse_id [PK1], product_id [PK2], on_hand, reserved)`

- FK component: `product_id` -> `products.product_id` (group 0).
- FK component: `warehouse_id` -> `warehouses.warehouse_id` (group 1).
- Unique key: `warehouse_id, product_id`.

## order_items

`order_items(order_id [PK1], line_no [PK2], product_id, quantity, unit_price_kobo)`

- FK component: `product_id` -> `products.product_id` (group 0).
- FK component: `order_id` -> `orders.order_id` (group 1).
- Unique key: `order_id, product_id`.
- Unique key: `order_id, line_no`.

## orders

`orders(order_id [PK1], customer_id, shipping_address_no, warehouse_id, status, created_at, delivery_fee_kobo)`

- FK component: `customer_id` -> `customer_addresses.customer_id` (group 0).
- FK component: `shipping_address_no` -> `customer_addresses.address_no` (group 0).
- FK component: `warehouse_id` -> `warehouses.warehouse_id` (group 1).
- FK component: `customer_id` -> `customers.customer_id` (group 2).

## outbox

`outbox(event_id [PK1], aggregate_type, aggregate_id, event_type, payload_json, occurred_at, processed_at)`

- Unique key: `event_id`.

## payment_attempts

`payment_attempts(payment_id [PK1], order_id, provider_reference, amount_kobo, status, attempted_at)`

- FK component: `order_id` -> `orders.order_id` (group 0).
- Unique key: `provider_reference`.

## products

`products(product_id [PK1], sku, product_name, category_id, unit_price_kobo, active)`

- FK component: `category_id` -> `categories.category_id` (group 0).
- Unique key: `sku`.

## shipments

`shipments(shipment_id [PK1], order_id, tracking_reference, carrier, shipped_at, delivered_at)`

- FK component: `order_id` -> `orders.order_id` (group 0).
- Unique key: `tracking_reference`.
- Unique key: `order_id`.

## warehouses

`warehouses(warehouse_id [PK1], warehouse_code, warehouse_name, city)`

- Unique key: `warehouse_code`.

The payment success rule uses a partial unique index. Other checks and all triggers are documented in `schema.sql`; generated `data_dictionary.csv` records the actual types and key positions.

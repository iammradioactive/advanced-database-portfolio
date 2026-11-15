# Lagoon Market: implemented table design

This supersedes the initial table sketch. `schema.sql` is the executable definition;
`relational-schema.md` lists its attributes, keys and foreign keys. The initial sketch
used broad business names. The implementation makes the following decisions explicit.

| Table | Purpose | Primary key |
|---|---|---|
| customers | Customer names and unique email | customer_id |
| customer_addresses | Customer-scoped, historical delivery addresses | customer_id + address_no |
| categories | Product categories | category_id |
| products | Unique SKU, category and current price | product_id |
| warehouses | Ikeja and Lekki warehouse details | warehouse_id |
| inventory | On-hand and reserved quantities at each warehouse | warehouse_id + product_id |
| orders | Customer, address, warehouse, state, date and delivery fee | order_id |
| order_items | Ordered products, quantities and historical unit prices | order_id + line_no |
| payment_attempts | Successful and failed simulated charges | payment_id |
| shipments | At most one shipment per order | shipment_id |
| outbox | Integration-event envelope for later portfolio activities | event_id |

`customer_addresses` replaces the sketch's generic `addresses` name. Its composite
key ensures that an order can use only an address registered to its own customer.
`order_items` uses `(order_id, line_no)` as its primary key and also enforces uniqueness
of `(order_id, product_id)`, preserving the no-duplicate-products rule.
`payment_attempts` and `shipments` are the implemented names for payments and deliveries.
`outbox` is the additional integration table; it is intentionally empty after seeding.

Prices are stored as positive integer kobo. Stock can be zero but not negative, and
reserved stock cannot exceed on-hand stock. A partial unique index prevents two
successful payment records for one order. Triggers preserve successful payment history,
paid order lines and referenced delivery addresses. The checkout service in Portfolio 3
will enforce atomic multi-row workflow operations; a schema alone does not implement checkout.

The seed contains synthetic data only. The customer phone field from the initial sketch
is not collected in this scoped implementation. No real payment gateway is contacted.

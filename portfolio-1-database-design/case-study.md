# Organisation and scope

Lagoon Market is a **simulated** online retailer selling groceries, household goods,
personal-care products, electronics, stationery and beverages. Its two fulfilment
centres are in Ikeja and Lekki. Customer-service agents retrieve order histories;
merchandisers maintain the catalogue; warehouse staff reserve stock and dispatch orders;
finance staff reconcile payment attempts; customers view products and delivery updates.
All people, addresses, orders and product brands in this portfolio are synthetic.

The database stores customers and their customer-scoped delivery addresses, categories,
products, warehouses, stock positions, orders, order lines, payment attempts, shipments
and integration events. Checkout reserves stock atomically. A successful payment must
match the order's calculated value; only one successful charge is allowed per order.
The project records simulated payment outcomes, not real gateway transactions. No card
numbers or financial account credentials are stored.

## Business boundaries

Each order is fulfilled by one warehouse and has at most one shipment. One customer may
have several numbered addresses. Referenced addresses are immutable: a change creates
a new address number so historical delivery information remains intact. Partial
shipments, cross-warehouse orders, refunds, tax calculations and multiple currencies
are deliberately outside this implementation. Monetary amounts are NGN kobo integers.
An order line records the price agreed at purchase, not a pointer to today's selling
price. Product price changes therefore cannot rewrite order history.

The relational store is authoritative for stock and payment state. A rebuildable
key-value catalogue supports read-oriented product access. The distributed exercise
shards the delivery-tracking projection, not the authoritative inventory transaction.
This separation avoids pretending that a local SQLite transaction is a distributed
transaction across all stores.

## Data provenance

`seed.py` uses only Python's standard library and random seed 8103. It generates 5,000
customers, 5,050 addresses, 600 products, two warehouses, 120,000 orders and their related
records. Orders cover 1 January to 13 November 2026. Email addresses use the reserved
`example.invalid` suffix. The generated state is a historical snapshot; inventory
on-hand is a synthetic opening balance plus current reservations, not a reconstruction
of every purchase and goods-receipt movement during the year. Active reservations are
reconciled against RESERVED and PAID order lines by a test.

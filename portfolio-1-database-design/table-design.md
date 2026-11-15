# Lagoon Market: Initial Table Design

## Purpose

This document identifies the main tables and relationships for Lagoon Market.

## Proposed Tables

| Table | Information stored | Primary key |
|---|---|---|
| customers | Customer names, email addresses and phone numbers | customer_id |
| addresses | Customers' delivery addresses | address_id |
| categories | Product categories, such as groceries and electronics | category_id |
| products | Product names, categories and current prices | product_id |
| warehouses | Warehouse names and locations | warehouse_id |
| inventory | Stock quantities for each product at each warehouse | warehouse_id + product_id |
| orders | Customer, delivery address, fulfilment warehouse, order date and status | order_id |
| order_items | Products in an order, quantities and agreed unit prices | order_id + product_id |
| payments | Payment attempts, amounts, references and statuses | payment_id |
| deliveries | Delivery tracking references and statuses | delivery_id |

## Relationships

A customer can have several delivery addresses and place several orders. Each address and order belongs to one customer.

Each product belongs to one category. A category can contain many products.

A product can be stocked at both warehouses. The inventory table records each product-and-warehouse combination separately.

For this project, each order is fulfilled by one warehouse and sent to one delivery address belonging to its customer. Splitting one order across warehouses is outside the scope.

An order can contain several order items. Each item refers to one product. The same product appears only once per order; its quantity records how many units were purchased.

An order can have several payment attempts, but no more than one successful payment. Split payments and refunds are outside the scope of this initial implementation.

An order has no delivery record before dispatch and at most one delivery record afterwards.

## Key Design Decisions

The inventory table uses warehouse_id and product_id together to identify a stock record. This allows the same product to have different stock quantities at Ikeja and Lekki.

The order_items table uses order_id and product_id together to identify an item within an order.

The agreed unit price is stored in order_items. Later changes to a product's current price must not alter an earlier order.

Delivery addresses referenced by existing orders will be preserved. A changed address will be stored as a new record rather than overwriting an address used by an earlier order.

## Constraints to Implement and Test

- Customer email addresses must be unique.
- Order quantities must be greater than zero.
- Prices and stock quantities must not be negative.
- Each order must reference an existing customer.
- Each order item must reference an existing order and product.
- An order's delivery address must belong to its customer.
- A confirmed order must contain at least one order item.
- Checkout must not allocate more stock than is available.

Some rules will require transaction logic or triggers in addition to ordinary table constraints. The SQL implementation will document how each rule is enforced.

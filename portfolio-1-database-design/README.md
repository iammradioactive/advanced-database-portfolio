# Portfolio 1: Database Design and Modelling

## Organisation

Lagoon Market is a fictional online retailer selling household goods, groceries and electronics. It manages stock at its Ikeja and Lekki warehouses.

## Business Rules

1. A customer can place many orders. Each order belongs to one customer.

2. A confirmed order must contain at least one order item. Each item identifies a product, the quantity ordered and the agreed unit price.

3. The agreed unit price is stored on the order item. Changing a product's current price must not change the value of an earlier order.

4. Each product belongs to one product category.

5. Stock is recorded separately for each combination of product and warehouse.

6. Order quantities must be positive. Stock quantities must not be negative.

7. Checkout must not reserve more stock than is available. A failed checkout must undo its database changes.

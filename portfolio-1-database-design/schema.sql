-- Lagoon Market / SQLite >= 3.37. All monetary amounts are integer NGN kobo.
-- Foreign-key enforcement is connection-local; every application enables it.
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=FULL;
BEGIN;
CREATE TABLE categories (
 category_id INTEGER PRIMARY KEY,
 category_name TEXT NOT NULL UNIQUE
) STRICT;
CREATE TABLE products (
 product_id INTEGER PRIMARY KEY,
 sku TEXT NOT NULL UNIQUE,
 product_name TEXT NOT NULL,
 category_id INTEGER NOT NULL REFERENCES categories(category_id),
 unit_price_kobo INTEGER NOT NULL CHECK(unit_price_kobo>0),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
) STRICT;
CREATE TABLE customers (
 customer_id INTEGER PRIMARY KEY,
 first_name TEXT NOT NULL,
 last_name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE CHECK(email=lower(email) AND instr(email,'@')>1)
) STRICT;
CREATE TABLE customer_addresses (
 customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 address_no INTEGER NOT NULL CHECK(address_no>0),
 address_line TEXT NOT NULL,
 city TEXT NOT NULL,
 state TEXT NOT NULL,
 country_code TEXT NOT NULL DEFAULT 'NG' CHECK(length(country_code)=2),
 PRIMARY KEY(customer_id,address_no)
) STRICT;
CREATE TABLE warehouses (
 warehouse_id INTEGER PRIMARY KEY,
 warehouse_code TEXT NOT NULL UNIQUE,
 warehouse_name TEXT NOT NULL,
 city TEXT NOT NULL
) STRICT;
CREATE TABLE inventory (
 warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
 product_id INTEGER NOT NULL REFERENCES products(product_id),
 on_hand INTEGER NOT NULL CHECK(on_hand>=0),
 reserved INTEGER NOT NULL DEFAULT 0 CHECK(reserved>=0 AND reserved<=on_hand),
 PRIMARY KEY(warehouse_id,product_id)
) STRICT;
CREATE TABLE orders (
 order_id INTEGER PRIMARY KEY,
 customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 shipping_address_no INTEGER NOT NULL,
 warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
 status TEXT NOT NULL CHECK(status IN ('PENDING','RESERVED','PAID','DISPATCHED','DELIVERED','CANCELLED')),
 created_at TEXT NOT NULL CHECK(strftime('%Y-%m-%dT%H:%M:%SZ',created_at) IS NOT NULL
                                AND strftime('%Y-%m-%dT%H:%M:%SZ',created_at)=created_at),
 delivery_fee_kobo INTEGER NOT NULL DEFAULT 0 CHECK(delivery_fee_kobo>=0),
 FOREIGN KEY(customer_id,shipping_address_no)
   REFERENCES customer_addresses(customer_id,address_no)
) STRICT;
CREATE TABLE order_items (
 order_id INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
 line_no INTEGER NOT NULL CHECK(line_no>0),
 product_id INTEGER NOT NULL REFERENCES products(product_id),
 quantity INTEGER NOT NULL CHECK(quantity>0),
 unit_price_kobo INTEGER NOT NULL CHECK(unit_price_kobo>0),
 PRIMARY KEY(order_id,line_no),
 UNIQUE(order_id,product_id)
) STRICT;
CREATE TABLE payment_attempts (
 payment_id INTEGER PRIMARY KEY,
 order_id INTEGER NOT NULL REFERENCES orders(order_id),
 provider_reference TEXT NOT NULL UNIQUE,
 amount_kobo INTEGER NOT NULL CHECK(amount_kobo>0),
 status TEXT NOT NULL CHECK(status IN ('SUCCEEDED','FAILED')),
 attempted_at TEXT NOT NULL
) STRICT;
CREATE UNIQUE INDEX uq_one_successful_payment
 ON payment_attempts(order_id) WHERE status='SUCCEEDED';
CREATE TABLE shipments (
 shipment_id INTEGER PRIMARY KEY,
 order_id INTEGER NOT NULL UNIQUE REFERENCES orders(order_id),
 tracking_reference TEXT NOT NULL UNIQUE,
 carrier TEXT NOT NULL,
 shipped_at TEXT NOT NULL,
 delivered_at TEXT,
 CHECK(delivered_at IS NULL OR delivered_at>=shipped_at)
) STRICT;
CREATE TABLE outbox (
 event_id TEXT PRIMARY KEY,
 aggregate_type TEXT NOT NULL CHECK(aggregate_type IN ('order','product')),
 aggregate_id INTEGER NOT NULL,
 event_type TEXT NOT NULL,
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
 occurred_at TEXT NOT NULL,
 processed_at TEXT
) STRICT;
CREATE VIEW v_order_totals AS
 SELECT o.order_id, COALESCE(SUM(i.quantity*i.unit_price_kobo),0) AS item_total_kobo,
        o.delivery_fee_kobo,
        COALESCE(SUM(i.quantity*i.unit_price_kobo),0)+o.delivery_fee_kobo AS payable_kobo
 FROM orders o LEFT JOIN order_items i ON i.order_id=o.order_id
 GROUP BY o.order_id;
CREATE VIEW v_stock_availability AS
 SELECT warehouse_id,product_id,on_hand,reserved,on_hand-reserved AS available
 FROM inventory;
CREATE TRIGGER successful_payment_amount_insert
 BEFORE INSERT ON payment_attempts WHEN NEW.status='SUCCEEDED'
 BEGIN
   SELECT CASE WHEN NEW.amount_kobo<>(SELECT payable_kobo FROM v_order_totals WHERE order_id=NEW.order_id)
     THEN RAISE(ABORT,'successful payment must equal order payable amount') END;
 END;
CREATE TRIGGER successful_payment_amount_update
 BEFORE UPDATE ON payment_attempts WHEN NEW.status='SUCCEEDED'
 BEGIN
   SELECT CASE WHEN NEW.amount_kobo<>(SELECT payable_kobo FROM v_order_totals WHERE order_id=NEW.order_id)
     THEN RAISE(ABORT,'successful payment must equal order payable amount') END;
 END;
CREATE TRIGGER protect_paid_line_update BEFORE UPDATE ON order_items
 WHEN EXISTS(SELECT 1 FROM payment_attempts WHERE order_id IN (OLD.order_id,NEW.order_id) AND status='SUCCEEDED')
 BEGIN SELECT RAISE(ABORT,'paid order lines are immutable'); END;
CREATE TRIGGER protect_paid_line_delete BEFORE DELETE ON order_items
 WHEN EXISTS(SELECT 1 FROM payment_attempts WHERE order_id=OLD.order_id AND status='SUCCEEDED')
 BEGIN SELECT RAISE(ABORT,'paid order lines are immutable'); END;
CREATE TRIGGER protect_paid_line_insert BEFORE INSERT ON order_items
 WHEN EXISTS(SELECT 1 FROM payment_attempts WHERE order_id=NEW.order_id AND status='SUCCEEDED')
 BEGIN SELECT RAISE(ABORT,'paid order lines are immutable'); END;
CREATE TRIGGER protect_paid_fee BEFORE UPDATE OF delivery_fee_kobo ON orders
 WHEN EXISTS(SELECT 1 FROM payment_attempts WHERE order_id=OLD.order_id AND status='SUCCEEDED')
 BEGIN SELECT RAISE(ABORT,'paid delivery fee is immutable'); END;
CREATE TRIGGER protect_used_address BEFORE UPDATE ON customer_addresses
 WHEN EXISTS(SELECT 1 FROM orders WHERE customer_id=OLD.customer_id AND shipping_address_no=OLD.address_no)
 BEGIN SELECT RAISE(ABORT,'used delivery address is immutable; create a new address'); END;
CREATE TRIGGER protect_successful_payment_update BEFORE UPDATE ON payment_attempts
 WHEN OLD.status='SUCCEEDED'
 BEGIN SELECT RAISE(ABORT,'successful payment history is immutable'); END;
CREATE TRIGGER protect_successful_payment_delete BEFORE DELETE ON payment_attempts
 WHEN OLD.status='SUCCEEDED'
 BEGIN SELECT RAISE(ABORT,'successful payment history is immutable'); END;
PRAGMA user_version=2;
COMMIT;

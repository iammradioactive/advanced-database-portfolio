-- Executable SQLite transaction examples on a disposable copy of the seeded database.
-- tools/sql_console.py accepts this file. Rollback ensures the canonical state is unchanged.
PRAGMA foreign_keys=ON;
BEGIN IMMEDIATE;
UPDATE inventory SET reserved=reserved+1
 WHERE warehouse_id=1 AND product_id=1 AND on_hand-reserved>=1;
SELECT warehouse_id,product_id,on_hand,reserved,on_hand-reserved AS available
 FROM inventory WHERE warehouse_id=1 AND product_id=1;
SAVEPOINT optional_step;
UPDATE inventory SET reserved=reserved+1
 WHERE warehouse_id=1 AND product_id=1 AND on_hand-reserved>=1;
ROLLBACK TO optional_step;
RELEASE optional_step;
-- Demonstrate rollback of the first change too.
ROLLBACK;
BEGIN IMMEDIATE;
-- A committed no-op does not change business stock; actual checkout commits are in service.py.
UPDATE inventory SET reserved=reserved WHERE warehouse_id=1 AND product_id=1;
COMMIT;

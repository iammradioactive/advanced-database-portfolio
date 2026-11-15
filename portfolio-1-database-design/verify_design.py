"""Exercise enforced constraints and check cross-table business invariants."""
import json, sqlite3, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import connect,write_json,utc_now
HERE=Path(__file__).resolve().parent

def main():
    c=connect(); results=[]
    def reject(name,sql,params=()):
        c.execute('SAVEPOINT constraint_test')
        try:
            c.execute(sql,params)
        except sqlite3.IntegrityError as e:
            results.append({'test':name,'passed':True,'error':str(e),'code':e.sqlite_errorname})
        else:
            results.append({'test':name,'passed':False,'error':'invalid value was accepted'})
        finally:
            c.execute('ROLLBACK TO constraint_test'); c.execute('RELEASE constraint_test')
    reject('duplicate customer email',"INSERT INTO customers VALUES (999999,'Test','User','customer00001@example.invalid')")
    reject('missing category foreign key',"INSERT INTO products VALUES (999999,'TEST-999','Test',999999,100,1)")
    reject('zero product price','UPDATE products SET unit_price_kobo=0 WHERE product_id=1')
    reject('strict integer quantity',"UPDATE inventory SET reserved='invalid' WHERE warehouse_id=1 AND product_id=1")
    reject('negative stock','UPDATE inventory SET on_hand=-1 WHERE warehouse_id=1 AND product_id=1')
    reject('reserved exceeds stock','UPDATE inventory SET reserved=on_hand+1 WHERE warehouse_id=1 AND product_id=1')
    reject('address number not registered to this customer',"INSERT INTO orders VALUES (999999,1,2,1,'PENDING','2026-11-14T12:00:00Z',100)")
    reject('unknown order state',"UPDATE orders SET status='UNKNOWN' WHERE order_id=1")
    reject('noncanonical timestamp',"UPDATE orders SET created_at='yesterday' WHERE order_id=1")
    pending=c.execute("SELECT order_id FROM orders WHERE status='PENDING' LIMIT 1").fetchone()[0]
    reject('zero order-line quantity','UPDATE order_items SET quantity=0 WHERE order_id=? AND line_no=1',(pending,))
    reject('duplicate product per order','INSERT INTO order_items SELECT order_id,99,product_id,1,unit_price_kobo FROM order_items WHERE order_id=? AND line_no=1',(pending,))
    paid=c.execute("SELECT order_id FROM payment_attempts WHERE status='SUCCEEDED' LIMIT 1").fetchone()[0]
    reject('wrong successful payment amount',"INSERT INTO payment_attempts VALUES (999999,?,'TEST-WRONG',1,'SUCCEEDED','2026-11-14T12:00:00Z')",(pending,))
    total=c.execute('SELECT payable_kobo FROM v_order_totals WHERE order_id=?',(paid,)).fetchone()[0]
    reject('second successful charge',"INSERT INTO payment_attempts VALUES (999999,?,'TEST-DUP',?,'SUCCEEDED','2026-11-14T12:00:00Z')",(paid,total))
    reject('paid line modification','UPDATE order_items SET quantity=quantity+1 WHERE order_id=? AND line_no=1',(paid,))
    reject('paid delivery fee modification','UPDATE orders SET delivery_fee_kobo=delivery_fee_kobo+1 WHERE order_id=?',(paid,))
    reject('invalid outbox JSON',"INSERT INTO outbox VALUES ('bad','order',1,'test','not-json','2026-11-14T12:00:00Z',NULL)")
    reject('delivery before dispatch',"UPDATE shipments SET delivered_at='2020-01-01T00:00:00Z' WHERE shipment_id=1")
    reject('mutation of historical address',"UPDATE customer_addresses SET address_line='changed' WHERE customer_id=1 AND address_no=1")
    movable=c.execute('''SELECT order_id,line_no FROM order_items i WHERE order_id=?
      AND NOT EXISTS(SELECT 1 FROM order_items p WHERE p.order_id=? AND p.product_id=i.product_id)
      LIMIT 1''',(pending,paid)).fetchone()
    assert movable is not None,'need a distinct pending line for the cross-parent test'
    reject('moving an unpaid line into a paid order','UPDATE order_items SET order_id=?,line_no=999 WHERE order_id=? AND line_no=?',(paid,*movable))
    reject('rewriting successful payment history',"UPDATE payment_attempts SET status='FAILED' WHERE order_id=? AND status='SUCCEEDED'",(paid,))
    reject('deleting successful payment history',"DELETE FROM payment_attempts WHERE order_id=? AND status='SUCCEEDED'",(paid,))
    checks={
      'integrity_check':c.execute('PRAGMA integrity_check').fetchone()[0],
      'foreign_key_errors':c.execute('PRAGMA foreign_key_check').fetchall(),
      'mismatched_successful_payments':c.execute("SELECT count(*) FROM payment_attempts p JOIN v_order_totals t ON t.order_id=p.order_id WHERE p.status='SUCCEEDED' AND p.amount_kobo<>t.payable_kobo").fetchone()[0],
      'reserved_inventory_mismatches':c.execute("""SELECT count(*) FROM inventory inv LEFT JOIN
        (SELECT o.warehouse_id,i.product_id,sum(i.quantity) qty FROM orders o JOIN order_items i USING(order_id)
         WHERE o.status IN ('RESERVED','PAID') GROUP BY o.warehouse_id,i.product_id) x
         ON x.warehouse_id=inv.warehouse_id AND x.product_id=inv.product_id
         WHERE inv.reserved<>coalesce(x.qty,0)""").fetchone()[0],
      'shipped_orders_without_shipment':c.execute("SELECT count(*) FROM orders o LEFT JOIN shipments s USING(order_id) WHERE o.status IN ('DISPATCHED','DELIVERED') AND s.shipment_id IS NULL").fetchone()[0]
    }
    all_passed=all(x['passed'] for x in results) and checks['integrity_check']=='ok' and not checks['foreign_key_errors'] and all(checks[k]==0 for k in ('mismatched_successful_payments','reserved_inventory_mismatches','shipped_orders_without_shipment'))
    out={'executed_at_utc':utc_now(),'constraint_tests':results,'cross_table_checks':checks,'all_passed':all_passed}
    write_json(HERE/'results'/'design_checks.json',out)
    print(json.dumps(out,indent=2)); c.close()
    assert all_passed,'Design verification failed; inspect results/design_checks.json'
if __name__=='__main__':main()

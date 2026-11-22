"""Reproducible transaction/isolation tests with actual concurrent connections."""
from __future__ import annotations
import json, sqlite3, sys, threading, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import ROOT,DB,RUNTIME,connect,backup,write_json,utc_now
from service import reserve_order,record_successful_payment,InsufficientStock
HERE=Path(__file__).resolve().parent
TESTDB=RUNTIME/'transactions.sqlite'; TRACE=[]; LOCK=threading.Lock(); RESULTS=[]

def conn(actor='main',path=TESTDB,**kwargs):
 c=connect(path,**kwargs)
 def trace(sql):
    with LOCK: TRACE.append({'at_utc':utc_now(),'connection':actor,'sql':sql})
 c.set_trace_callback(trace);return c

def record(test,**observations):
 RESULTS.append({'test':test,'passed':True,**observations})
 print(json.dumps(RESULTS[-1],default=str))

def reset_fixture():
 with conn('fixture') as c:
    c.execute('UPDATE inventory SET on_hand=10,reserved=0 WHERE warehouse_id=1 AND product_id=1')
def value(c):return c.execute('SELECT reserved FROM inventory WHERE warehouse_id=1 AND product_id=1').fetchone()[0]

def main():
 backup(DB,TESTDB)
 a=conn('checkout');before=a.execute('SELECT reserved FROM inventory WHERE warehouse_id=1 AND product_id=1').fetchone()[0]
 count_before=a.execute('SELECT count(*) FROM orders').fetchone()[0]
 oid=reserve_order(a,customer_id=1,address_no=1,warehouse_id=1,cart=[(1,2),(2,1)],request_key='portfolio-checkout')
 after=value(a); a.close()
 a=conn('reopened')
 assert after==before+2 and a.execute('SELECT status FROM orders WHERE order_id=?',(oid,)).fetchone()[0]=='RESERVED'
 assert a.execute('SELECT count(*) FROM orders').fetchone()[0]==count_before+1
 record('T01 COMMIT and reopen durability',order_id=oid,reserved_before=before,reserved_after=after,order_lines=2)
 repeated=reserve_order(a,customer_id=1,address_no=1,warehouse_id=1,cart=[(1,2),(2,1)],request_key='portfolio-checkout')
 assert repeated==oid and value(a)==after
 try: reserve_order(a,customer_id=1,address_no=1,warehouse_id=1,cart=[(1,3)],request_key='portfolio-checkout')
 except ValueError as e: conflict=str(e)
 else:raise AssertionError('conflicting idempotency key accepted')
 record('T02 Idempotent checkout',same_order_id=repeated,duplicate_reservation=False,conflicting_request_error=conflict)
 counts_before=[a.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('orders','order_items','outbox')]
 inventory_before=a.execute('SELECT * FROM inventory WHERE warehouse_id=1 AND product_id IN (1,2) ORDER BY product_id').fetchall()
 available2=a.execute('SELECT available FROM v_stock_availability WHERE warehouse_id=1 AND product_id=2').fetchone()[0]
 try: reserve_order(a,customer_id=1,address_no=1,warehouse_id=1,cart=[(1,1),(2,available2+1)],request_key='fail-after-first-line')
 except InsufficientStock as e:reason=str(e)
 else:raise AssertionError('oversized reservation succeeded')
 counts_after=[a.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('orders','order_items','outbox')]
 inventory_after=a.execute('SELECT * FROM inventory WHERE warehouse_id=1 AND product_id IN (1,2) ORDER BY product_id').fetchall()
 assert counts_before==counts_after and inventory_before==inventory_after
 record('T03 ROLLBACK after a partial multi-item operation',error=reason,counts_before=counts_before,counts_after=counts_after,first_item_reservation_undone=True)
 pid=record_successful_payment(a,order_id=oid,provider_reference='SIMULATED-PAY-8103')
 pid2=record_successful_payment(a,order_id=oid,provider_reference='SIMULATED-PAY-8103')
 assert pid==pid2 and a.execute('SELECT status FROM orders WHERE order_id=?',(oid,)).fetchone()[0]=='PAID'
 record('T04 Payment transaction',payment_id=pid,repeat_payment_id=pid2,order_state='PAID',real_gateway_called=False)
 original=a.execute('SELECT on_hand,reserved FROM inventory WHERE warehouse_id=1 AND product_id=1').fetchone();a.close()
 reset_fixture();a=conn('savepoint');a.execute('BEGIN IMMEDIATE')
 a.execute('UPDATE inventory SET reserved=reserved+1 WHERE warehouse_id=1 AND product_id=1');a.execute('SAVEPOINT optional_reservation')
 try:a.execute('UPDATE inventory SET reserved=11 WHERE warehouse_id=1 AND product_id=1')
 except sqlite3.IntegrityError:
    a.execute('ROLLBACK TO optional_reservation');a.execute('RELEASE optional_reservation')
 else:raise AssertionError('CHECK did not reject over-reservation')
 a.execute('COMMIT');assert value(a)==1
 record('T05 SAVEPOINT rollback retains prior valid statement',committed_reserved=1,rejected_reserved=11);a.close()
 reset_fixture();a=conn('dirty-A');b=conn('dirty-B')
 a.execute('BEGIN IMMEDIATE');a.execute('UPDATE inventory SET reserved=4 WHERE warehouse_id=1 AND product_id=1')
 writer=value(a);reader=value(b);a.execute('ROLLBACK');after_rollback=value(b)
 assert (writer,reader,after_rollback)==(4,0,0)
 record('T06 Default isolation prevents dirty reads',writer_uncommitted=writer,reader_observed=reader,reader_after_rollback=after_rollback);a.close();b.close()
 reset_fixture();a=conn('snapshot-A');b=conn('snapshot-B')
 a.execute('BEGIN');first=value(a)
 b.execute('BEGIN IMMEDIATE');b.execute('UPDATE inventory SET reserved=2 WHERE warehouse_id=1 AND product_id=1');b.execute('COMMIT')
 second=value(a)
 try:a.execute('UPDATE inventory SET reserved=reserved+1 WHERE warehouse_id=1 AND product_id=1')
 except sqlite3.OperationalError as e:code=e.sqlite_errorname
 else:raise AssertionError('stale snapshot write unexpectedly succeeded')
 a.execute('ROLLBACK');a.execute('BEGIN IMMEDIATE');fresh=value(a)
 a.execute('UPDATE inventory SET reserved=reserved+1 WHERE warehouse_id=1 AND product_id=1');a.execute('COMMIT')
 final=value(a);assert first==second==0 and fresh==2 and final==3 and code=='SQLITE_BUSY_SNAPSHOT'
 record('T07 WAL snapshot and full-transaction retry',first_read=first,repeat_read=second,write_error=code,retry_read=fresh,final_reserved=final);a.close();b.close()
 # Deliberately opt in to discouraged shared-cache mode on a separate fixture file.
 dirty=RUNTIME/'shared_cache.sqlite';backup(DB,dirty)
 with connect(dirty) as d:
    d.execute('PRAGMA journal_mode=DELETE');d.execute('UPDATE inventory SET on_hand=10,reserved=0 WHERE warehouse_id=1 AND product_id=1')
 uri=dirty.resolve().as_uri()+'?cache=shared'
 a=conn('shared-A',uri,uri=True);b=conn('shared-B',uri,uri=True)
 a.execute('BEGIN IMMEDIATE');a.execute('UPDATE inventory SET reserved=4 WHERE warehouse_id=1 AND product_id=1')
 try:value(b)
 except sqlite3.OperationalError as e:default_error=e.sqlite_errorname
 else:raise AssertionError('default shared cache allowed dirty read')
 b.execute('PRAGMA read_uncommitted=1');dirty_read=value(b);a.execute('ROLLBACK');rolled_back=value(b)
 assert dirty_read==4 and rolled_back==0 and default_error=='SQLITE_LOCKED_SHAREDCACHE'
 record('T08 READ UNCOMMITTED with shared cache',default_read_error=default_error,dirty_read=dirty_read,after_writer_rollback=rolled_back,production_setting=False);a.close();b.close()
 reset_fixture();reads={};errors=[];barrier=threading.Barrier(2);first_written=threading.Event()
 def stale_worker(name):
    c=conn('stale-'+name)
    try:
      old=value(c);reads[name]=old;barrier.wait(timeout=3)
      if name=='B': assert first_written.wait(3)
      c.execute('UPDATE inventory SET reserved=? WHERE warehouse_id=1 AND product_id=1',(old+3,))
      if name=='A':first_written.set()
    except BaseException as e:errors.append(repr(e));first_written.set()
    finally:c.close()
 threads=[threading.Thread(target=stale_worker,args=(n,)) for n in ('A','B')]
 for t in threads:t.start()
 for t in threads:t.join(5)
 assert not errors and not any(t.is_alive() for t in threads)
 with conn('lost-check') as c:final=value(c)
 assert reads=={'A':0,'B':0} and final==3
 record('T09 Stale-read lost update reproduced',client_reads=reads,expected_if_both_preserved=6,actual_reserved=final,scope='reads and writes in separate autocommit transactions')
 reset_fixture();held=threading.Event();observed={};waits={};errors=[]
 def protected_worker(name):
    c=conn('protected-'+name)
    try:
      if name=='B':assert held.wait(3)
      start=time.perf_counter();c.execute('BEGIN IMMEDIATE');waits[name]=(time.perf_counter()-start)*1000
      old=value(c);observed[name]=old
      if name=='A':held.set();time.sleep(0.08)
      c.execute('UPDATE inventory SET reserved=? WHERE warehouse_id=1 AND product_id=1',(old+3,));c.execute('COMMIT')
    except BaseException as e:
      errors.append(repr(e));held.set()
      if c.in_transaction:c.execute('ROLLBACK')
    finally:c.close()
 threads=[threading.Thread(target=protected_worker,args=(n,)) for n in ('A','B')]
 for t in threads:t.start()
 for t in threads:t.join(5)
 assert not errors and not any(t.is_alive() for t in threads)
 with conn('protected-check') as c:final=value(c)
 assert observed=={'A':0,'B':3} and final==6
 record('T10 BEGIN IMMEDIATE prevents stale reservation update',client_reads=observed,final_reserved=final,writer_begin_wait_ms=waits)
 reset_fixture();barrier=threading.Barrier(2);outcomes=[];errors=[]
 def guard_worker(name):
    c=conn('guard-'+name)
    try:
      barrier.wait(timeout=3)
      cur=c.execute('UPDATE inventory SET reserved=reserved+7 WHERE warehouse_id=1 AND product_id=1 AND on_hand-reserved>=7')
      outcomes.append({'client':name,'rows_updated':cur.rowcount})
    except BaseException as e:errors.append(repr(e))
    finally:c.close()
 threads=[threading.Thread(target=guard_worker,args=(n,)) for n in ('A','B')]
 for t in threads:t.start()
 for t in threads:t.join(5)
 assert not errors and not any(t.is_alive() for t in threads)
 with conn('guard-check') as c:final=value(c)
 assert sorted(x['rows_updated'] for x in outcomes)==[0,1] and final==7
 record('T11 Atomic predicate prevents overselling',requested_by_each=7,available_initially=10,outcomes=outcomes,final_reserved=final)
 reset_fixture();a=conn('lock-A');b=conn('lock-B',timeout=0.05)
 a.execute('BEGIN IMMEDIATE');start=time.perf_counter()
 try:b.execute('UPDATE inventory SET reserved=reserved+1 WHERE warehouse_id=1 AND product_id=1')
 except sqlite3.OperationalError as e:lock_error=e.sqlite_errorname
 else:raise AssertionError('second writer acquired a held lock')
 waited=(time.perf_counter()-start)*1000;a.execute('ROLLBACK')
 b.execute('UPDATE inventory SET reserved=reserved+1 WHERE warehouse_id=1 AND product_id=1');assert value(b)==1 and lock_error=='SQLITE_BUSY'
 record('T12 Busy timeout and retry after release',blocked_error=lock_error,elapsed_ms=waited,retry_reserved=1);a.close();b.close()
 # Restore the controlled stock fixture; real checkout/payment effects remain in the test copy.
 with conn('restore') as c:
    c.execute('UPDATE inventory SET on_hand=?,reserved=? WHERE warehouse_id=1 AND product_id=1',original)
    integrity=c.execute('PRAGMA integrity_check').fetchone()[0]
    mismatches=c.execute("""SELECT count(*) FROM inventory inv LEFT JOIN
       (SELECT o.warehouse_id,i.product_id,sum(i.quantity) qty FROM orders o JOIN order_items i USING(order_id)
        WHERE o.status IN ('RESERVED','PAID') GROUP BY o.warehouse_id,i.product_id) x
       ON inv.warehouse_id=x.warehouse_id AND inv.product_id=x.product_id
       WHERE inv.reserved<>coalesce(x.qty,0)""").fetchone()[0]
    assert integrity=='ok' and mismatches==0
    c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
 out={'executed_at_utc':utc_now(),'database':'isolated backup; canonical dataset unchanged','tests':RESULTS,'passed_count':len(RESULTS),'all_passed':True,'final_integrity':integrity,'final_reservation_mismatches':mismatches}
 write_json(HERE/'results'/'transaction_tests.json',out)
 write_json(HERE/'results'/'sql_trace.json',TRACE)
 (HERE/'results'/'sql_trace.txt').write_text('\n'.join(f"{x['at_utc']} [{x['connection']}] {x['sql']}" for x in TRACE)+'\n')
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()

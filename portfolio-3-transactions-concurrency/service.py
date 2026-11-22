"""Transactional checkout service. SQLite remains the stock/payment authority.
All reads needed for a stock decision occur after BEGIN IMMEDIATE. Errors roll back
the order, every line, the reservation changes, and the outbox event together.
"""
from __future__ import annotations
import hashlib, json, sqlite3
from collections import Counter
from datetime import datetime, timezone

class InsufficientStock(ValueError): pass

def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def fingerprint(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def reserve_order(con, *, customer_id:int, address_no:int, warehouse_id:int,
                  cart:list[tuple[int,int]], request_key:str, delivery_fee_kobo:int=150000)->int:
    if not request_key or not cart or delivery_fee_kobo<0: raise ValueError('invalid checkout input')
    quantities=Counter()
    for product,quantity in cart:
        if type(product) is not int or type(quantity) is not int or product<=0 or quantity<=0:
            raise ValueError('product and quantity must be positive integers')
        quantities[product]+=quantity
    request={'customer_id':customer_id,'address_no':address_no,'warehouse_id':warehouse_id,
             'cart':sorted(quantities.items()),'delivery_fee_kobo':delivery_fee_kobo}
    request_hash=fingerprint(request);event_id='checkout:'+request_key
    con.execute('BEGIN IMMEDIATE')
    try:
        previous=con.execute('SELECT aggregate_id,payload_json FROM outbox WHERE event_id=?',(event_id,)).fetchone()
        if previous:
            if json.loads(previous[1])['request_hash']!=request_hash:
                raise ValueError('idempotency key reused with a different request')
            con.execute('COMMIT');return previous[0]
        timestamp=now()
        cur=con.execute("INSERT INTO orders(customer_id,shipping_address_no,warehouse_id,status,created_at,delivery_fee_kobo) VALUES (?,?,?,'RESERVED',?,?)",(customer_id,address_no,warehouse_id,timestamp,delivery_fee_kobo))
        order_id=cur.lastrowid
        for line,(product,quantity) in enumerate(sorted(quantities.items()),1):
            row=con.execute('SELECT unit_price_kobo FROM products WHERE product_id=? AND active=1',(product,)).fetchone()
            if row is None: raise ValueError('product missing or inactive')
            cur=con.execute('UPDATE inventory SET reserved=reserved+? WHERE warehouse_id=? AND product_id=? AND on_hand-reserved>=?',(quantity,warehouse_id,product,quantity))
            if cur.rowcount!=1: raise InsufficientStock(f'insufficient stock for product {product}')
            con.execute('INSERT INTO order_items VALUES (?,?,?,?,?)',(order_id,line,product,quantity,row[0]))
        payload=json.dumps({'order_id':order_id,'request_hash':request_hash,'items':sorted(quantities.items())})
        con.execute("INSERT INTO outbox VALUES (?,'order',?,'order.reserved',?,?,NULL)",(event_id,order_id,payload,timestamp))
        con.execute('COMMIT');return order_id
    except BaseException:
        if con.in_transaction:con.execute('ROLLBACK')
        raise

def record_successful_payment(con, *, order_id:int, provider_reference:str)->int:
    """Record a simulated successful provider response. No real provider is called."""
    con.execute('BEGIN IMMEDIATE')
    try:
        prior=con.execute('SELECT payment_id,order_id,status FROM payment_attempts WHERE provider_reference=?',(provider_reference,)).fetchone()
        if prior:
            if prior[1]!=order_id or prior[2]!='SUCCEEDED':raise ValueError('provider reference conflict')
            con.execute('COMMIT');return prior[0]
        row=con.execute('SELECT status FROM orders WHERE order_id=?',(order_id,)).fetchone()
        if row is None or row[0]!='RESERVED':raise ValueError('payment requires a RESERVED order')
        amount=con.execute('SELECT payable_kobo FROM v_order_totals WHERE order_id=?',(order_id,)).fetchone()[0]
        timestamp=now()
        cur=con.execute("INSERT INTO payment_attempts(order_id,provider_reference,amount_kobo,status,attempted_at) VALUES (?,?,?,'SUCCEEDED',?)",(order_id,provider_reference,amount,timestamp))
        pid=cur.lastrowid
        con.execute("UPDATE orders SET status='PAID' WHERE order_id=?",(order_id,))
        con.execute("INSERT INTO outbox VALUES (?,'order',?,'order.paid',?,?,NULL)",('payment:'+provider_reference,order_id,json.dumps({'order_id':order_id,'payment_id':pid,'amount_kobo':amount}),timestamp))
        con.execute('COMMIT');return pid
    except BaseException:
        if con.in_transaction:con.execute('ROLLBACK')
        raise

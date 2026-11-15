"""Create deterministic synthetic business data. Only replaces this project's DB.
Run from the repository root: python portfolio-1-database-design/seed.py
"""
from __future__ import annotations
import csv, json, random, sqlite3, sys, time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import ROOT, DB, connect, write_json, write_csv, environment, utc_now
HERE=Path(__file__).resolve().parent
SEED=8103
CATEGORIES={
'Groceries': [('Parboiled rice','5 kg',1200000),('Brown beans','2 kg',650000),('Semolina','2 kg',550000),('Palm oil','1 L',400000),('Pasta','500 g',160000),('Rolled oats','500 g',260000),('White garri','2 kg',280000),('Granulated sugar','1 kg',320000),('Tomato paste','400 g',180000),('Wheat flour','2 kg',450000)],
'Household': [('Laundry detergent','1 kg',350000),('Dishwashing liquid','750 mL',220000),('Floor cleaner','1 L',300000),('Tissue rolls','6 pack',420000),('Bin liners','20 pack',180000),('Kitchen towels','2 pack',250000),('Storage containers','3 pack',680000),('Scrub sponges','5 pack',150000),('Clothes pegs','24 pack',120000),('Handwash refill','1 L',320000)],
'Personal care': [('Bath soap','4 pack',200000),('Body lotion','400 mL',480000),('Toothpaste','150 g',250000),('Toothbrush','2 pack',160000),('Shampoo','400 mL',450000),('Hair conditioner','400 mL',470000),('Petroleum jelly','250 g',230000),('Deodorant','150 mL',350000),('Cotton pads','100 pack',180000),('Facial cleanser','200 mL',620000)],
'Electronics': [('USB-C charger','20 W',850000),('Power bank','10000 mAh',1850000),('USB-C cable','1 m',320000),('LED lamp','9 W',220000),('Extension socket','4 outlet',750000),('Wireless mouse','2.4 GHz',680000),('Wired keyboard','USB',900000),('Earphones','3.5 mm',550000),('Flash drive','32 GB',620000),('Rechargeable torch','1200 mAh',800000)],
'Stationery': [('Exercise books','10 pack',400000),('Ballpoint pens','12 pack',220000),('A4 paper','500 sheets',750000),('Pencils','12 pack',180000),('Stapler','standard',320000),('Sticky notes','5 pack',250000),('Document folders','10 pack',300000),('Highlighters','4 pack',260000),('Desk notebook','A5',350000),('Envelopes','50 pack',200000)],
'Beverages': [('Black tea','25 bags',230000),('Instant coffee','100 g',550000),('Cocoa drink','500 g',650000),('Orange juice','1 L',280000),('Apple juice','1 L',300000),('Bottled water','12 pack',360000),('Malt drink','6 pack',550000),('Soy drink','1 L',320000),('Ginger tea','20 bags',300000),('Powdered milk','400 g',600000)]}
BRANDS=['Lagoon Select','Harbour','Palmstone','Westgate','Creek']

def main():
    start=time.perf_counter(); rng=random.Random(SEED)
    DB.parent.mkdir(exist_ok=True)
    # The path is fixed inside the project. No arbitrary database is accepted.
    for suffix in ('','-wal','-shm'):
        p=Path(str(DB)+suffix)
        if p.exists(): p.unlink()
    c=connect(); c.executescript((HERE/'schema.sql').read_text())
    c.execute('BEGIN IMMEDIATE')
    c.executemany('INSERT INTO categories VALUES (?,?)',enumerate(CATEGORIES,1))
    c.executemany('INSERT INTO warehouses VALUES (?,?,?,?)',[(1,'IKEJA','Ikeja fulfilment centre','Ikeja'),(2,'LEKKI','Lekki fulfilment centre','Lekki')])
    products=[]; catalogue=[]
    for cid,(cat,items) in enumerate(CATEGORIES.items(),1):
        for base,size,price in items:
            for brand in BRANDS:
                for pack in (1,2):
                    pid=len(products)+1; sku=f'LM-{cid:02d}-{pid:04d}'
                    name=f'{brand} {base} ({size}; {pack} unit pack)'
                    amount=int(price*pack*(0.95+0.025*BRANDS.index(brand)))
                    products.append((pid,sku,name,cid,amount,1))
                    attrs={'brand':brand,'pack_units':pack,'unit_size':size}
                    if cat=='Electronics': attrs.update(warranty_months=12,power_source='model dependent')
                    elif cat in ('Groceries','Beverages'): attrs.update(storage='cool dry place',allergen_note='see packaging')
                    elif cat=='Stationery': attrs.update(usage='office and school',recyclable_packaging=True)
                    else: attrs.update(handling='follow product label',sealed_pack=True)
                    catalogue.append({'product_id':pid,'sku':sku,'name':name,'category_id':cid,'category':cat,'price_kobo':amount,'active':True,'attributes':attrs,'schema_version':1})
    c.executemany('INSERT INTO products VALUES (?,?,?,?,?,?)',products)
    first=['Amina','Tola','Chinedu','Fatima','Kemi','Emeka','Bola','Ibrahim','Ada','Seyi','Zainab','Uche','Damilola','Musa','Ngozi','Yusuf']
    last=['Bello','Adeyemi','Okafor','Musa','Balogun','Obi','Adebayo','Ibrahim','Eze','Ogunleye','Lawal','Nwosu','Ojo','Yusuf','Okeke','Sule']
    cities=['Ikeja','Yaba','Surulere','Lekki','Ajah']
    customers=[]; addresses=[]; customer_city={}
    for cid in range(1,5001):
        customers.append((cid,rng.choice(first),rng.choice(last),f'customer{cid:05d}@example.invalid'))
        city=rng.choice(cities); customer_city[cid]=city
        addresses.append((cid,1,f'{1+(cid%80)} Sample Crescent',city,'Lagos','NG'))
    addresses.extend((cid,2,'10 Alternative Sample Road','Yaba','Lagos','NG') for cid in range(100,5001,100))
    c.executemany('INSERT INTO customers VALUES (?,?,?,?)',customers)
    c.executemany('INSERT INTO customer_addresses VALUES (?,?,?,?,?,?)',addresses)
    begin=datetime(2026,1,1,tzinfo=timezone.utc); end=datetime(2026,11,13,23,59,tzinfo=timezone.utc)
    snapshot=datetime(2026,11,15,tzinfo=timezone.utc)
    seconds=int((end-begin).total_seconds()); fmt=lambda d:d.strftime('%Y-%m-%dT%H:%M:%SZ')
    orders=[]; lines=[]; payments=[]; shipments=[]; held=Counter()
    statuses=Counter(); payment_id=0
    for oid in range(1,120001):
        cid=rng.randint(1,5000); wid=2 if customer_city[cid] in ('Lekki','Ajah') else 1
        created=begin+timedelta(seconds=int(seconds*oid/120000))
        age=(snapshot-created).total_seconds()/86400
        if age>14: status=rng.choices(['DELIVERED','CANCELLED'],[94,6])[0]
        elif age>3: status=rng.choices(['DELIVERED','DISPATCHED','PAID','CANCELLED'],[55,30,10,5])[0]
        else: status=rng.choices(['PENDING','RESERVED','PAID','DISPATCHED','DELIVERED','CANCELLED'],[25,10,20,30,10,5])[0]
        fee=150000 if wid==1 else 200000
        orders.append((oid,cid,1,wid,status,fmt(created),fee)); statuses[status]+=1
        total=fee
        for ln,pid in enumerate(rng.sample(range(1,601),rng.choices([1,2,3,4,5],[10,25,35,20,10])[0]),1):
            qty=rng.choices([1,2,3,4],[65,25,7,3])[0]
            unit=(int(products[pid-1][4]*rng.choice([0.90,0.95,1.0]))//100)*100
            lines.append((oid,ln,pid,qty,unit)); total+=qty*unit
            if status in ('RESERVED','PAID'): held[(wid,pid)]+=qty
        if status in ('PAID','DISPATCHED','DELIVERED'):
            if rng.random()<0.08:
                payment_id+=1; payments.append((payment_id,oid,f'LM-PAY-{payment_id:08d}',total,'FAILED',fmt(created+timedelta(minutes=1))))
            payment_id+=1; payments.append((payment_id,oid,f'LM-PAY-{payment_id:08d}',total,'SUCCEEDED',fmt(created+timedelta(minutes=3))))
        elif status=='CANCELLED' or (status=='PENDING' and rng.random()<0.3):
            payment_id+=1; payments.append((payment_id,oid,f'LM-PAY-{payment_id:08d}',total,'FAILED',fmt(created+timedelta(minutes=2))))
        if status in ('DISPATCHED','DELIVERED'):
            shipped=created+timedelta(hours=3)
            delivered=min(shipped+timedelta(hours=rng.randint(6,48)),snapshot-timedelta(minutes=1)) if status=='DELIVERED' else None
            shipments.append((len(shipments)+1,oid,f'LM-TRK-{oid:08d}','Lagoon Logistics',fmt(shipped),fmt(delivered) if delivered else None))
    c.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?)',orders)
    c.executemany('INSERT INTO order_items VALUES (?,?,?,?,?)',lines)
    c.executemany('INSERT INTO payment_attempts VALUES (?,?,?,?,?,?)',payments)
    c.executemany('INSERT INTO shipments VALUES (?,?,?,?,?,?)',shipments)
    c.executemany('INSERT INTO inventory VALUES (?,?,?,?)',[(wid,pid,held[(wid,pid)]+rng.randint(50,400),held[(wid,pid)]) for wid in (1,2) for pid in range(1,601)])
    c.execute('COMMIT'); c.execute('ANALYZE'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    tables=[r[0] for r in c.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    counts={t:c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables}
    samples=HERE/'sample-data'; samples.mkdir(exist_ok=True)
    for table in tables:
        cursor=c.execute('SELECT * FROM '+table+' LIMIT 15')
        write_csv(samples/(table+'.csv'),[x[0] for x in cursor.description],cursor.fetchall())
    (ROOT/'data'/'catalogue_seed.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in catalogue))
    dictionary=[]
    for table in tables:
        for row in c.execute('PRAGMA table_info('+table+')'):
            dictionary.append((table,row[1],row[2],row[3],row[4],row[5]))
    write_csv(HERE/'data_dictionary.csv',['table','column','sqlite_type','not_null','default','primary_key_position'],dictionary)
    result={'executed_at_utc':utc_now(),'seed':SEED,'synthetic':True,'time_window':['2026-01-01','2026-11-13'],'currency':'NGN; integer kobo','counts':counts,'order_status_counts':dict(statuses),'build_seconds':round(time.perf_counter()-start,3),'integrity_check':c.execute('PRAGMA integrity_check').fetchone()[0],'foreign_key_errors':c.execute('PRAGMA foreign_key_check').fetchall()}
    write_json(HERE/'results'/'seed_manifest.json',result); write_json(ROOT/'evidence'/'environment.json',environment())
    print(json.dumps(result,indent=2)); c.close()
if __name__=='__main__': main()

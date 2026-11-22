"""Run real key-value CRUD, indexed access, schema variation, repair and TTL tests."""
import copy,dbm,dbm.ndbm,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import ROOT,RUNTIME,connect,write_json,digest,utc_now
from kv_store import CatalogueStore,encode,decode
HERE=Path(__file__).resolve().parent

def main():
 docs=[json.loads(x) for x in (ROOT/'data'/'catalogue_seed.jsonl').read_text().splitlines()]
 store=CatalogueStore(RUNTIME/'catalogue');tests=[]
 def ok(name,**facts):
    tests.append({'test':name,'passed':True,**facts});print(json.dumps(tests[-1]))
 loaded=store.load(docs)
 assert loaded==600 and dbm.whichdb(str(store.path))=='dbm.ndbm'
 ok('N01 Persist 600 JSON product documents in an independent key-value engine',backend=dbm.ndbm.library,interface=dbm.whichdb(str(store.path)),loaded=loaded)
 with connect() as c:
    sql={r[0]:r for r in c.execute('SELECT product_id,sku,product_name,category_id,unit_price_kobo FROM products')}
 for d in store.products():assert tuple(d[k] for k in ('product_id','sku','name','category_id','price_kobo'))==sql[d['product_id']]
 ok('N02 Cross-model consistency',matching_products=len(sql))
 original=store.get_product('LM-01-0001');assert original['product_id']==1
 ok('N03 Primary-key lookup',key='product:LM-01-0001',value=original)
 result=store.category_query(1,max_price_kobo=600000)
 with connect() as c:expected={r[0] for r in c.execute('SELECT sku FROM products WHERE category_id=1 AND unit_price_kobo<=600000')}
 assert {x['sku'] for x in result}==expected
 write_json(HERE/'results'/'groceries_under_6000_ngn.json',result)
 ok('N04 Category index plus price filter',category_id=1,max_price_kobo=600000,result_count=len(result),sql_result_equal=True)
 nested=store.category_query(4,max_price_kobo=1000000,attribute=('warranty_months',12))
 assert nested and all(x['attributes']['warranty_months']>=12 and x['price_kobo']<=1000000 for x in nested)
 write_json(HERE/'results'/'electronics_warranty_query.json',nested)
 ok('N05 Nested flexible-attribute query',result_count=len(nested),warranty_min_months=12,max_price_kobo=1000000)
 modified=copy.deepcopy(original);modified['attributes']['origin_region']='South West';modified['attributes']['recyclable_packaging']=True
 store.upsert_product(modified);assert store.get_product(original['sku'])['attributes']['origin_region']=='South West'
 ok('N06 Update a document without relational DDL',added_attributes=['origin_region','recyclable_packaging'])
 store.upsert_product(original)
 assert store.delete_product(original['sku']) and store.get_product(original['sku']) is None
 deleted_count=len(store.category_query(1));assert deleted_count==99
 store.upsert_product(original);assert len(store.category_query(1))==100
 ok('N07 Delete and restore with maintained category index',count_after_delete=99,count_after_restore=100)
 moved=copy.deepcopy(original);moved['category_id']=2;moved['category']='Household'
 store.upsert_product(moved)
 assert len(store.category_query(1))==99 and len(store.category_query(2))==101
 store.upsert_product(original);assert store.check_indexes()
 ok('N08 Category change updates secondary keys',during_move_counts={'category_1':99,'category_2':101},restored_indexes_valid=True)
 # Draft key is intentionally not a published SQL product.
 store.set_json('draft:new-product',{'name':'Lagoon reusable delivery bag','price_kobo':250000,'attributes':{'material':'woven fibre'}})
 assert store.get_json('draft:new-product')['attributes']['material']=='woven fibre'
 assert store.delete_json('draft:new-product') and store.get_json('draft:new-product') is None
 ok('N09 Generic key-value insertion/read/deletion',draft_published=False)
 with connect() as c:
    deliveries=c.execute('SELECT order_id,tracking_reference,shipped_at,delivered_at FROM shipments ORDER BY shipment_id DESC LIMIT 20').fetchall()
 for oid,tracking,shipped,delivered in deliveries:
    events=[{'status':'DISPATCHED','at':shipped}]
    if delivered:events.append({'status':'DELIVERED','at':delivered})
    store.set_json(f'delivery:{oid}',{'order_id':oid,'tracking_reference':tracking,'events':events[-50:]})
 example=store.get_json(f'delivery:{deliveries[0][0]}');assert example['order_id']==deliveries[0][0]
 write_json(HERE/'results'/'delivery_example.json',example)
 ok('N10 Embedded bounded delivery history',documents=20,example_order_id=example['order_id'])
 store.set_cart(1,[{'sku':original['sku'],'quantity':2}],ttl_seconds=1)
 assert store.get_cart(1) is not None;start=time.perf_counter();time.sleep(1.05)
 assert store.get_cart(1) is None
 ok('N11 Application-managed TTL',ttl_seconds=1,elapsed_seconds=time.perf_counter()-start,expired_cart_deleted=True,native_engine_ttl=False)
 external=json.loads(subprocess.check_output([sys.executable,str(HERE/'kv_cli.py'),'--get',original['sku']],text=True))
 assert external==original
 ok('N12 Persistence across independent processes',read_back_sku=external['sku'])
 invalid=copy.deepcopy(original);invalid['price_kobo']=-1
 try:store.upsert_product(invalid)
 except ValueError as e:reason=str(e)
 else:raise AssertionError('invalid document accepted')
 ok('N13 Application document validation',rejected=reason)
 # Explicit index-damage injection demonstrates a repair strategy; no crash is fabricated.
 with store.handle(write=True) as d:del d[b'category:1']
 damaged=not store.check_indexes();assert damaged
 store.rebuild_indexes();assert store.check_indexes()
 ok('N14 Repair application-maintained index after injected deletion',damage_detected=damaged,indexes_valid_after_rebuild=True)
 exported=store.products();write_json(HERE/'results'/'catalogue_export.json',exported)
 rebuilt=CatalogueStore(RUNTIME/'catalogue_roundtrip');rebuilt.load(exported)
 assert digest(rebuilt.products())==digest(exported)
 ok('N15 Portable JSON export/import',documents=len(exported),sha256=digest(exported))
 assert digest(exported)==digest(sorted(docs,key=lambda x:x['sku']))
 out={'executed_at_utc':utc_now(),'backend':dbm.ndbm.library,'tests':tests,'passed_count':len(tests),'all_passed':True,'final_product_count':len(exported),'final_indexes_valid':store.check_indexes(),'final_catalogue_matches_seed':True,'native_multikey_transactions_claimed':False}
 write_json(HERE/'results'/'nosql_tests.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()

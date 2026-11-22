"""CLI for querying the actual key-value engine."""
import argparse,json
from pathlib import Path
from kv_store import CatalogueStore
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--store',default=str(ROOT/'.runtime'/'catalogue'))
g=p.add_mutually_exclusive_group(required=True);g.add_argument('--get');g.add_argument('--category',type=int);g.add_argument('--load',action='store_true');g.add_argument('--export',action='store_true')
p.add_argument('--max-price-kobo',type=int);args=p.parse_args();store=CatalogueStore(args.store)
if args.load:
 docs=[json.loads(x) for x in (ROOT/'data'/'catalogue_seed.jsonl').read_text().splitlines()]
 result={'loaded':store.load(docs)}
elif args.get:result=store.get_product(args.get)
elif args.category:result=store.category_query(args.category,args.max_price_kobo)
else:result=store.products()
print(json.dumps(result,indent=2,ensure_ascii=False))

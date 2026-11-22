"""Independent persistent key-value catalogue using NDBM, not SQLite or a dict mock.
The actual NDBM backend is recorded at runtime. Explicit POSIX advisory locks guard
cooperating processes. The NDBM interface does NOT expose multi-key transactions;
secondary indexes are repairable projections, not a claimed crash-atomic facility.
"""
from __future__ import annotations
import dbm.ndbm, fcntl, json, time
from contextlib import contextmanager
from pathlib import Path

def encode(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def decode(value): return json.loads(value.decode('utf-8'))

class CatalogueStore:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lockfile=Path(str(self.path)+'.lock')
    @contextmanager
    def handle(self,write=False,reset=False):
        with self.lockfile.open('a+b') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX if write else fcntl.LOCK_SH)
            try:
                with dbm.ndbm.open(str(self.path),'n' if reset else ('c' if write else 'r')) as db:
                    yield db
            finally: fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
    @staticmethod
    def validate(doc):
        for k in ('product_id','sku','name','category_id','category','price_kobo','attributes','schema_version'):
            if k not in doc:raise ValueError('missing field: '+k)
        if type(doc['price_kobo']) is not int or doc['price_kobo']<=0:raise ValueError('price_kobo must be a positive integer')
        if not isinstance(doc['attributes'],dict):raise ValueError('attributes must be an object')
        if not isinstance(doc['sku'],str) or not doc['sku']:raise ValueError('invalid SKU')
    @staticmethod
    def _reindex(db):
        for key in list(db.keys()):
            if key.startswith(b'category:'):del db[key]
        categories={}
        for key in db.keys():
            if key.startswith(b'product:'):
                doc=decode(db[key]);categories.setdefault(doc['category_id'],[]).append(doc['sku'])
        for cid,skus in categories.items():db[f'category:{cid}'.encode()]=encode(sorted(skus))
    def load(self,documents):
        documents=list(documents)
        for d in documents:self.validate(d)
        with self.handle(write=True,reset=True) as db:
            for d in documents:db[('product:'+d['sku']).encode()]=encode(d)
            self._reindex(db)
            db[b'meta:schema']=encode({'version':1,'model':'key-value JSON documents','backend':dbm.ndbm.library})
        return len(documents)
    def get_product(self,sku):
        with self.handle() as db:
            raw=db.get(('product:'+sku).encode());return decode(raw) if raw is not None else None
    def upsert_product(self,doc):
        self.validate(doc)
        with self.handle(write=True) as db:
            db[('product:'+doc['sku']).encode()]=encode(doc)
            self._reindex(db)
    def delete_product(self,sku):
        with self.handle(write=True) as db:
            key=('product:'+sku).encode()
            if key not in db:return False
            del db[key];self._reindex(db);return True
    def products(self):
        with self.handle() as db:
            return sorted((decode(db[k]) for k in db.keys() if k.startswith(b'product:')),key=lambda x:x['sku'])
    def category_query(self,category_id,max_price_kobo=None,attribute=None):
        with self.handle() as db:
            key=f'category:{category_id}'.encode()
            if key not in db:raise KeyError('category index missing; rebuild it')
            documents=[decode(db[('product:'+sku).encode()]) for sku in decode(db[key])]
            if max_price_kobo is not None:documents=[d for d in documents if d['price_kobo']<=max_price_kobo]
            if attribute:
                field,minimum=attribute;documents=[d for d in documents if d['attributes'].get(field,0)>=minimum]
            return sorted(documents,key=lambda d:(d['price_kobo'],d['sku']))
    def rebuild_indexes(self):
        with self.handle(write=True) as db:self._reindex(db)
    def check_indexes(self):
        with self.handle() as db:
            expected={}
            for k in db.keys():
                if k.startswith(b'product:'):
                    d=decode(db[k]);expected.setdefault(d['category_id'],[]).append(d['sku'])
            actual={int(k.decode().split(':')[1]):decode(db[k]) for k in db.keys() if k.startswith(b'category:')}
            return {k:sorted(v) for k,v in expected.items()}==actual
    def set_json(self,key,value):
        if key.startswith(('product:','category:')):raise ValueError('use product methods for maintained indexes')
        with self.handle(write=True) as db:db[key.encode()]=encode(value)
    def get_json(self,key):
        with self.handle() as db:
            raw=db.get(key.encode());return decode(raw) if raw is not None else None
    def delete_json(self,key):
        if key.startswith(('product:','category:')):raise ValueError('use product methods for maintained indexes')
        with self.handle(write=True) as db:
            if key.encode() in db:del db[key.encode()];return True
            return False
    def set_cart(self,customer_id,items,ttl_seconds):
        if ttl_seconds<=0:raise ValueError('positive TTL required')
        self.set_json(f'cart:{customer_id}',{'customer_id':customer_id,'items':items,'expires_at_unix':time.time()+ttl_seconds})
    def get_cart(self,customer_id):
        key=f'cart:{customer_id}'
        # Check and lazy deletion under one exclusive lock, not a racy read-then-delete.
        with self.handle(write=True) as db:
            raw=db.get(key.encode())
            if raw is None:return None
            doc=decode(raw)
            if doc['expires_at_unix']<=time.time():del db[key.encode()];return None
            return doc

"""HTTP client and explicit shard router. No hidden cross-shard transaction."""
import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

def request(method,url,body=None,timeout=1.5):
 raw=json.dumps(body).encode() if body is not None else None
 req=Request(url,data=raw,method=method,headers={'Content-Type':'application/json'})
 try:
  with urlopen(req,timeout=timeout) as response:return response.status,json.load(response)
 except HTTPError as e:return e.code,json.loads(e.read())
 except (URLError,TimeoutError,ConnectionError,OSError) as e:raise ConnectionError(str(e)) from e

def expect(method,url,body=None):
 status,result=request(method,url,body)
 if status!=200:raise RuntimeError(f'{method} {url} -> {status}: {result}')
 return result

class Router:
 def __init__(self,primaries,replicas,epochs=None):
  self.primaries=dict(primaries);self.replicas=dict(replicas);self.epochs=epochs or {0:1,1:1}
 def read(self,order_id,min_seq=0):
  shard=order_id%2;failures=[]
  for base in (self.primaries[shard],self.replicas[shard]):
   try:
    code,data=request('GET',f'{base}/orders/{order_id}?min_seq={min_seq}')
    if code==200:return data
    if code not in (503,):raise RuntimeError(f'read rejected: {code}: {data}')
    failures.append(data)
   except ConnectionError as e:failures.append(str(e))
  raise ConnectionError('no node can satisfy read: '+str(failures))
 def write(self,body):
  shard=body['order_id']%2
  payload={**body,'expected_epoch':self.epochs[shard]}
  return expect('POST',self.primaries[shard]+'/apply',payload)

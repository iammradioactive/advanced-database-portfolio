"""Load a running initial-role lab cluster. Optional Docker workflow, not run here.
Idempotent for the same source snapshot; fails rather than silently changing events.
"""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import connect
from client import Router,expect

def main():
 primaries={0:'http://127.0.0.1:8810',1:'http://127.0.0.1:8820'}
 replicas={0:'http://127.0.0.1:8811',1:'http://127.0.0.1:8821'}
 router=Router(primaries,replicas)
 with connect() as c:
  rows=c.execute("SELECT o.order_id,s.tracking_reference,o.warehouse_id,s.shipped_at FROM orders o JOIN shipments s USING(order_id) WHERE o.status='DISPATCHED' ORDER BY o.order_id DESC LIMIT 120").fetchall()
 if len(rows)!=120:raise RuntimeError('Expected the seeded relational dataset first')
 for oid,tracking,warehouse,shipped in sorted(rows):
  router.write({'event_id':f'source-{oid}-v1','order_id':oid,'tracking_reference':tracking,'warehouse_id':warehouse,'status':'DISPATCHED','expected_version':0,'updated_at':shipped})
 end=time.monotonic()+30
 while time.monotonic()<end:
  pairs=[(expect('GET',primaries[s]+'/status'),expect('GET',replicas[s]+'/status')) for s in (0,1)]
  if all(a['last_applied']==b['last_applied'] and a['projection_sha256']==b['projection_sha256'] for a,b in pairs):
   print(json.dumps({'loaded':len(rows),'converged':True,'status':pairs},indent=2));return
  time.sleep(.2)
 raise TimeoutError('Replicas did not converge within the load-check window')
if __name__=='__main__':main()

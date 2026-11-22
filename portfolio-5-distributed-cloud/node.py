"""Educational HTTP database node: separate SQLite file, transactional event log.
Replication and sharding here are application-level. This is NOT native SQLite
replication, a consensus implementation, or a production-secure cluster.
"""
from __future__ import annotations
import argparse,fcntl,hashlib,json,os,sqlite3,sys
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
HERE=Path(__file__).resolve().parent

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def sha(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
class APIError(Exception):
 def __init__(self,status,message):self.status=status;self.message=message

def db_connect(path):
 c=sqlite3.connect(str(path),timeout=3,isolation_level=None);c.row_factory=sqlite3.Row
 c.execute('PRAGMA busy_timeout=3000');c.execute('PRAGMA synchronous=FULL');return c

def meta(c):return dict(c.execute('SELECT * FROM node_meta WHERE singleton=1').fetchone())
def projection(c,order_id):
 row=c.execute('SELECT * FROM delivery_projection WHERE order_id=?',(order_id,)).fetchone()
 return dict(row) if row else None

def save_event(c,event):
 # Caller owns a transaction. Projection, event and watermark advance together.
 c.execute('INSERT INTO delivery_projection VALUES (?,?,?,?,?,?,?) ON CONFLICT(order_id) DO UPDATE SET tracking_reference=excluded.tracking_reference,warehouse_id=excluded.warehouse_id,status=excluded.status,version=excluded.version,updated_at=excluded.updated_at,seq=excluded.seq',
  tuple(event[k] for k in ('order_id','tracking_reference','warehouse_id','status','version','updated_at','seq')))
 c.execute('INSERT INTO event_log VALUES (?,?,?,?,?)',(event['seq'],event['event_id'],event['order_id'],event['epoch'],canonical(event)))
 c.execute('UPDATE node_meta SET last_applied=?,epoch=max(epoch,?) WHERE singleton=1',(event['seq'],event['epoch']))

def apply_primary(c,body):
 required=('event_id','order_id','tracking_reference','warehouse_id','status','expected_version','expected_epoch','updated_at')
 if any(k not in body for k in required):raise APIError(400,'missing required field')
 if type(body['order_id']) is not int or body['order_id']<=0:raise APIError(400,'invalid order_id')
 if type(body['expected_version']) is not int or body['expected_version']<0:raise APIError(400,'invalid expected_version')
 if body['status'] not in ('DISPATCHED','OUT_FOR_DELIVERY','DELIVERED'):raise APIError(400,'invalid status')
 if body['warehouse_id'] not in (1,2):raise APIError(400,'invalid warehouse')
 if not isinstance(body['event_id'],str) or not body['event_id']:raise APIError(400,'invalid event_id')
 req={k:body[k] for k in required if k!='expected_epoch'};request_hash=sha(req)
 c.execute('BEGIN IMMEDIATE')
 try:
  m=meta(c)
  if m['role']!='primary':raise APIError(403,'replica is read-only for application writes')
  if body['order_id']%2!=m['shard_id']:raise APIError(409,'wrong shard for order_id')
  prior=c.execute('SELECT event_json FROM event_log WHERE event_id=?',(body['event_id'],)).fetchone()
  if prior:
   event=json.loads(prior[0])
   if event['request_hash']!=request_hash:raise APIError(409,'event_id reused with different content')
   c.execute('COMMIT');return {'duplicate':True,'event':event}
  if body['expected_epoch']!=m['epoch']:raise APIError(409,'stale leader epoch')
  old=projection(c,body['order_id']);version=old['version'] if old else 0
  if body['expected_version']!=version:raise APIError(409,'version conflict')
  if old:
   allowed={'DISPATCHED':{'OUT_FOR_DELIVERY','DELIVERED'},'OUT_FOR_DELIVERY':{'DELIVERED'},'DELIVERED':set()}
   if body['status'] not in allowed[old['status']]:raise APIError(409,'invalid delivery-state transition')
   if old['tracking_reference']!=body['tracking_reference'] or old['warehouse_id']!=body['warehouse_id']:
    raise APIError(409,'immutable delivery identity changed')
  event={'seq':m['last_applied']+1,'event_id':body['event_id'],'order_id':body['order_id'],
   'tracking_reference':body['tracking_reference'],'warehouse_id':body['warehouse_id'],
   'status':body['status'],'version':version+1,'updated_at':body['updated_at'],
   'epoch':m['epoch'],'shard_id':m['shard_id'],'request_hash':request_hash}
  save_event(c,event);c.execute('COMMIT');return {'duplicate':False,'event':event}
 except BaseException:
  if c.in_transaction:c.execute('ROLLBACK')
  raise

def replicate(c,body):
 events=body.get('events')
 if not isinstance(events,list) or len(events)>1000:raise APIError(400,'events must be a batch of at most 1000')
 c.execute('BEGIN IMMEDIATE');applied=0;duplicates=0
 try:
  m=meta(c)
  if m['role']!='replica':raise APIError(403,'replication target is not a replica')
  for event in events:
   if event['shard_id']!=m['shard_id'] or event['order_id']%2!=m['shard_id']:raise APIError(409,'wrong-shard event')
   if event['seq']<=m['last_applied']:
    old=c.execute('SELECT event_json FROM event_log WHERE seq=?',(event['seq'],)).fetchone()
    if not old or old[0]!=canonical(event):raise APIError(409,'divergent replay')
    duplicates+=1;continue
   if event['seq']!=m['last_applied']+1:raise APIError(409,'replication sequence gap')
   if event['epoch']<m['epoch']:raise APIError(409,'stale source epoch')
   old=projection(c,event['order_id']);version=old['version'] if old else 0
   if event['version']!=version+1:raise APIError(409,'projection version gap')
   save_event(c,event);m['last_applied']=event['seq'];m['epoch']=max(m['epoch'],event['epoch']);applied+=1
  c.execute('COMMIT');return {'applied':applied,'duplicates':duplicates,'last_applied':m['last_applied'],'epoch':m['epoch']}
 except BaseException:
  if c.in_transaction:c.execute('ROLLBACK')
  raise

class Handler(BaseHTTPRequestHandler):
 server_version='LagoonLab/1.0'
 def log_message(self,fmt,*args):
  print(json.dumps({'at_utc':datetime.now(timezone.utc).isoformat(),'node':self.server.node_id,'request':fmt%args}),flush=True)
 def respond(self,status,data):
  raw=(canonical(data)+'\n').encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  c=db_connect(self.server.db_path)
  try:
   parsed=urlparse(self.path);query=parse_qs(parsed.query);m=meta(c)
   if parsed.path=='/status':
    rows=[dict(r) for r in c.execute('SELECT * FROM delivery_projection ORDER BY order_id')]
    self.respond(200,{**m,'pid':os.getpid(),'orders_count':len(rows),'event_count':c.execute('SELECT count(*) FROM event_log').fetchone()[0],'projection_sha256':sha(rows)})
   elif parsed.path=='/events':
    after=int(query.get('after',['0'])[0]);limit=min(1000,max(1,int(query.get('limit',['1000'])[0])))
    rows=c.execute('SELECT event_json FROM event_log WHERE seq>? ORDER BY seq LIMIT ?',(after,limit)).fetchall()
    self.respond(200,{'events':[json.loads(r[0]) for r in rows],'source_last_applied':m['last_applied']})
   elif parsed.path.startswith('/orders/'):
    oid=int(parsed.path.rsplit('/',1)[1]);minimum=int(query.get('min_seq',['0'])[0])
    if oid%2!=m['shard_id']:raise APIError(409,'wrong shard for order_id')
    if m['last_applied']<minimum:raise APIError(503,'node behind requested session watermark')
    row=projection(c,oid)
    if row is None:raise APIError(404,'order not found')
    self.respond(200,{'served_by':m['node_id'],'role':m['role'],'epoch':m['epoch'],'last_applied':m['last_applied'],'order':row})
   else:raise APIError(404,'unknown endpoint')
  except APIError as e:self.respond(e.status,{'error':e.message})
  except (ValueError,KeyError,TypeError) as e:self.respond(400,{'error':str(e)})
  finally:c.close()
 def do_POST(self):
  c=db_connect(self.server.db_path)
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n<=0 or n>2_000_000:raise APIError(400,'invalid body size')
   body=json.loads(self.rfile.read(n))
   if self.path=='/apply':self.respond(200,apply_primary(c,body))
   elif self.path=='/replicate':self.respond(200,replicate(c,body))
   elif self.path=='/promote':
    # Operator assertion is not a consensus/fencing service. The test driver actually
    # terminates and waits for the old primary before it supplies this assertion.
    if body.get('old_primary_process_confirmed_stopped') is not True:raise APIError(412,'old primary must be fenced first')
    c.execute('BEGIN IMMEDIATE');m=meta(c)
    if m['role']!='replica':raise APIError(409,'only a replica can be promoted')
    if m['last_applied']<int(body.get('required_seq',0)):raise APIError(409,'replica missing required events')
    c.execute("UPDATE node_meta SET role='primary',epoch=epoch+1 WHERE singleton=1");c.execute('COMMIT')
    self.respond(200,meta(c))
   else:raise APIError(404,'unknown endpoint')
  except APIError as e:
   if c.in_transaction:c.execute('ROLLBACK')
   self.respond(e.status,{'error':e.message})
  except (ValueError,KeyError,TypeError,sqlite3.Error) as e:
   if c.in_transaction:c.execute('ROLLBACK')
   self.respond(400,{'error':str(e)})
  finally:c.close()

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--node-id',required=True);p.add_argument('--shard',type=int,choices=(0,1),required=True);p.add_argument('--role',choices=('primary','replica'),required=True);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,required=True)
 p.add_argument('--rejoin-as-replica',action='store_true');p.add_argument('--source-epoch',type=int)
 a=p.parse_args();path=Path(a.db);path.parent.mkdir(parents=True,exist_ok=True)
 # Lifetime file lock prevents two processes opening one node identity concurrently.
 lock=open(str(path)+'.process.lock','a+b');fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 c=db_connect(path);c.executescript((HERE/'node_schema.sql').read_text())
 if c.execute('SELECT count(*) FROM node_meta').fetchone()[0]==0:
  c.execute('INSERT INTO node_meta VALUES (1,?,?,?,?,0)',(a.node_id,a.shard,a.role,1))
 else:
  m=meta(c)
  if m['node_id']!=a.node_id or m['shard_id']!=a.shard:raise RuntimeError('database identity mismatch')
  if a.rejoin_as_replica:
   if a.source_epoch is None or a.source_epoch<=m['epoch']:raise RuntimeError('rejoin requires a newer source epoch')
   c.execute("UPDATE node_meta SET role='replica',epoch=? WHERE singleton=1",(a.source_epoch,))
 m=meta(c);c.close()
 server=ThreadingHTTPServer((a.host,a.port),Handler);server.daemon_threads=True;server.db_path=path;server.node_id=a.node_id
 print(canonical({'startup':True,'pid':os.getpid(),'host':a.host,'port':a.port,'meta':m}),flush=True)
 try:server.serve_forever(poll_interval=0.1)
 finally:server.server_close();lock.close()
if __name__=='__main__':main()

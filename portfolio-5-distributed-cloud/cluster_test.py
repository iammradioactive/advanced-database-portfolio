"""Start four real HTTP processes, exercise replication and failover, then stop them."""
from __future__ import annotations
import argparse,copy,json,shutil,socket,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import ROOT,RUNTIME,connect,write_json,utc_now
from client import Router,request,expect
HERE=Path(__file__).resolve().parent
OUT=HERE/'results';LOGS=OUT/'node-logs';LOGS.mkdir(parents=True,exist_ok=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--base-port',type=int,default=8810);args=parser.parse_args()
 specs=json.loads((HERE/'configs'/'cluster.json').read_text())['nodes']
 for spec in specs:spec['port']+=args.base_port-8810
 # Refuse to interfere with any pre-existing listener.
 for spec in specs:
  sock=socket.socket()
  try:sock.bind(('127.0.0.1',spec['port']))
  except OSError:raise RuntimeError('port occupied; choose --base-port rather than stopping another service')
  finally:sock.close()
 folder=RUNTIME/'cluster'
 if folder.exists():shutil.rmtree(folder)
 folder.mkdir(parents=True)
 for old_log in LOGS.glob('*.log'):old_log.unlink()
 processes={};workers={};handles=[];events=[];tests=[];lifecycle=[]
 urls={s['node_id']:f"http://127.0.0.1:{s['port']}" for s in specs}
 def record(name,**facts):
  tests.append({'test':name,'passed':True,**facts});print(json.dumps(tests[-1]),flush=True)
 def start_node(spec,rejoin=False):
  name=spec['node_id'];log=open(LOGS/(name+'.log'),'a');handles.append(log)
  cmd=[sys.executable,str(HERE/'node.py'),'--db',str(ROOT/spec['db']),'--node-id',name,'--shard',str(spec['shard']),'--role',spec['role'],'--port',str(spec['port'])]
  if rejoin:cmd+=['--rejoin-as-replica','--source-epoch','2']
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);processes[name]=proc
  deadline=time.monotonic()+6
  while time.monotonic()<deadline:
   if proc.poll() is not None:raise RuntimeError(name+' failed; inspect node log')
   try:
    status=expect('GET',urls[name]+'/status')
    if status['node_id']==name:
     lifecycle.append({'at_utc':utc_now(),'action':'start','node':name,'pid':proc.pid,'port':spec['port'],'role':status['role']});return status
   except Exception:time.sleep(0.03)
  raise TimeoutError('node start timeout: '+name)
 def stop_node(name):
  proc=processes[name];proc.terminate();code=proc.wait(timeout=5)
  lifecycle.append({'at_utc':utc_now(),'action':'stop','node':name,'pid':proc.pid,'exit_code':code})
  return code
 def start_worker(shard,source,target):
  log=open(LOGS/f'replicator-{shard}.log','a');handles.append(log)
  proc=subprocess.Popen([sys.executable,str(HERE/'replicator.py'),'--source',source,'--target',target,'--interval','0.05'],stdout=log,stderr=subprocess.STDOUT)
  workers[shard]=proc;return proc.pid
 def stop_worker(shard):
  proc=workers.pop(shard,None)
  if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
 def wait_synced(source,target):
  deadline=time.monotonic()+8
  while time.monotonic()<deadline:
   a=expect('GET',source+'/status');b=expect('GET',target+'/status')
   if a['last_applied']==b['last_applied'] and a['projection_sha256']==b['projection_sha256']:return a,b
   time.sleep(0.04)
  raise TimeoutError('replication failed to converge')
 try:
  initial={s['node_id']:start_node(s) for s in specs}
  assert len({s['pid'] for s in initial.values()})==4
  record('D01 Four independent database server processes',pids={k:v['pid'] for k,v in initial.items()},ports={s['node_id']:s['port'] for s in specs})
  primaries={0:urls['s0-primary'],1:urls['s1-primary']};replicas={0:urls['s0-replica'],1:urls['s1-replica']};router=Router(primaries,replicas)
  for shard in (0,1):start_worker(shard,primaries[shard],replicas[shard])
  with connect() as c:
   selected=c.execute("SELECT o.order_id,s.tracking_reference,o.warehouse_id,s.shipped_at FROM orders o JOIN shipments s USING(order_id) WHERE o.status='DISPATCHED' ORDER BY o.order_id DESC LIMIT 120").fetchall()
  for oid,tracking,warehouse,shipped in sorted(selected):
   body={'event_id':f'source-{oid}-v1','order_id':oid,'tracking_reference':tracking,'warehouse_id':warehouse,'status':'DISPATCHED','expected_version':0,'updated_at':shipped}
   event=router.write(body)['event'];events.append(event)
  pairs={shard:wait_synced(primaries[shard],replicas[shard]) for shard in (0,1)}
  counts={str(shard):pairs[shard][0]['orders_count'] for shard in (0,1)}
  assert sum(counts.values())==120 and all(x>0 for x in counts.values())
  record('D02 Real horizontal partitioning of delivery records',rule='order_id % 2',shard_counts=counts,total=120)
  record('D03 Asynchronous event-log replication',watermarks={str(k):v[0]['last_applied'] for k,v in pairs.items()},pairwise_projection_hashes_equal=True)
  example=next(e for e in events if e['shard_id']==0);oid=example['order_id']
  initial_body={'event_id':example['event_id'],'order_id':oid,'tracking_reference':example['tracking_reference'],'warehouse_id':example['warehouse_id'],'status':'DISPATCHED','expected_version':0,'updated_at':example['updated_at']}
  replay=router.write(initial_body);assert replay['duplicate'] and replay['event']['seq']==example['seq']
  record('D04 Idempotent application-event retry',event_id=example['event_id'],original_seq=example['seq'],replay_seq=replay['event']['seq'])
  code,wrong=request('POST',primaries[1]+'/apply',{**initial_body,'expected_epoch':1})
  assert code==409 and 'wrong shard' in wrong['error']
  code2,readonly=request('POST',replicas[0]+'/apply',{**initial_body,'expected_epoch':1})
  assert code2==403
  record('D05 Routing and replica write protection',wrong_shard_http=code,replica_write_http=code2)
  stop_worker(0)
  update={**initial_body,'event_id':f'carrier-{oid}-v2','status':'OUT_FOR_DELIVERY','expected_version':1,'updated_at':'2026-11-15T10:00:00Z'}
  new=router.write(update)['event'];minimum=new['seq']
  stale=expect('GET',replicas[0]+f'/orders/{oid}')
  fresh=expect('GET',primaries[0]+f'/orders/{oid}')
  lag=expect('GET',primaries[0]+'/status')['last_applied']-expect('GET',replicas[0]+'/status')['last_applied']
  assert stale['order']['version']==1 and fresh['order']['version']==2 and lag==1
  record('D06 Controlled replication pause produces stale read',order_id=oid,primary_version=2,replica_version=1,lag_events=lag,fault='replication worker paused; not an OS network partition')
  code,gate=request('GET',replicas[0]+f'/orders/{oid}?min_seq={minimum}')
  assert code==503
  record('D07 Session watermark refuses a stale response',required_seq=minimum,http_status=code,error=gate['error'])
  # Missing fencing confirmation prevents an unsafe promotion while primary is live.
  code,unfenced=request('POST',replicas[0]+'/promote',{'required_seq':minimum,'old_primary_process_confirmed_stopped':False})
  assert code==412
  record('D08 Promotion requires an explicit fencing step',http_status=code,error=unfenced['error'])
  start_worker(0,primaries[0],replicas[0]);a,b=wait_synced(primaries[0],replicas[0])
  caught=expect('GET',replicas[0]+f'/orders/{oid}?min_seq={minimum}');assert caught['order']['version']==2
  record('D09 Resume replication and regain session consistency',replica_version=2,last_applied=b['last_applied'],hashes_equal=a['projection_sha256']==b['projection_sha256'])
  code,version_conflict=request('POST',primaries[0]+'/apply',{**update,'event_id':'stale-version-request','status':'DELIVERED','expected_epoch':1})
  assert code==409 and version_conflict['error']=='version conflict'
  record('D10 Optimistic concurrency rejects stale client version',http_status=code,error=version_conflict['error'])
  replayed=expect('POST',replicas[0]+'/replicate',{'events':[new]});assert replayed['duplicates']==1 and replayed['applied']==0
  record('D11 Replication replay is idempotent',duplicates=replayed['duplicates'],new_events=replayed['applied'])
  stop_worker(0);required=expect('GET',primaries[0]+'/status')['last_applied']
  start=time.perf_counter();exit_code=stop_node('s0-primary')
  fallback=router.read(oid,min_seq=required);elapsed=(time.perf_counter()-start)*1000
  assert fallback['served_by']=='s0-replica' and fallback['order']['version']==2
  record('D12 Read availability after actual primary process termination',old_primary_exit_code=exit_code,served_by=fallback['served_by'],version=fallback['order']['version'],observed_stop_and_read_ms=elapsed)
  try:router.write({**update,'event_id':f'carrier-{oid}-v3','status':'DELIVERED','expected_version':2})
  except ConnectionError:unavailable=True
  else:raise AssertionError('write accepted without a primary')
  record('D13 Writes unavailable until controlled promotion',write_rejected=unavailable,replica_not_implicitly_promoted=True)
  promoted=expect('POST',replicas[0]+'/promote',{'required_seq':required,'old_primary_process_confirmed_stopped':True})
  assert promoted['epoch']==2 and promoted['role']=='primary'
  router.primaries[0],router.replicas[0]=replicas[0],primaries[0];router.epochs[0]=2
  final_body={**update,'event_id':f'carrier-{oid}-v3','status':'DELIVERED','expected_version':2,'updated_at':'2026-11-15T11:00:00Z'}
  stale_epoch_code,stale_epoch=request('POST',router.primaries[0]+'/apply',{**final_body,'expected_epoch':1})
  assert stale_epoch_code==409 and stale_epoch['error']=='stale leader epoch'
  delivered=router.write(final_body)['event'];assert delivered['version']==3 and delivered['epoch']==2
  record('D14 Fenced manual promotion, epoch guard and successful write',new_primary='s0-replica',epoch=2,old_epoch_http=stale_epoch_code,order_version=3,order_status='DELIVERED',last_seq=delivered['seq'])
  # The terminated old primary is restarted explicitly as a replica of epoch 2.
  old_spec=next(s for s in specs if s['node_id']=='s0-primary');start_node(old_spec,rejoin=True)
  start_worker(0,router.primaries[0],router.replicas[0]);new_primary,rejoined=wait_synced(router.primaries[0],router.replicas[0])
  assert rejoined['role']=='replica' and rejoined['epoch']==2
  record('D15 Rejoin fenced old primary and recover replication',old_node_role=rejoined['role'],epoch=rejoined['epoch'],last_applied=rejoined['last_applied'],hashes_equal=True)
  # A replica process restart must retain its committed projection and role.
  stop_worker(1);s1=expect('GET',replicas[1]+'/status');stop_node('s1-replica')
  spec=next(s for s in specs if s['node_id']=='s1-replica');restart=start_node(spec)
  assert restart['projection_sha256']==s1['projection_sha256'] and restart['last_applied']==s1['last_applied']
  start_worker(1,primaries[1],replicas[1]);wait_synced(primaries[1],replicas[1])
  record('D16 Durable state after replica restart',last_applied=restart['last_applied'],projection_hash_unchanged=True)
  final_status={name:expect('GET',url+'/status') for name,url in urls.items()}
  write_json(OUT/'final_cluster_status.json',final_status)
  write_json(OUT/'sample_source_events.json',events)
  write_json(OUT/'observed_deployment.json',{'executed_at_utc':utc_now(),'nodes':specs,'process_lifecycle':lifecycle,'physical_hosts':1,'cloud_deployed':False})
  out={'executed_at_utc':utc_now(),'tests':tests,'passed_count':len(tests),'all_passed':True,'deployment':'four local HTTP processes, two shards, one replica each; application-level event-log replication','cloud_deployed':False,'consensus_implemented':False,'real_network_partition_tested':False,'source_linked_delivery_records':120,'final_roles':{k:v['role'] for k,v in final_status.items()},'scope_limit':'one physical host; manually fenced failover; no production HA claim'}
  write_json(OUT/'distributed_tests.json',out);print(json.dumps(out,indent=2))
 finally:
  for shard in list(workers):stop_worker(shard)
  for name,p in processes.items():
   if p.poll() is None:stop_node(name)
  for f in handles:f.close()
  write_json(OUT/'process_lifecycle.json',lifecycle)
 # Verify every stopped node's database, including shard-placement invariants.
 checks={}
 for s in specs:
  with sqlite3.connect(ROOT/s['db']) as c:
   c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
   checks[s['node_id']]={'integrity_check':c.execute('PRAGMA integrity_check').fetchone()[0],
    'wrong_shard_rows':c.execute('SELECT count(*) FROM delivery_projection WHERE order_id%2<>?',(s['shard'],)).fetchone()[0]}
   assert checks[s['node_id']]=={'integrity_check':'ok','wrong_shard_rows':0}
 write_json(OUT/'node_integrity.json',checks)
if __name__=='__main__':main()

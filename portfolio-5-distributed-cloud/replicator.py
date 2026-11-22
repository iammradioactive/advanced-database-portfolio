"""Asynchronous pull worker; target commits each ordered batch atomically."""
import argparse,json,time
from client import expect

def sync_once(source,target):
 target_status=expect('GET',target+'/status')
 batch=expect('GET',source+'/events?after='+str(target_status['last_applied']))['events']
 if batch:return expect('POST',target+'/replicate',{'events':batch})
 return {'applied':0,'last_applied':target_status['last_applied']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--target',required=True);p.add_argument('--interval',type=float,default=0.1);p.add_argument('--once',action='store_true');a=p.parse_args()
 while True:
  try:
   result=sync_once(a.source,a.target)
   if result['applied'] or a.once:print(json.dumps(result),flush=True)
  except Exception as e:
   print(json.dumps({'replication_error':str(e)}),flush=True)
   if a.once:raise
  if a.once:break
  time.sleep(a.interval)
if __name__=='__main__':main()

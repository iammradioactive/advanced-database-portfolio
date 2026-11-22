"""Run genuine wall-clock benchmarks and save native query plans.
No EXPLAIN ANALYZE support is claimed: SQLite EQP is structural, timings are
Python perf_counter_ns elapsed time for execute + fetchall, with a warm cache.
"""
from __future__ import annotations
import json, statistics, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import connect,write_json,write_csv,digest,utc_now,environment
HERE=Path(__file__).resolve().parent
OUT=HERE/'results'; PLANS=OUT/'plans'; PLANS.mkdir(parents=True,exist_ok=True)
RUNS=11; WARMUPS=3

def main():
 c=connect(); raw=[]; measured={}; data_hashes={}
 for idx in ('opt_orders_customer_recent','opt_orders_created_status','opt_paid_queue'):
    c.execute('DROP INDEX IF EXISTS '+idx)
 c.execute('ANALYZE'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
 base_bytes=c.execute('PRAGMA page_count').fetchone()[0]*c.execute('PRAGMA page_size').fetchone()[0]
 def run(label,filename):
    sql=(HERE/'queries'/filename).read_text()
    for _ in range(WARMUPS): c.execute(sql).fetchall()
    times=[]; result=[]
    for i in range(RUNS):
      t=time.perf_counter_ns(); cur=c.execute(sql); result=cur.fetchall(); ms=(time.perf_counter_ns()-t)/1e6
      times.append(ms);raw.append((label,i+1,ms,len(result)))
    plan=c.execute('EXPLAIN QUERY PLAN '+sql).fetchall()
    (PLANS/(label+'.txt')).write_text('\n'.join(' | '.join(map(str,row)) for row in plan)+'\n')
    write_json(PLANS/(label+'.json'),plan)
    bytecode=c.execute('EXPLAIN '+sql)
    write_csv(PLANS/(label+'_bytecode.csv'),[x[0] for x in bytecode.description],bytecode.fetchall())
    write_csv(OUT/(label+'_result.csv'),[x[0] for x in cur.description],result)
    entry={'label':label,'file':filename,'median_ms':statistics.median(times),'min_ms':min(times),'max_ms':max(times),'stdev_ms':statistics.stdev(times),'runs':RUNS,'warmups':WARMUPS,'rows':len(result),'result_sha256':digest(result),'plan':[r[3] for r in plan]}
    measured[label]=entry;data_hashes[label]=entry['result_sha256'];return entry
 for q,f in [('q1','q1_customer_history'),('q2','q2_daily_orders'),('q3','q3_paid_queue')]:
    run(q+'_before',f+'_before.sql')
 run('q2_rewrite_only','q2_daily_orders_after.sql')
 t=time.perf_counter();c.executescript((HERE/'indexes.sql').read_text());build_ms=(time.perf_counter()-t)*1000
 c.execute('PRAGMA wal_checkpoint(TRUNCATE)')
 after_bytes=c.execute('PRAGMA page_count').fetchone()[0]*c.execute('PRAGMA page_size').fetchone()[0]
 run('q2_index_only','q2_daily_orders_before.sql')
 for q,f in [('q1','q1_customer_history'),('q2','q2_daily_orders'),('q3','q3_paid_queue')]:
    run(q+'_after',f+'_after.sql')
 comparisons=[]
 for q in ('q1','q2','q3'):
    b=measured[q+'_before'];a=measured[q+'_after']
    assert b['result_sha256']==a['result_sha256'],q+' results changed'
    comparisons.append({'query':q,'before_median_ms':b['median_ms'],'after_median_ms':a['median_ms'],'speedup':b['median_ms']/a['median_ms'],'reduction_percent':(1-a['median_ms']/b['median_ms'])*100,'rows':a['rows'],'identical_results':True})
 assert len({data_hashes[k] for k in ('q2_before','q2_rewrite_only','q2_index_only','q2_after')})==1
 business=[]
 for filename in ('q4_category_revenue.sql','q5_customer_rank.sql','q6_dispatch_exceptions.sql'):
    sql=(HERE/'queries'/filename).read_text();t=time.perf_counter();cur=c.execute(sql);rows=cur.fetchall()
    elapsed=(time.perf_counter()-t)*1000
    write_csv(OUT/(Path(filename).stem+'_result.csv'),[d[0] for d in cur.description],rows)
    plan=c.execute('EXPLAIN QUERY PLAN '+sql).fetchall()
    (PLANS/(Path(filename).stem+'.txt')).write_text('\n'.join(' | '.join(map(str,row)) for row in plan)+'\n')
    business.append({'query':filename,'rows':len(rows),'elapsed_ms':elapsed,'sha256':digest(rows)})
 index_sizes=[]
 try:
    index_sizes=c.execute("SELECT name,sum(pgsize) FROM dbstat WHERE name LIKE 'opt_%' GROUP BY name").fetchall()
 except Exception: pass
 out={'executed_at_utc':utc_now(),'method':{'clock':'perf_counter_ns','timed_work':'execute + fetchall; excludes plan capture','cache':'warm; three warm-ups per variant','measurement_runs':RUNS,'concurrent_load':'no workload intentionally generated; shared-host noise uncontrolled','limitations':'not cold-cache, not an SLA, not a server throughput test','index_build_ms':build_ms,'database_bytes_before':base_bytes,'database_bytes_after':after_bytes,'index_sizes_bytes':index_sizes},'comparisons':comparisons,'variants':measured,'additional_business_queries':business,'environment':environment()}
 write_json(OUT/'benchmark_summary.json',out)
 write_csv(OUT/'raw_timings.csv',['variant','run','elapsed_ms','result_rows'],raw)
 write_csv(OUT/'performance_comparison.csv',list(comparisons[0]),[list(x.values()) for x in comparisons])
 print(json.dumps(out,indent=2));c.close()
if __name__=='__main__':main()

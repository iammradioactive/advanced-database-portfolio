"""Execute a SQL file and print genuine result rows. Defaults to the project DB.
Use --copy for experiments that must not modify the canonical database.
"""
import argparse,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import DB,ROOT,RUNTIME,connect,backup

def main():
 p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=DB);p.add_argument('--file',type=Path,required=True);p.add_argument('--copy',action='store_true');a=p.parse_args()
 if not a.db.is_file():p.error('Database does not exist; run the seed script first')
 path=backup(a.db,RUNTIME/'sql_console.sqlite') if a.copy else a.db
 con=connect(path);pending=''
 try:
  for line in a.file.read_text().splitlines(keepends=True):
   pending+=line
   if sqlite3.complete_statement(pending):
    cur=con.execute(pending)
    if cur.description:print(json.dumps({'columns':[x[0] for x in cur.description],'rows':cur.fetchall()},indent=2))
    pending=''
  if pending.strip() and not all(x.strip().startswith('--') or not x.strip() for x in pending.splitlines()):raise ValueError('Incomplete SQL statement at end of file')
 finally:
  if con.in_transaction:con.rollback()
  con.close()
if __name__=='__main__':main()

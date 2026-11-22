"""Fail clearly if this specific laboratory environment is unsupported."""
import json,sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.common import environment

def check():
 if sys.version_info<(3,11):raise RuntimeError('Python 3.11 or later is required')
 if sqlite3.sqlite_version_info<(3,37,0):raise RuntimeError('SQLite 3.37+ is required for STRICT tables')
 try:
  import fcntl,dbm.ndbm
 except ImportError as e:raise RuntimeError('Linux/WSL Python with fcntl and dbm.ndbm is required; no mock fallback is used') from e
 with sqlite3.connect(':memory:') as c:
  if c.execute("SELECT json_valid('{}')").fetchone()[0]!=1:raise RuntimeError('SQLite JSON functions are required')
 with tempfile.TemporaryDirectory() as td:
  with dbm.ndbm.open(str(Path(td)/'probe'),'c') as d:d[b'check']=b'persistent'
  with dbm.ndbm.open(str(Path(td)/'probe'),'r') as d:assert d[b'check']==b'persistent'
 return {**environment(),'dbm_backend':dbm.ndbm.library,'runtime_dependencies':'Python standard library; real ndbm extension required'}
if __name__=='__main__':print(json.dumps(check(),indent=2))

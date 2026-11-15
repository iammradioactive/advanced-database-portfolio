"""Shared paths, safe SQLite connections and evidence serialisation."""
from __future__ import annotations
import csv, hashlib, json, os, platform, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "lagoon_market.sqlite"
RUNTIME = ROOT / ".runtime"
def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
def connect(path=DB, *, timeout=5.0, uri=False):
    con = sqlite3.connect(str(path), timeout=timeout, isolation_level=None,
                          cached_statements=0, uri=uri)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=" + str(int(timeout*1000)))
    con.execute("PRAGMA synchronous=FULL")
    return con

def write_json(path, data):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
def write_csv(path, columns, rows):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(columns); w.writerows(rows)
def digest(rows):
    return hashlib.sha256(json.dumps(rows, separators=(",",":"), sort_keys=True, default=str).encode()).hexdigest()
def backup(source=DB, destination=None):
    if destination is None: raise ValueError("destination required")
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists(): destination.unlink()
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(destination)) as dst:
        src.backup(dst)
    return destination

def environment():
    cpu="unknown"
    if Path("/proc/cpuinfo").exists():
        cpu=next((x.split(":",1)[1].strip() for x in Path("/proc/cpuinfo").read_text().splitlines() if x.startswith("model name")),cpu)
    return {"captured_at_utc":utc_now(), "python":sys.version, "sqlite":sqlite3.sqlite_version,
            "platform":platform.platform(),"cpu":cpu,"logical_cpus":os.cpu_count(),
            "timing_scope":("GitHub Actions runner" if os.environ.get("GITHUB_ACTIONS")=="true" else "local runtime") + "; no production capacity claim"}

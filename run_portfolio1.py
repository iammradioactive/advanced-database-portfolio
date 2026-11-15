"""Rebuild Portfolio 1, execute its tests, and save truthful run evidence.

Run from this project: python run_portfolio1.py --rebuild
Requires Python 3.11+ and SQLite 3.37+ with JSON functions. No pip packages.
Only project-generated files are replaced. This does not publish or submit anything.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from tools.common import ROOT, DB, environment, utc_now, write_json

P1 = ROOT / "portfolio-1-database-design"
RESULTS = P1 / "results"
ARTIFACT = ROOT / "portfolio1-run-evidence"


def preflight() -> None:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required.")
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise RuntimeError("SQLite 3.37 or newer is required for STRICT tables.")
    with sqlite3.connect(":memory:") as con:
        if con.execute("SELECT json_valid('{}')").fetchone()[0] != 1:
            raise RuntimeError("SQLite JSON functions are required.")


def run_step(script: str, log: str) -> dict:
    start = time.perf_counter()
    print(f"RUN {script}", flush=True)
    with (RESULTS / log).open("w", encoding="utf-8") as handle:
        proc = subprocess.Popen(
            [sys.executable, "-u", str(P1 / script)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
            handle.write(line)
        exit_code = proc.wait()
    return {"script": script, "log": log, "exit_code": exit_code,
            "elapsed_seconds": round(time.perf_counter() - start, 3)}


def inspection_queries() -> None:
    statements = []
    buffer = ""
    for line in (P1 / "example_queries.sql").read_text(encoding="utf-8").splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer)
            buffer = ""
    if any(line.strip() and not line.lstrip().startswith("--") for line in buffer.splitlines()):
        raise RuntimeError("An inspection query is incomplete.")
    con = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        with (RESULTS / "example_queries.txt").open("w", encoding="utf-8") as out:
            for number, sql in enumerate(statements, 1):
                if not sql.strip():
                    continue
                cursor = con.execute(sql)
                columns = [field[0] for field in cursor.description]
                rows = cursor.fetchall()
                out.write(f"QUERY {number}\n{sql.strip()};\n")
                out.write(" | ".join(columns) + "\n")
                for row in rows:
                    out.write(" | ".join(str(value) for value in row) + "\n")
                out.write(f"Rows returned: {len(rows)}\n\n")
                with (RESULTS / f"inspection_query_{number}.csv").open(
                        "w", encoding="utf-8", newline="") as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(columns)
                    writer.writerows(rows)
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true",
                        help="Allow replacement of this project's generated database and run reports")
    args = parser.parse_args()
    if not args.rebuild:
        parser.error("Add --rebuild to acknowledge replacing this project's generated data.")
    if sys.flags.optimize:
        parser.error("Run without -O: the validation suite uses assertions.")
    RESULTS.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.json", "*.txt", "*.csv", "SUMMARY.md"):
        for old in RESULTS.glob(pattern):
            old.unlink()
    if ARTIFACT.exists():
        shutil.rmtree(ARTIFACT)
    ARTIFACT.mkdir()
    github_run = os.environ.get("GITHUB_ACTIONS") == "true"
    started = utc_now()
    result = {
        "started_at_utc": started,
        "execution_context": "GitHub Actions" if github_run else "local execution",
        "environment": environment(),
        "github_repository": os.environ.get("GITHUB_REPOSITORY"),
        "github_commit": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_url": None,
        "all_passed": False,
        "steps": [],
        "source_sha256": {},
    }
    if github_run:
        result["github_run_url"] = (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
        )
    for source in [Path(__file__), ROOT / "tools/common.py", *P1.glob("*.py"), *P1.glob("*.sql")]:
        result["source_sha256"][source.relative_to(ROOT).as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    failure = None
    try:
        preflight()
        for script, log in (("seed.py", "seed_output.txt"), ("verify_design.py", "design_output.txt")):
            step = run_step(script, log)
            result["steps"].append(step)
            if step["exit_code"]:
                raise RuntimeError(f"{script} failed; inspect {log}")
        inspection_queries()
        checks = json.loads((RESULTS / "design_checks.json").read_text(encoding="utf-8"))
        if checks["all_passed"] is not True:
            raise RuntimeError("The constraint suite reported a failure.")
        result["all_passed"] = True
    except Exception as exc:
        failure = str(exc)
        result["error"] = failure
        print(f"FAIL: {failure}", file=sys.stderr)
    finally:
        result["finished_at_utc"] = utc_now()
        write_json(RESULTS / "execution.json", result)
        lines = ["# Portfolio 1 execution evidence", "",
                 f"Result: **{'PASS' if result['all_passed'] else 'FAIL'}**", "",
                 f"Execution context: {result['execution_context']}",
                 f"Started (UTC): {started}",
                 f"Finished (UTC): {result['finished_at_utc']}", ""]
        if result["github_run_url"]:
            lines.extend([f"Run: {result['github_run_url']}",
                          f"Source commit: {result['github_commit']}", ""])
        if result["all_passed"]:
            seed = json.loads((RESULTS / "seed_manifest.json").read_text(encoding="utf-8"))
            checks = json.loads((RESULTS / "design_checks.json").read_text(encoding="utf-8"))
            count = len(checks["constraint_tests"])
            lines.extend([f"Constraint tests passed: **{count}/{count}**", "",
                          f"Database integrity: **{checks['cross_table_checks']['integrity_check']}**",
                          f"Foreign-key violations: **{len(checks['cross_table_checks']['foreign_key_errors'])}**",
                          "", "| Table | Rows |", "|---|---:|"])
            lines += [f"| {table} | {rows:,} |" for table, rows in seed["counts"].items()]
            lines.extend(["", "The outbox is empty at this stage; integration events are generated during Portfolio 3.",
                          "", "Read schema.sql, normalisation.md, the ER diagram and design_checks.json.",
                          "A passing automated run is test evidence, not a personal statement of understanding.",
                          "AI-assisted source code must be acknowledged and reviewed by the student."])
            print(f"\nPASS: {count}/{count} constraint tests; integrity ok; no foreign-key violations.")
        else:
            lines.extend([f"Error: {failure}", "Inspect the available logs before changing or rerunning the implementation."])
        summary = "\n".join(lines) + "\n"
        (RESULTS / "SUMMARY.md").write_text(summary, encoding="utf-8")
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary:
            with open(step_summary, "a", encoding="utf-8") as handle:
                handle.write(summary)
        shutil.copytree(RESULTS, ARTIFACT / "portfolio-1-database-design/results")
        for name in ("sample-data", "data_dictionary.csv"):
            source = P1 / name
            destination = ARTIFACT / "portfolio-1-database-design" / name
            if source.is_dir():
                shutil.copytree(source, destination)
            elif source.is_file():
                shutil.copy2(source, destination)
        if (ROOT / "evidence/environment.json").exists():
            (ARTIFACT / "evidence").mkdir(exist_ok=True)
            shutil.copy2(ROOT / "evidence/environment.json", ARTIFACT / "evidence/environment.json")
        print("Evidence saved in portfolio-1-database-design/results/.")
        print("Upload-ready run evidence is in portfolio1-run-evidence/ (database binary excluded).")
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

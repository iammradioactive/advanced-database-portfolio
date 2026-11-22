"""Execute Portfolios 2-5 in order, preserving saved Portfolio 1 evidence.

Usage: python finish_assessment.py --rebuild
Only project-generated runtime data, current P2-P5 results and generated submission
files are replaced. This command does not push Git or submit to the university.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, shutil, sqlite3, statistics, subprocess, sys, time, traceback, zipfile
from pathlib import Path
from tools.common import ROOT, DB, RUNTIME, utc_now, write_json, connect
from completion.preflight import check as preflight

FOLDERS = ['portfolio-2-query-optimisation', 'portfolio-3-transactions-concurrency',
           'portfolio-4-nosql', 'portfolio-5-distributed-cloud']
OUT = ROOT / 'completion/results'
ARTIFACT = ROOT / 'assessment-artifacts'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fingerprint(folder):
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def run(script, logfile, *args):
    path = ROOT / script
    logfile = Path(logfile)
    logfile.parent.mkdir(parents=True, exist_ok=True)
    print('RUN ' + str(script), flush=True)
    start = time.perf_counter()
    with logfile.open('w', encoding='utf-8') as handle:
        result = subprocess.run([sys.executable, '-u', str(path), *args], cwd=ROOT,
                                stdout=handle, stderr=subprocess.STDOUT, timeout=300)
    elapsed = round(time.perf_counter() - start, 3)
    if result.returncode:
        print(logfile.read_text(encoding='utf-8')[-12000:], flush=True)
        raise RuntimeError(f'{script} failed: inspect {logfile.relative_to(ROOT)}')
    print(f'PASS {script} ({elapsed:.3f} seconds)', flush=True)
    return {'script':str(script),'seconds':elapsed,'exit_code':result.returncode,
            'log':logfile.relative_to(ROOT).as_posix()}


def build_baseline():
    """Run copies of P1 sources; never replace existing P1 evidence."""
    scratch = RUNTIME / 'completion-baseline'
    if scratch.exists(): shutil.rmtree(scratch)
    p1 = scratch / 'portfolio-1-database-design'
    (p1 / 'results').mkdir(parents=True)
    (scratch / 'tools').mkdir()
    for name in ('schema.sql', 'seed.py', 'verify_design.py'):
        shutil.copy2(ROOT / 'portfolio-1-database-design' / name, p1 / name)
    for name in ('common.py', '__init__.py'):
        shutil.copy2(ROOT / 'tools' / name, scratch / 'tools' / name)
    steps = []
    for name in ('seed.py', 'verify_design.py'):
        steps.append(run((p1 / name).relative_to(ROOT), OUT / 'baseline' / (name + '.log')))
    for name in ('seed_manifest.json', 'design_checks.json'):
        shutil.copy2(p1 / 'results' / name, OUT / 'baseline' / name)
    DB.parent.mkdir(exist_ok=True)
    for suffix in ('', '-wal', '-shm'):
        old = Path(str(DB) + suffix)
        if old.exists(): old.unlink()
    shutil.copy2(scratch / 'data/lagoon_market.sqlite', DB)
    shutil.copy2(scratch / 'data/catalogue_seed.jsonl', ROOT / 'data/catalogue_seed.jsonl')
    return steps


def verify():
    checks = []
    def add(name, condition):
        checks.append({'check':name, 'passed':bool(condition)})
        if not condition: raise AssertionError(name)
    baseline = read(OUT / 'baseline/design_checks.json')
    seed = read(OUT / 'baseline/seed_manifest.json')
    add('21 baseline constraints rechecked', baseline['all_passed'] and
        len(baseline['constraint_tests']) == 21 and all(x['passed'] for x in baseline['constraint_tests']))
    b = read(ROOT / FOLDERS[0] / 'results/benchmark_summary.json')
    raw = list(csv.DictReader((ROOT / FOLDERS[0] / 'results/raw_timings.csv').open()))
    for label, variant in b['variants'].items():
        values = [float(row['elapsed_ms']) for row in raw if row['variant'] == label]
        add('Timing sample count and median: ' + label, len(values) == 11 and
            abs(statistics.median(values) - variant['median_ms']) < 1e-9)
    for q in ('q1', 'q2', 'q3'):
        folder = ROOT / FOLDERS[0] / 'results'
        add('Complete before/after CSV equality: ' + q,
            (folder / f'{q}_before_result.csv').read_bytes() == (folder / f'{q}_after_result.csv').read_bytes())
        add('Before/after result hash equality: ' + q,
            b['variants'][q+'_before']['result_sha256'] == b['variants'][q+'_after']['result_sha256'])
    add('Date query four-way ablation equality', len({b['variants'][k]['result_sha256'] for k in
        ('q2_before','q2_rewrite_only','q2_index_only','q2_after')}) == 1)
    for folder, file, expected in [(FOLDERS[1],'transaction_tests.json',12),
                                  (FOLDERS[2],'nosql_tests.json',15),
                                  (FOLDERS[3],'distributed_tests.json',16)]:
        result = read(ROOT / folder / 'results' / file)
        add(folder + ' complete test suite', result['all_passed'] and len(result['tests']) == expected
            and all(x['passed'] for x in result['tests']))
    with connect() as con:
        add('Canonical database integrity', con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
        add('Canonical foreign-key consistency', not con.execute('PRAGMA foreign_key_check').fetchall())
        add('Canonical seeded row counts preserved', all(con.execute('SELECT count(*) FROM '+table).fetchone()[0] == count
            for table, count in seed['counts'].items()))
    seed_docs = sorted([json.loads(line) for line in (ROOT/'data/catalogue_seed.jsonl').read_text().splitlines()], key=lambda x:x['sku'])
    export = read(ROOT / FOLDERS[2] / 'results/catalogue_export.json')
    add('600-document NoSQL export matches SQL-derived seed', len(export) == 600 and sorted(export,key=lambda x:x['sku']) == seed_docs)
    nodes = read(ROOT / FOLDERS[3] / 'results/node_integrity.json')
    add('Four node files have correct integrity and shard placement', len(nodes) == 4 and
        all(x['integrity_check'] == 'ok' and x['wrong_shard_rows'] == 0 for x in nodes.values()))
    return checks


def summaries(meta):
    provenance = f"Execution context: **{meta['execution_context']}**\n\nRun: {meta['run_url'] or 'Local verification; no GitHub run claimed.'}\n\n"
    b = read(ROOT / FOLDERS[0] / 'results/benchmark_summary.json')
    text = '# Portfolio 2: measured results\n\n' + provenance
    text += '| Query | Before median (ms) | After median (ms) | Ratio | Same result |\n|---|---:|---:|---:|---|\n'
    for x in b['comparisons']:
        text += f"| {x['query']} | {x['before_median_ms']:.6f} | {x['after_median_ms']:.6f} | {x['speedup']:.2f}x | {x['identical_results']} |\n"
    text += '\nThree warm-ups; eleven samples per variant; timed execution plus all result fetching. Warm-cache local measurements only.\n\n'
    text += '## Date-query ablation\n\n'
    for k in ('q2_before','q2_rewrite_only','q2_index_only','q2_after'):
        text += f"- `{k}`: {b['variants'][k]['median_ms']:.6f} ms.\n"
    text += '\nAll four variants returned the same records. A function applied to a date column and a direct timestamp range can have very different access plans; see `plans/`.\n'
    text += f"\nIndex creation and statistics: {b['method']['index_build_ms']:.3f} ms.\n"
    text += f"Database allocation before/after: {b['method']['database_bytes_before']:,} / {b['method']['database_bytes_after']:,} bytes.\n"
    text += f"Measured per-index bytes (when dbstat is available): `{b['method']['index_sizes_bytes']}`.\n"
    text += '\nIndexes consume space and add maintenance on writes. This experiment measures read queries and build time, not write-throughput or production service levels.\n'
    (ROOT / FOLDERS[0] / 'results/SUMMARY.md').write_text(text)
    for number, folder, file in [(3,FOLDERS[1],'transaction_tests.json'),(4,FOLDERS[2],'nosql_tests.json'),(5,FOLDERS[3],'distributed_tests.json')]:
        result = read(ROOT / folder / 'results' / file)
        text = f'# Portfolio {number}: executed checks\n\n' + provenance
        text += f"Result: **PASS - {len(result['tests'])}/{len(result['tests'])} checks**\n\n"
        for x in result['tests']:
            text += f"## {x['test']}\n\n```json\n{json.dumps({k:v for k,v in x.items() if k not in ('test','passed')},indent=2)}\n```\n\n"
        if number == 5:
            text += 'Executed on one host as separate local processes. Docker, public cloud, multi-host faults and automatic consensus were not executed.\n'
        (ROOT / folder / 'results/SUMMARY.md').write_text(text)
    main = '# Completed execution: Portfolios 2-5\n\n' + provenance
    main += 'All implementation checks passed. Portfolio 1 evidence was preserved unchanged; its schema was rechecked on a fresh isolated copy.\n\n'
    main += '| Activity | Verified evidence |\n|---|---|\n'
    main += '| P1 baseline | 21 constraint cases; integrity and foreign keys |\n| P2 | 6 business queries; 3 equal-result before/after comparisons; date-query ablation |\n| P3 | 12 transaction and concurrency checks |\n| P4 | 15 persistent NoSQL checks |\n| P5 | 16 distributed-process checks |\n\n'
    main += '## Read these four outcomes\n\n'
    main += '1. Query optimisation changes access paths, not answers; compare the before/after plans and full result equality.\n'
    main += '2. The unsafe reservation sequence ends at 3 units; the protected sequence ends at 6. A database lock cannot repair a stale read made outside the transaction.\n'
    main += '3. Product attributes vary naturally in JSON values, but the application still validates prices and repairs secondary-key indexes.\n'
    main += '4. Replicas can be stale. A caught-up replica supports reads after a primary stops, but writes need a safely fenced promotion.\n\n'
    main += '## Before submission\n\nRead the activity READMEs and results. Review the generated 3-page Word/PDF summary in `submission/`; replace any identity or personal-verification placeholders. Give the assessor access to the private repository. Follow any separate university filename instructions. Nothing is submitted automatically.\n\n'
    main += 'The automated results commit records this execution only. It does not represent semester-long development or replace your technical reflection.\n'
    (OUT / 'SUMMARY.md').write_text(main)
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'docs/FINAL_STATUS.md').write_text(main)
    review = '# Review against the published rubric\n\n| Criterion | Marks | Evidence |\n|---|---:|---|\n'
    for row in [('Technical correctness',8,'Baseline validation, result equality, transaction/NoSQL/cluster assertions; completion/results/verification.json'),('Database design quality',6,'Portfolio 1 ER diagram, schema, keys, constraints and normalisation'),('Practical implementation',8,'Executable scripts and per-activity results; source hashes and run URL'),('Query and performance analysis',5,'Raw timings, plans, ablation, index costs and current P2 summary'),('Advanced database concepts',5,'Concurrency, key-value persistence, replication, sharding and manual failover'),('Documentation and GitHub organisation',5,'Five named folders, READMEs, summary and references'),('Technical reflection / individual understanding',3,'Review the technical reflection and complete the personal verification sentence')]:
        review += '| '+' | '.join(map(str,row))+' |\n'
    review += '\nThis is an evidence map, not a predicted mark. Assessor access, a meaningful personal reflection and final LMS upload remain the student\'s responsibility.\n'
    (ROOT / 'docs/RUBRIC_REVIEW.md').write_text(review)
    readme = ROOT / 'README.md'
    if readme.exists():
        text = readme.read_text(encoding='utf-8')
        marker = '<!-- verified-completion -->'
        text = text.split(marker)[0].rstrip()
        text += '\n\n'+marker+'\n## Latest verified implementation\n\nPortfolios 2-5 have been executed in sequence. '
        text += 'See [current results](docs/FINAL_STATUS.md), [rubric evidence](docs/RUBRIC_REVIEW.md), '
        text += 'and the [submission summary](submission/MIT8103_Portfolio_Summary.pdf). '
        text += 'The earlier Portfolio 1 run evidence is retained in its original folder.\n'
        readme.write_text(text)


def package_artifact():
    ARTIFACT.mkdir(exist_ok=True)
    for file in (ROOT / 'submission').iterdir():
        if file.is_file(): shutil.copy2(file, ARTIFACT / file.name)
    excluded = {'.git','.venv','.runtime','__pycache__','assessment-artifacts','portfolio1-run-evidence'}
    with zipfile.ZipFile(ARTIFACT / 'MIT8103_Complete_Project.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for file in sorted(ROOT.rglob('*')):
            rel = file.relative_to(ROOT)
            if not file.is_file() or excluded.intersection(rel.parts): continue
            if file.name.endswith(('.sqlite','.sqlite-wal','.sqlite-shm','.pyc','.db','.dat','.dir','.bak')): continue
            if file.suffix == '.zip': continue
            archive.write(file, 'advanced-database-portfolio/' + rel.as_posix())
    # An upload-ready fallback is kept if branch rules prevent the automated commit.
    backup = ARTIFACT / 'evidence-for-manual-upload'
    for folder in FOLDERS:
        shutil.copytree(ROOT / folder / 'results', backup / folder / 'results', dirs_exist_ok=True)
    for folder in ('completion/results','submission'):
        shutil.copytree(ROOT/folder,backup/folder,dirs_exist_ok=True)
    for file in ('README.md','docs/FINAL_STATUS.md','docs/RUBRIC_REVIEW.md'):
        if (ROOT/file).exists():
            (backup/file).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/file,backup/file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true')
    args = parser.parse_args()
    if not args.rebuild: parser.error('Use --rebuild to allow project-local generated data to be replaced.')
    if sys.flags.optimize: parser.error('Do not use -O: the executable tests use assertions.')
    p1 = ROOT / 'portfolio-1-database-design'
    required = [p1/'schema.sql',p1/'seed.py',p1/'verify_design.py',ROOT/'tools/common.py']
    if any(not file.is_file() for file in required): raise RuntimeError('Portfolio 1 implementation is missing from the repository root.')
    preserved = fingerprint(p1)
    for folder in [OUT, ARTIFACT, *(ROOT/f/'results' for f in FOLDERS)]:
        if folder.exists(): shutil.rmtree(folder)
        folder.mkdir(parents=True)
    RUNTIME.mkdir(exist_ok=True)
    repo = os.environ.get('GITHUB_REPOSITORY')
    server = os.environ.get('GITHUB_SERVER_URL','https://github.com')
    context = os.environ.get('GITHUB_ACTIONS') == 'true'
    meta = {'started_at_utc':utc_now(), 'execution_context':'GitHub Actions' if context else 'local verification',
            'repository_url':f'{server}/{repo}' if context and repo else '[PRIVATE GITHUB REPOSITORY URL]',
            'run_url':f"{server}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID')}" if context and repo else None,
            'source_commit':os.environ.get('GITHUB_SHA'), 'all_passed':False, 'steps':[],
            'portfolio1_source_and_evidence_sha256':preserved}
    ok = False
    try:
        meta['environment'] = preflight()
        meta['steps'] += build_baseline()
        for folder, script in zip(FOLDERS,('benchmark.py','run_tests.py','run_tests.py','cluster_test.py')):
            meta['steps'].append(run(folder+'/'+script, ROOT/folder/'results/execution.log'))
        meta['steps'].append(run('completion/sql_console.py',ROOT/FOLDERS[1]/'results/standalone_sql_output.txt',
                                 '--copy','--file',FOLDERS[1]+'/transaction_examples.sql'))
        checks = verify()
        if fingerprint(p1) != preserved: raise AssertionError('Saved Portfolio 1 files were unexpectedly changed.')
        checks.append({'check':'Original Portfolio 1 files preserved byte-for-byte','passed':True})
        write_json(OUT/'verification.json', {'verified_at_utc':utc_now(),'all_passed':True,'checks':checks})
        meta['database_tests_passed'] = True
        meta['source_sha256'] = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                for folder in FOLDERS for p in (ROOT/folder).rglob('*')
                                if p.is_file() and 'results' not in p.parts and '__pycache__' not in p.parts}
        write_json(OUT/'execution.json',meta)
        summaries(meta)
        meta['steps'].append(run('completion/build_submission.py',OUT/'document_build.log'))
        meta['all_passed'] = True
        meta['finished_at_utc'] = utc_now()
        write_json(OUT/'execution.json',meta)
        package_artifact()
        ok = True
        print('PASS: Portfolios 2-5, 21 baseline checks, 43 remaining scenario checks, 3 query pairs, and summary generation.')
    except Exception as exc:
        meta['all_passed'] = False
        meta['error'] = str(exc)
        traceback.print_exc()
    finally:
        meta['finished_at_utc'] = utc_now()
        write_json(OUT/'execution.json',meta)
        shutil.copytree(OUT, ARTIFACT/'run-diagnostics', dirs_exist_ok=True)
        summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary_file:
            with open(summary_file,'a',encoding='utf-8') as handle:
                if ok: handle.write((OUT/'SUMMARY.md').read_text())
                else: handle.write('# Completion run did not finish\n\nInspect the failed step and completion/results/execution.json. No success is claimed.\n')
    return 0 if ok else 1

if __name__ == '__main__': raise SystemExit(main())

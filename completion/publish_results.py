"""Save generated evidence with a normal, non-forced Git commit and push.

Only runs when explicitly invoked in GitHub Actions. Needs contents: write.
No personal access token, password, backdated commit or fabricated user identity.
If branch protection rejects the push, the artifact remains available for download.
"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATHS=['README.md','docs/FINAL_STATUS.md','docs/RUBRIC_REVIEW.md','completion/results','submission',
       'portfolio-2-query-optimisation/results','portfolio-3-transactions-concurrency/results',
       'portfolio-4-nosql/results','portfolio-5-distributed-cloud/results']

def git(*args,check=True):
    return subprocess.run(['git',*args],cwd=ROOT,check=check,text=True,capture_output=True)

def main():
    if os.environ.get('GITHUB_ACTIONS')!='true':
        raise RuntimeError('Automatic publishing is only enabled inside the explicitly started GitHub Actions workflow.')
    report=json.loads((ROOT/'completion/results/execution.json').read_text())
    if report.get('all_passed') is not True:raise RuntimeError('Refusing to publish results from an incomplete execution.')
    branch=os.environ.get('GITHUB_REF_NAME','')
    if not branch:raise RuntimeError('GitHub branch name is unavailable.')
    git('check-ref-format','--branch',branch)
    # Do not absorb unrelated staged changes into the generated-results commit.
    if git('diff','--cached','--name-only').stdout.strip():
        raise RuntimeError('Unexpected staged changes; refusing to include unrelated work.')
    files=[p for p in PATHS if (ROOT/p).exists()]
    git('add','--',*files)
    if git('diff','--cached','--quiet',check=False).returncode==0:
        note='No new generated results to commit.\n'
    else:
        git('config','user.name','github-actions[bot]')
        git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
        git('commit','-m','Save verified Portfolio 2-5 results and submission summary')
        result=git('push','origin','HEAD:refs/heads/'+branch,check=False)
        if result.returncode:
            note=('TESTS PASSED, BUT AUTOMATIC SAVING WAS BLOCKED.\n'
                  'No force push was attempted. Check branch protection and workflow permissions.\n'
                  'Download MIT8103-final-submission; evidence-for-manual-upload contains the generated files.\n')
            (ROOT/'assessment-artifacts/AUTO_SAVE_STATUS.txt').write_text(note)
            print(note,file=sys.stderr)
            print(result.stderr[-2000:],file=sys.stderr)
            summary=os.environ.get('GITHUB_STEP_SUMMARY')
            if summary:
                with open(summary,'a') as f:f.write('\n## Automatic repository saving failed\n\n'+note)
            return 1
        sha=git('rev-parse','HEAD').stdout.strip()
        note=f'Generated evidence and submission documents saved to {branch}.\nCommit: {sha}\n'
    (ROOT/'assessment-artifacts/AUTO_SAVE_STATUS.txt').write_text(note)
    print(note)
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:f.write('\n## Results saved to the repository\n\n'+note)
    return 0

if __name__=='__main__':raise SystemExit(main())

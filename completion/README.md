# Complete Portfolios 2-5 without repeated uploads

Prerequisite: the existing Portfolio 1 implementation is present at the repository root.
The completed Portfolio 1 evidence is preserved byte-for-byte.

## What happens

`python finish_assessment.py --rebuild` rechecks copies of the Portfolio 1 sources in
an isolated runtime directory, creates a fresh deterministic dataset, then executes
Portfolios 2, 3, 4 and 5 in sequence. It measures query timings, tests transaction
behaviour, exercises a persistent NDBM store, and starts/stops four local HTTP database
processes. It checks cross-model consistency, produces per-activity summaries and
builds the three-page Word/PDF summary using actual measurements from that run.

The optional GitHub workflow then saves only generated reports and submission files
in a clearly identified `github-actions[bot]` commit. It never force-pushes, rewrites
history, changes repository visibility or submits to the university. The workflow
requests `contents: write` solely for this results commit. It needs no personal token.

## Browser setup

Upload all contents of the supplied upload folder to the repository root. Open the
existing `.github/workflows/portfolio1.yml` file, edit it and replace its contents with
`completion/WORKFLOW.txt`. The existing workflow filename can stay unchanged. Commit
that change, then run **Complete remaining portfolios** in Actions on `main`.

This reuses the workflow file that already worked, avoiding another hidden-folder
upload. Portfolio 1 can still be rerun manually with `python run_portfolio1.py --rebuild`.
Historical workflow runs remain in GitHub; no history is manufactured.

Optional workflow inputs set the name and matriculation number in the summary. Blank
inputs leave explicit placeholders. The repository/run URL is taken from GitHub.

## Outputs

- `portfolio-2-query-optimisation/results/`: query CSVs, native plans, timings and analysis.
- `portfolio-3-transactions-concurrency/results/`: test observations and SQL traces.
- `portfolio-4-nosql/results/`: persistent-store tests, exports and query outputs.
- `portfolio-5-distributed-cloud/results/`: deployment, HTTP logs and failover checks.
- `completion/results/`: execution metadata, source hashes, combined verification and PDF previews.
- `submission/`: three-page DOCX/PDF and submission instructions.
- Download artifact **MIT8103-final-submission**: summary files, full project ZIP and upload-ready fallback evidence.

No initial measured results are included in this upload. Your workflow creates them.
A failed check stops the run; it is not converted into a pass or replaced with sample
outputs. If branch protection blocks the results push, download the artifact and read
AUTO_SAVE_STATUS.txt. There is no need to rerun successful tests solely to recover files.

## Local requirements

Python 3.11+; SQLite 3.37+ with JSON; POSIX file locking; a real `dbm.ndbm` module;
python-docx, LibreOffice Writer and poppler-utils. The documented GitHub configuration
uses Ubuntu 24.04's system Python. The optional native DBM library is reported at runtime,
not assumed to be identical across operating systems. No mocked database fallback exists.

## Execution scope

Distributed nodes are separate local processes on one machine. Docker and public cloud
are optional, unexecuted configurations. No production uptime, multi-host tolerance,
automatic consensus or semester-long progress is inferred from this one run.

Read each README and its generated summary. An automated run produces evidence but
cannot supply your personal understanding or a genuine account of your own review.

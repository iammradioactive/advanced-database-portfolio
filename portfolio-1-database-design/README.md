# Portfolio 1 - Database Design and Modelling

**Organisation:** Lagoon Market, a simulated online retailer with Ikeja and Lekki warehouses.

This folder contains implementation files, not just a proposed design. Start with
`case-study.md`, `table-design.md` and `er_diagram.png`. `schema.sql` is authoritative.

## Evidence map

| Assessment evidence | File |
|---|---|
| Chosen case study | case-study.md |
| ER diagram | er_diagram.png; editable source er_diagram.dot |
| Relational schema | relational-schema.md |
| Keys, constraints and triggers | schema.sql; data_dictionary.csv |
| Normalisation explanation | normalisation.md |
| Executable dataset generator | seed.py |
| Constraint tests | verify_design.py |
| SQL inspection examples | example_queries.sql |
| Saved results and run provenance | results/SUMMARY.md; results/execution.json; results/design_checks.json |
| Readable sample records | sample-data/ |

## Run from GitHub without a local installation

The repository includes `.github/workflows/portfolio1.yml`. Commit it on the default
branch, open **Actions**, select **Portfolio 1 - Build and verify**, and choose
**Run workflow**. This manually rebuilds the database in an isolated GitHub runner.
It does not write commits, require personal tokens or submit anything to the university.

A successful run publishes a summary and a downloadable artifact named
`portfolio1-evidence`. Download and extract it, then upload its
`portfolio-1-database-design` and `evidence` folders to the repository root to preserve
your actual run outputs. Read the results before committing them. Artifact retention
is 14 days, so do not rely on the temporary Actions download as the only submission copy.

Actions usage in a private repository draws on the account's included usage and may
incur charges beyond that allowance. This workflow runs only when manually requested.
Do not enable paid usage merely to follow this guide.

## Equivalent local command

From the repository root, using Python 3.11+ and SQLite 3.37+ with JSON functions:

```bash
python run_portfolio1.py --rebuild
```

No third-party Python packages are needed for Portfolio 1. This replaces only the
project's generated `data/lagoon_market.sqlite`, result reports and upload-ready
run-evidence folder. Close any connections to this database before rebuilding.
The driver runs `seed.py`, then `verify_design.py`, then the inspection queries.
A failure returns a nonzero exit code and is recorded in the logs.

## What the code implements

The schema contains 11 STRICT tables, two views, primary and foreign keys, CHECK and
UNIQUE constraints, a partial unique index and historical-data protection triggers.
The generator creates 5,000 customers, 600 products and 120,000 orders with related
records. Readable samples are exported; the full database is regenerated, not uploaded
through GitHub's web interface. The tests attempt 21 invalid changes under savepoints,
then verify integrity, foreign keys, payment totals, reservations and shipments.

Read `normalisation.md` alongside the schema: customer details, category descriptions
and warehouse details are not copied into each order line. Historical sale price is
stored on the line because it is a different fact from the current catalogue price.

The scope is one warehouse and shipment per order, one successful charge, no refunds
or tax calculations. Atomic checkout and workflow transitions belong to Portfolio 3.
The outbox holds integration events in later activities and is empty in this seed.

## Provenance and individual verification

The files were prepared with ChatGPT assistance and executed in the assistant's local
runtime. The supplied results are labelled with their actual local context; they do
not claim a GitHub run or student verification. The GitHub workflow configuration has
not been executed in the student's account by the assistant. Running it produces fresh
results tied to the student's real repository commit and workflow URL.

A green test result is not a substitute for understanding. Review the schema and
normalisation, explain why stock has a composite key, and inspect at least one rejected
invalid update. Record what you personally checked in your technical reflection and
AI-use declaration. Do not describe assistant-authored code as independently authored.

## References

Technical references and the verified GitHub workflow instructions are in REFERENCES.md.

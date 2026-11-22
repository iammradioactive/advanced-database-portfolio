# Portfolio 4 - NoSQL and Advanced Data Models (7 marks)

```bash
python portfolio-4-nosql/run_tests.py
python portfolio-4-nosql/kv_cli.py --get LM-01-0001
python portfolio-4-nosql/kv_cli.py --category 4 --max-price-kobo 1000000
python portfolio-4-nosql/kv_cli.py --export
```

This is an actual, independent **key-value database**, using `dbm.ndbm` and the native
DBM library reported by the execution environment. It is not a Python dictionary mock,
a JSON file pretending to be a database, MongoDB, or SQLite's JSON extension. The exact
backend and module are asserted and saved. NDBM is a small embedded interface: using it
does not imply access to a richer native transactional API.

## Model and access patterns

`model.json` specifies five key families. A `product:<sku>` value embeds a complete JSON
catalogue document. Food documents carry storage/allergen information; electronics
carry warranty information; stationery can specify packaging properties. This avoids
a wide product table with mostly inapplicable columns, while common identifiers,
prices and categories remain consistent with the relational authority. Product values
are validated by the application; flexible schema is not permission to accept negative
prices or missing keys.

A `category:<id>` value is a sorted SKU list. Queries read that key, fetch its documents
and apply price/attribute filters in Python. The engine itself has no SQL query planner,
server-side JSON predicate language or native secondary-index maintenance. The code
makes the query work explicit rather than labelling a Python filter as a MongoDB query.
Delivery values embed a bounded order-centric event history; cart values carry expiry
metadata. The TTL is checked and lazily deleted by the application, not by the engine.

## Practical evidence

The 15 tests import all 600 products and compare their base fields with SQL, perform
key lookups, category/price and nested-attribute queries, insert/read/delete a draft,
update flexible attributes, delete and restore a product, move a product between
category indexes, store 20 real source-linked delivery documents and expire a cart.
An independent subprocess reopens the store to prove persistence. Another test
intentionally deletes a category index, detects inconsistency and rebuilds it. This is
logical damage injection, not an invented crash-recovery result. A JSON export is
loaded into a second physical store and the document hashes are compared.

`results/nosql_tests.json` records every observation. Full result sets, the portable
600-document export and a delivery example are included. The final catalogue is
restored to the original generated contents and all category indexes are checked.

## Suitability and limits

Direct SKU access and product-specific attributes suit a key-value read projection.
Orders, stock reservations and payments remain relational because they need joined
constraints and atomic multi-row updates. A cache miss can be rebuilt from the SQL
source and the attribute seed. DBM offers neither a foreign-key constraint nor automatic
TTL, distributed replication or native multi-key transactions through this interface.

A POSIX advisory file lock serializes cooperating writers and prevents cooperating
readers seeing a live multi-key update. A process crash can nevertheless leave document
and index keys inconsistent; the demonstrated rebuild is the recovery mechanism.
Full reindexing on each product mutation is acceptable for this 600-product teaching
store but O(n) and unsuitable for a high-write, very large catalogue. A transactional
key-value/document service would be a production alternative. No such external service
was deployed or benchmarked here. DBM binary files are backend-dependent; the JSON
export and reload script are the portable submission artefacts. Use Linux/WSL with
`dbm.ndbm` available rather than silently replacing the engine on another platform.

Reference: Python Software Foundation (n.d.); see `docs/REFERENCES.md`.

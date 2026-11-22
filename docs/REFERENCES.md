# References (APA 7th edition)

Gilbert, S., & Lynch, N. (2002). Brewer's conjecture and the feasibility of consistent,
    available, partition-tolerant web services. *ACM SIGACT News, 33*(2), 51-59.
    https://doi.org/10.1145/564585.564601
    Author-hosted manuscript: https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer6.pdf

Miva Open University. (2026). *MIT 8103 Advanced Database Systems: First semester
    continuous assessment, 2026/2027 academic session* [Assessment brief].
    Supplied assessment, September cohort 2026.

Python Software Foundation. (n.d.). *dbm - Interfaces to Unix "databases"*.
    In *Python 3.13 documentation*. https://docs.python.org/3.13/library/dbm.html

SQLite. (n.d.-a). *Appropriate uses for SQLite*. https://www.sqlite.org/whentouse.html

SQLite. (n.d.-b). *EXPLAIN QUERY PLAN*. https://www.sqlite.org/eqp.html

SQLite. (n.d.-c). *Isolation in SQLite*. https://www.sqlite.org/isolation.html

SQLite. (n.d.-d). *Query planning*. https://www.sqlite.org/queryplanner.html

SQLite. (n.d.-e). *SQLite shared-cache mode*. https://www.sqlite.org/sharedcache.html

## Resource and code provenance

The assessment defines the required deliverables and marking criteria. The SQLite and
Python documentation support the engine semantics; the Gilbert and Lynch paper supports
the discussion of partitions and consistency. The submitted data are newly generated,
fictional Lagoon Market records using seed 8103, not an external customer dataset.
All SQL and application code were developed for this portfolio with ChatGPT assistance;
no third-party tutorial implementation was copied. Python, SQLite and the DBM backend
are runtime dependencies. Graphviz, python-docx, LibreOffice, Pillow and Playwright were
used to prepare diagrams, documents and browser captures. Their package versions and
roles are recorded separately in `evidence/authoring_environment.json`.

The AI-use declaration records assistance explicitly. A generated technical reflection
is not evidence that the student personally performed the experiments; the student must
complete the separate verification record before claiming individual ownership.

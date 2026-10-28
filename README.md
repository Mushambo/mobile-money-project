# Project 2 – Mobile Money Investigations with PostgreSQL and Neo4j

Advanced Big Data Analytics, Project 2 (issued 12 Oct 2026, due 26 Oct 2026 23:59 CAT).
Group members: `<Name – Student ID>`, `<Name – Student ID>`, `<Name – Student ID>`

The September 2026 records from the unchanged `mobile_money_generator.py` are captured to CSV,
loaded into PostgreSQL and Neo4j, queried with seven SQL/Cypher pairs, cross-checked, timed and
load-tested. CSVs and database stores stay local (see `.gitignore`).

## Folder layout

```
mobile_money_generator.py      supplied generator – DO NOT EDIT (hash in generator.sha256)
generator.sha256               SHA-256 of the supplied generator
.env.example                   connection settings with placeholder secrets (copy to .env)
requirements.txt
sql/
  01_schema.sql                five tables, NOT NULL columns, Africa/Kigali time zone   (2.1)
  02_load.psql                 \copy bulk load, parents first                          (2.2)
  03_constraints_indexes.sql   PKs, FKs, CHECKs, required indexes, BRIN, ANALYZE        (2.1/2.2)
  04_checks.sql                counts, audit totals, roles, constraints, indexes, sizes (2.2)
  queries/Q1..Q7*.sql          readable copies of the SQL queries (generated)
cypher/
  01_import.sh / 01_import.ps1 neo4j-admin full import (Linux-macOS / Windows)       (3.2)
  02_constraints_indexes.cypher unique constraints + TRANSFER.occurred_at range index (3.2)
  03_checks.cypher             node/relationship counts, roles, owners, audit totals   (3.2)
  queries/Q1..Q7*.cypher       readable copies of the Cypher queries (generated)
src/
  config.py                    reads .env (PG_DSN, NEO4J_*), data/result folders
  capture.py                   preview + progressive CSV capture + audit               (1.2)
  workspace_info.py            versions, CPU, RAM, OS, DB memory settings             (1.1)
  prepare_import.py            typed-header import copies + owns.csv; --clean         (3.2)
  trace_account.py             one account traced with JOINs and MATCH                (3.3)
  queries.py                   all SQL/Cypher pairs, review sets, 61 case list        (4–5)
  db.py                        run_pg / run_neo wrappers + normalization              (6.1)
  reference_answers.py         independent pandas answers for all 61 cases           (6.1)
  compare.py                   61-case status table + Q7 path verification            (6.1)
  independent_checks.py        overlap + chain/cycle checked against raw CSV rows     (6.1)
  benchmark.py                 21-case timing, 3 warm-ups + 5 runs, summary/ratios    (6.2/6.3)
  explain_plans.py             EXPLAIN (ANALYZE, BUFFERS) and PROFILE                 (6.2/6.3)
  loadtest.py                  multiprocessing + Barrier load test                    (7.1)
  plots.py, diagrams.py        charts and schema/evidence diagrams                    (4, 5, 7, 8)
  export_queries.py            writes sql/queries and cypher/queries files
  verify_generator.py          confirms the generator is unchanged                    (9.2)
results/                       raw outputs, summaries, plans, charts, diagrams (submitted)
report/                        report draft (.docx) – add screenshots, export to PDF
data/                          CSVs and Neo4j import copies – LOCAL ONLY, not submitted
```

## Prerequisites

* Python 3.10+ ; `pip install -r requirements.txt`
* PostgreSQL 14+ (tested on 16.15) with `psql` on PATH
* Neo4j Community 5.x (5.26 LTS or newer) with `neo4j-admin`; Graphviz `dot` for diagrams
* About 10 GB free disk. Suggested memory (record what you actually use):
  * PostgreSQL `postgresql.conf`: `shared_buffers = 1GB`, `work_mem = 64MB`,
    `maintenance_work_mem = 1GB`, `effective_cache_size = 4GB`, `max_wal_size = 8GB`
  * Neo4j `conf/neo4j.conf`: `server.memory.heap.initial_size=2g`, `server.memory.heap.max_size=2g`,
    `server.memory.pagecache.size=3g`

Copy `.env.example` to `.env` and put your real passwords there (never commit `.env`).

## Execution order (run every command from the project root)

| Step | Section | Command |
|---|---|---|
| 0 | 9.2 | `python src/verify_generator.py` |
| 1 | 1.1 | `psql -U postgres -c "CREATE DATABASE mobile_money"` then `python src/workspace_info.py` (both services running) |
| 2 | 1.2 | `python src/capture.py --preview` then `python src/capture.py` |
| 3 | 2.1 | `psql -d mobile_money -f sql/01_schema.sql` |
| 4 | 2.2 | `psql -d mobile_money -f sql/02_load.psql` (load seconds) |
| 5 | 2.2 | `psql -d mobile_money -f sql/03_constraints_indexes.sql` (setup seconds) |
| 6 | 2.2 | `psql -d mobile_money -f sql/04_checks.sql` |
| 7 | 3.2 | `python src/prepare_import.py` |
| 8 | 3.2 | Stop Neo4j; `NEO4J_HOME=... bash cypher/01_import.sh` (Windows: `cypher\01_import.ps1`) |
| 9 | 3.2 | `cypher-shell -u neo4j -p <pw> -f cypher/02_constraints_indexes.cypher` (time it); note store / tx-log size of `data/databases/neo4j` and `data/transactions/neo4j` |
| 10 | 3.2 | `cypher-shell -u neo4j -p <pw> -f cypher/03_checks.cypher`, then `python src/prepare_import.py --clean` |
| 11 | 3.3 | `python src/trace_account.py --account 998` |
| 12 | 4–5 | `python src/reference_answers.py` (independent answers, ~1 min, ~3 GB RAM) |
| 13 | 6.1 | `python src/compare.py` → 61-case status table; `python src/independent_checks.py` |
| 14 | 6.2 | Only PostgreSQL running: `python src/benchmark.py --engine pg --sql-q7 baseline` ; `python src/explain_plans.py --engines pg` |
| 15 | 6.2 | Only Neo4j running: `python src/benchmark.py --engine neo` ; `python src/explain_plans.py --engines neo` |
| 16 | 6.3 | Only PostgreSQL: `python src/compare.py --engines pg --sql-q7 improved` ; `python src/benchmark.py --engine pg --sql-q7 improved --only Q7` ; `python src/benchmark.py --summarize` |
| 17 | 7.1 | Only PostgreSQL: `python src/loadtest.py --engine pg` ; only Neo4j: `python src/loadtest.py --engine neo` ; `python src/loadtest.py --summarize` |
| 18 | charts | `python src/plots.py` ; `python src/diagrams.py` ; `python src/export_queries.py` |
| 19 | 9.2 | Both running: `python src/compare.py` (final rerun, screenshot), then stop both services and screenshot stopped status |

## Notes on query choices

* Hour windows are 09:45:00 inclusive to 10:45:00 exclusive CAT, converted to epoch seconds in
  Python with `zoneinfo("Africa/Kigali")` (`queries.hour_bounds`).
* Q4 SQL carries node kind with the ID; Cypher uses a bounded undirected pattern followed
  immediately by `WITH DISTINCT b`, which lets Neo4j use a pruning variable-length expand.
  The depth is formatted into the Cypher text from a validated integer because Cypher cannot
  parameterize a variable-length bound.
* Q6 "stop at the first return": a walk that reaches the review account is closed and never
  extended, so a 2-transfer return ends that walk and is not reported (length < 3).
* Q7 baseline SQL is a direct recursive breadth-first search; `Q7_SQL_IMPROVED` (Section 6.3)
  searches from both ends over distinct person neighbours, giving identical answers. The SQL
  version selected for Sections 7 and 8 is the improved one.
* `compare.py` normalizes integers/dates/lists and sorts rows before exact comparison; Q7
  lengths are compared separately from supporting-path verification (`q7_path_checks.json`).

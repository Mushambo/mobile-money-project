"""Section 6.1 - query wrappers returning every result row, plus result normalization."""
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, PG_DSN  # noqa: E402

_pg = None
_neo = None


def pg_conn():
    global _pg
    if _pg is None or _pg.closed:
        import psycopg
        _pg = psycopg.connect(PG_DSN, autocommit=True)
        _pg.execute("SET timezone TO 'Africa/Kigali'")
    return _pg


def neo_driver():
    global _neo
    if _neo is None:
        from neo4j import GraphDatabase
        _neo = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        _neo.verify_connectivity()
    return _neo


def run_pg(query, params=None, timeout_s=None):
    """Execute on the persistent PostgreSQL connection and return all rows as tuples."""
    conn = pg_conn()
    with conn.cursor() as cur:
        if timeout_s:
            cur.execute(f"SET statement_timeout = {int(timeout_s * 1000)}")
        cur.execute(query, params or {})
        rows = cur.fetchall()
        if timeout_s:
            cur.execute("SET statement_timeout = 0")
    return rows


def run_neo(query, params=None, timeout_s=None):
    """Execute on the persistent Neo4j driver (auto-commit) and return all rows as tuples."""
    from neo4j import Query
    q = Query(query, timeout=timeout_s) if timeout_s else query
    with neo_driver().session(database=NEO4J_DATABASE) as s:
        return [tuple(r.values()) for r in s.run(q, params or {})]   # consumes every row


def _norm_value(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if hasattr(v, "to_native"):                 # neo4j.time.Date / DateTime
        v = v.to_native()
    if isinstance(v, _dt.datetime):
        return v.date().isoformat() if v.time() == _dt.time() else v.isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return tuple(_norm_value(x) for x in v)
    try:
        import decimal
        if isinstance(v, decimal.Decimal):
            return int(v)
    except Exception:
        pass
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def normalize(rows):
    """Integers as int, dates as ISO text, lists as tuples, then sorted for exact comparison."""
    return sorted((tuple(_norm_value(v) for v in r) for r in rows), key=repr)


def close():
    global _pg, _neo
    if _pg is not None:
        _pg.close()
        _pg = None
    if _neo is not None:
        _neo.close()
        _neo = None

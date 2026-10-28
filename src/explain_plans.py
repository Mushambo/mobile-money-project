"""Section 6.2.3 / 6.3 - collect plans OUTSIDE timing.
PostgreSQL: EXPLAIN (ANALYZE, BUFFERS) ; Neo4j: PROFILE.
Cases: Q2 full month, Q4 B depth 10, Q7 B bound 6 (baseline and improved SQL).

    python src/explain_plans.py --engines pg      (with PostgreSQL running)
    python src/explain_plans.py --engines neo     (with Neo4j running)
Plans are written to results/plans/.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import NEO4J_DATABASE, RESULTS_DIR  # noqa: E402
from db import close, neo_driver, pg_conn  # noqa: E402
import queries as Q  # noqa: E402

PLANS = RESULTS_DIR / "plans"


def plan_cases():
    b = Q.set_params("B")
    return [("Q2_month", "Q2", {}), ("Q4_B_depth10", "Q4", {**b, "depth": 10}),
            ("Q7_B_bound6", "Q7", {**b, "bound": 6})]


def pg_plans():
    conn = pg_conn()
    for name, q, p in plan_cases():
        variants = [("", False)] + ([("_improved", True)] if q == "Q7" else [])
        for suffix, improved in variants:
            sql = "EXPLAIN (ANALYZE, BUFFERS, VERBOSE OFF) " + Q.sql_for(q, p, improved)
            with conn.cursor() as cur:
                cur.execute(sql, Q.pg_params(q, p))
                text = "\n".join(r[0] for r in cur.fetchall())
            out = PLANS / f"pg_{name}{suffix}.txt"
            out.write_text(Q.sql_for(q, p, improved).strip() + "\n\n" + text + "\n")
            print(f"--- {out.name}\n" + "\n".join(text.splitlines()[-4:]))


def _fmt(op, depth=0):
    args = op.get("args", {})
    line = (f"{'  ' * depth}+{op.get('operatorType')}  rows={args.get('Rows', '?')}  "
            f"dbHits={args.get('DbHits', '?')}  estRows={round(args.get('EstimatedRows', 0) or 0)}  "
            f"time_ms={round((args.get('Time', 0) or 0) / 1e6, 2) if 'Time' in args else '?'}  "
            f"{args.get('Details', '')}")
    lines = [line]
    for c in op.get("children", []):
        lines += _fmt(c, depth + 1)
    return lines


def _to_dict(p):
    if p is None:
        return {}
    if isinstance(p, dict):
        return p
    return {"operatorType": p.operator_type, "args": dict(p.arguments),
            "children": [_to_dict(c) for c in p.children]}


def neo_plans():
    with neo_driver().session(database=NEO4J_DATABASE) as s:
        for name, q, p in plan_cases():
            cypher = Q.cypher_for(q, p)
            summary = s.run("PROFILE " + cypher, Q.neo_params(q, p)).consume()
            prof = _to_dict(summary.profile)
            text = "\n".join(_fmt(prof))
            total = prof.get("args", {}).get("GlobalMemory", "")
            out = PLANS / f"neo_{name}.txt"
            out.write_text(cypher.strip() + "\n\n" + text + f"\n\nGlobalMemory={total}\n")
            print(f"--- {out.name}\n{text[:1500]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["pg", "neo"])
    a = ap.parse_args()
    PLANS.mkdir(parents=True, exist_ok=True)
    if "pg" in a.engines:
        pg_plans()
    if "neo" in a.engines:
        neo_plans()
    close()

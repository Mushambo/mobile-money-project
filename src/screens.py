"""Screenshot helper: prints SQL and Cypher results side by side for each report section.
Run from the project root with both databases running, e.g.

    python src\\screens.py q1        (4.1)   python src\\screens.py q5   (5.2)
    python src\\screens.py q2        (4.2)   python src\\screens.py q6   (5.3)
    python src\\screens.py q3        (4.3)   python src\\screens.py q7   (5.4)
    python src\\screens.py q4        (5.1)   python src\\screens.py plans (6.2/6.3)

Maximise the PowerShell window before taking the screenshot.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402
from db import close, normalize, run_neo, run_pg  # noqa: E402
import queries as Q  # noqa: E402

CAT = ZoneInfo("Africa/Kigali")


def both(q, p):
    sql = normalize(run_pg(Q.sql_for(q, p, improved_q7=True), Q.pg_params(q, p), timeout_s=300))
    cy = normalize(run_neo(Q.cypher_for(q, p), Q.neo_params(q, p), timeout_s=300))
    return sql, cy


def ok(a, b):
    return "MATCH" if a == b else "MISMATCH"


def cat(ts):
    return datetime.fromtimestamp(ts, CAT).strftime("%Y-%m-%d %H:%M:%S")


def header(title):
    print("=" * 100)
    print(title)
    print("=" * 100)


def q1():
    header("Q1 Account activity, 09:45-10:45 CAT (outgoing count, total RWF)")
    print(f"{'Set':4}{'Account':>9}{'Day':>6}   {'SQL (count, RWF)':28}{'Cypher (count, RWF)':28}Status")
    for s, (acc, _, day) in Q.SETS.items():
        a, b = both("Q1", Q.set_params(s))
        print(f"{s:4}{acc:>9}{day:>4} Sep  {str(a[0]):28}{str(b[0]):28}{ok(a, b)}")


def q2():
    header("Q2 Daily activity by CAT date: SQL vs Cypher")
    a, b = both("Q2", {})
    print(f"{'CAT date':12}{'SQL count':>11}{'SQL RWF':>16}   {'Cypher count':>12}{'Cypher RWF':>16}  Status")
    for x, y in zip(a, b):
        print(f"{x[0]:12}{x[1]:>11,}{x[2]:>16,}   {y[1]:>12,}{y[2]:>16,}  {ok(x, y)}")
    audit = json.loads((RESULTS_DIR / "capture_audit.json").read_text())["transfer_audit"]
    n, v = sum(r[1] for r in a), sum(r[2] for r in a)
    print(f"\nRows: SQL {len(a)}, Cypher {len(b)}  -> {ok(a, b)}")
    print(f"Reconciliation: sum of daily counts {n:,} vs capture {audit['transfer_count']:,} -> "
          f"{'OK' if n == audit['transfer_count'] else 'DIFFERENT'}")
    print(f"                sum of daily values {v:,} vs capture {audit['sum_amount_rwf']:,} RWF -> "
          f"{'OK' if v == audit['sum_amount_rwf'] else 'DIFFERENT'}")


def q3():
    header("Q3 Shared devices with overlapping observation days")
    for s, (acc, _, _) in Q.SETS.items():
        a, b = both("Q3", Q.set_params(s))
        print(f"\nSet {s}  account {acc}:  SQL rows {len(a)}, Cypher rows {len(b)}  -> {ok(a, b)}")
        print(f"   {'other_account':>14}{'device':>9}  {'access_type':16}{'overlap days':>14}")
        for r in a:
            print(f"   {r[0]:>14}{r[1]:>9}  {r[2]:16}{f'[{r[3]}, {r[4]}]':>14}")


def q4():
    header("Q4 Accounts reached through OWNS / USED_DEVICE links, by owner region")
    print(f"{'Set':4}{'Links':>6}{'SQL total':>11}{'Cypher total':>14}  {'SQL by region':60}Status")
    for s in Q.SETS:
        for d in Q.Q4_DEPTHS:
            a, b = both("Q4", {**Q.set_params(s), "depth": d})
            regions = ", ".join(f"{r[0][:3]} {r[1]}" for r in a)
            print(f"{s:4}{d:>6}{sum(r[1] for r in a):>11}{sum(r[1] for r in b):>14}  {regions:60}{ok(a, b)}")
    print("\nOne supporting path from Neo4j (set A, account 998 -> account 24751, at most 4 links):")
    for path, links in run_neo(Q.Q4_PATH_CYPHER_TEMPLATE.format(depth=4), {"account": 998, "other": 24751}):
        print("   " + "  -  ".join(path) + f"   ({links} links)")


def _transfers(ids):
    rows = run_pg("SELECT transfer_id, sender_id, receiver_id, occurred_at, amount_rwf FROM transfers "
                  "WHERE transfer_id = ANY(%(i)s) ORDER BY occurred_at", {"i": list(ids)})
    for t in rows:
        print(f"   #{t[0]}  {t[1]:>7} -> {t[2]:<7}  {cat(t[3])} CAT  {t[4]:>10,} RWF")


def q5():
    header("Q5 Rapid onward chains (3 transfers, gaps <= 600 s, amounts 90-105 %)")
    for s, (acc, _, day) in Q.SETS.items():
        a, b = both("Q5", Q.set_params(s))
        print(f"Set {s}  account {acc:>6}, {day} Sep:  SQL chains {len(a)}, Cypher chains {len(b)}  -> {ok(a, b)}"
              + (f"   {a}" if a else ""))
    print("\nSet B chain in detail:")
    a, _ = both("Q5", Q.set_params("B"))
    _transfers(a[0][:3])


def q6():
    header("Q6 Circular payments (3-8 transfers back to the start, <= 30 min, amounts 90-105 %)")
    for s, (acc, _, day) in Q.SETS.items():
        a, b = both("Q6", Q.set_params(s))
        print(f"Set {s}  account {acc:>6}, {day} Sep:  SQL cycles {len(a)}, Cypher cycles {len(b)}  -> {ok(a, b)}"
              + (f"   {[list(r[0]) for r in a]}" if a else ""))
    print("\nSet A cycle in detail:")
    a, _ = both("Q6", Q.set_params("A"))
    _transfers(a[0][0])


def q7():
    from compare import verify_path_sql
    header("Q7 Shortest person-only transfer connection (length only), bounds 4 and 6")
    print(f"{'Set':4}{'From':>8}{'To':>8}{'Bound':>6}{'SQL':>7}{'Cypher':>8}  Status   Neo4j path (checked hop by hop)")
    for s, (acc, dest, _) in Q.SETS.items():
        for bnd in Q.Q7_BOUNDS:
            p = {**Q.set_params(s), "bound": bnd}
            a, b = both("Q7", p)
            L = a[0][0]
            path = "no route within bound"
            if L is not None:
                acc_path, _tids = run_neo(Q.q7_path_cypher(bnd), {"account": acc, "dest": dest})[0]
                v = verify_path_sql(acc_path, L)
                path = " -> ".join(map(str, acc_path)) + ("   VALID" if v["valid"] else "   INVALID")
            print(f"{s:4}{acc:>8}{dest:>8}{bnd:>6}{str(L):>7}{str(b[0][0]):>8}  {ok(a, b):8} {path}")


def plans():
    header("Execution summaries of the saved plans (results/plans)")
    for f in sorted((RESULTS_DIR / "plans").glob("*.txt")):
        lines = [l for l in f.read_text().splitlines()
                 if "Execution Time" in l or "Recursive Union" in l or "rows=" in l and "loops" in l]
        print(f"\n--- {f.name}")
        for l in lines[:6]:
            print("   " + l.strip()[:150])


if __name__ == "__main__":
    cmds = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6, "q7": q7, "plans": plans}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(1)
    try:
        cmds[sys.argv[1]]()
    finally:
        close()

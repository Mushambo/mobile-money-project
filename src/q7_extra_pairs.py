"""Section 8.3 check: does the Q7 result hold for more review pairs?
Times Q7 (bound 6) on 10 extra person-to-person pairs: the baseline SQL once per pair
(it is slow, 60 s limit), the improved SQL and Neo4j with 1 warm-up and 5 runs each. Pairs are chosen with a fixed seed so the run can be repeated.

    python src\\q7_extra_pairs.py --engine pg      (only PostgreSQL running)
    python src\\q7_extra_pairs.py --engine neo     (only Neo4j running)
    python src\\q7_extra_pairs.py --summary        (prints the comparison)
"""
import argparse
import csv
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402
from db import close, run_neo, run_pg  # noqa: E402
import queries as Q  # noqa: E402

OUT = RESULTS_DIR / "q7_extra_pairs.csv"
BOUND, RUNS, LIMIT = 6, 5, 60


def pairs(n=10, seed=2026):
    rng = random.Random(seed)
    return [(rng.randint(1, 240_000), rng.randint(1, 240_000)) for _ in range(n)]


def timed(fn, runs=RUNS):
    out = []
    for _ in range(runs):
        t = time.perf_counter()
        try:
            rows = fn()
            out.append(((time.perf_counter() - t) * 1000, rows[0][0]))
        except Exception:
            out.append((None, "timeout"))
            close()
    return out


def run(engine):
    variants = ([("pg-baseline", Q.Q7_SQL), ("pg-improved", Q.Q7_SQL_IMPROVED)] if engine == "pg"
                else [("neo", None)])
    new = not OUT.exists()
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["variant", "account", "dest", "length", "median_ms", "completed"])
        for a, d in pairs():
            p = {"account": a, "dest": d, "bound": BOUND}
            for name, sql in variants:
                if sql:
                    fn = lambda: run_pg(sql, p, timeout_s=LIMIT)  # noqa: E731
                else:
                    fn = lambda: run_neo(Q.q7_cypher(BOUND), {"account": a, "dest": d}, timeout_s=LIMIT)  # noqa: E731
                if name == "pg-baseline":
                    res = timed(fn, runs=1)                     # slow: one timed run only
                else:
                    timed(fn, runs=1)                           # one warm-up
                    res = timed(fn)
                ok = [ms for ms, _ in res if ms is not None]
                length = next((L for ms, L in res if ms is not None), "timeout")
                med = round(statistics.median(ok), 3) if ok else ""
                w.writerow([name, a, d, length, med, len(ok)])
                print(f"{name:12} {a:>7} -> {d:<7} length={length!s:8} median={med} ms  ok={len(ok)}/{len(res)}", flush=True)
    close()


def summary():
    rows = list(csv.DictReader(open(OUT)))
    by = {}
    for r in rows:
        by.setdefault((r["account"], r["dest"]), {})[r["variant"]] = r
    print(f"{'pair':>17}  {'length':>6} {'baseline ms':>12} {'improved ms':>12} {'neo ms':>9}  same length")
    for (a, d), v in by.items():
        lens = {x["length"] for x in v.values() if x["length"] != "timeout"}
        g = lambda k: "-" if k not in v else (v[k]["median_ms"] or "timeout")  # noqa: E731
        print(f"{a:>7}->{d:<9} {'/'.join(sorted(lens)) or '-':>6} {g('pg-baseline'):>12} {g('pg-improved'):>12} "
              f"{g('neo'):>9}  {'yes' if len(lens) <= 1 else 'NO'}")
    for k in ("pg-baseline", "pg-improved", "neo"):
        ms = [float(r["median_ms"]) for r in rows if r["variant"] == k and r["median_ms"]]
        to = sum(1 for r in rows if r["variant"] == k and not r["median_ms"])
        if ms or to:
            print(f"{k:12} median of pair medians {statistics.median(ms) if ms else '-'} ms, timeouts {to}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["pg", "neo"])
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    summary() if a.summary else run(a.engine)

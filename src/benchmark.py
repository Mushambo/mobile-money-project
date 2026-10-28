"""Sections 6.2 / 6.3 - time the fixed selection on ONE engine at a time.

Run with only the engine under test started (stop the other service first):
    python src/benchmark.py --engine pg  --sql-q7 baseline        # 21 PostgreSQL cases
    python src/benchmark.py --engine neo                           # 21 Neo4j cases
    python src/benchmark.py --engine pg  --sql-q7 improved --only Q7   # 4 revised SQL cases (6.3)
    python src/benchmark.py --summarize                            # medians, min, max, ratios

Per case: 3 untimed warm-ups (180 s limit) then 5 measured runs (60 s limit), timed with
perf_counter from submission to receipt of the final row. Errors and timeouts are recorded
with their status and never counted as completed timings. Answers are compared with
results/reference_answers.json AFTER the timed loop.
"""
import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402
from db import close, normalize, run_neo, run_pg  # noqa: E402
import queries as Q  # noqa: E402

CAT = ZoneInfo("Africa/Kigali")
RAW = RESULTS_DIR / "benchmark_raw.csv"
FIELDS = ["variant", "engine", "case", "question", "set", "params", "run_type", "run", "start_cat",
          "duration_ms", "rows", "status", "correct"]
WARMUPS, MEASURED, WARM_LIMIT, RUN_LIMIT = 3, 5, 180, 60


def timed_cases():
    """21 cases: Q1/Q3/Q5/Q6 B,E; Q2 month; Q4 B,E x 4 depths; Q7 B,E x 2 bounds."""
    out = []
    for cid, q, s, p in Q.cases():
        if q == "Q2" or s in ("B", "E"):
            out.append((cid, q, s, p))
    return out


def classify(exc):
    text = f"{type(exc).__name__} {exc}".lower()
    return "timeout" if any(k in text for k in ("timeout", "timed out", "cancel", "terminated")) else "error"


def bench(engine, variant, only):
    improved = variant == "pg-improved"
    ref_file = RESULTS_DIR / "reference_answers.json"
    ref = json.loads(ref_file.read_text()) if ref_file.exists() else {}
    new = not RAW.exists()
    with open(RAW, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        for cid, q, s, p in timed_cases():
            if only and q not in only:
                continue
            if engine == "pg":
                query, params = Q.sql_for(q, p, improved), Q.pg_params(q, p)
                call = lambda lim: run_pg(query, params, timeout_s=lim)  # noqa: E731
            else:
                query, params = Q.cypher_for(q, p), Q.neo_params(q, p)
                call = lambda lim: run_neo(query, params, timeout_s=lim)  # noqa: E731
            measured = []
            for run_type, n, lim in (("warmup", WARMUPS, WARM_LIMIT), ("measured", MEASURED, RUN_LIMIT)):
                for i in range(1, n + 1):
                    start_cat = datetime.now(CAT).isoformat(timespec="milliseconds")
                    start = perf_counter()
                    try:
                        rows = call(lim)                     # wrapper consumes every row
                        dur = perf_counter() - start
                        status, nrows = "ok", len(rows)
                    except Exception as e:
                        dur, status, nrows, rows = perf_counter() - start, classify(e), "", None
                        close()                                # reset the session after a failure
                    rec = dict(variant=variant, engine=engine, case=cid, question=q, set=s,
                               params=json.dumps(params), run_type=run_type, run=i, start_cat=start_cat,
                               duration_ms=round(dur * 1000, 3) if status == "ok" else "",
                               rows=nrows, status=status, correct="")
                    measured.append((rec, rows))
            # correctness outside the timer
            for rec, rows in measured:
                if rows is not None and cid in ref:
                    exp = normalize([tuple(r) if isinstance(r, list) else r for r in ref[cid]])
                    rec["correct"] = normalize(rows) == exp
                w.writerow(rec)
            f.flush()
            ok = [r["duration_ms"] for r, _ in measured if r["run_type"] == "measured" and r["status"] == "ok"]
            bad = [r["status"] for r, _ in measured if r["status"] != "ok"]
            print(f"{variant:12s} {cid:12s} median={statistics.median(ok) if ok else '-':>10} ms "
                  f"ok={len(ok)}/5 {('failures: ' + ','.join(bad)) if bad else ''}", flush=True)
    close()


def summarize():
    rows = list(csv.DictReader(open(RAW)))
    groups = {}
    for r in rows:
        if r["run_type"] != "measured":
            continue
        groups.setdefault((r["variant"], r["case"]), []).append(r)
    summary = []
    for (variant, case), rs in sorted(groups.items()):
        ok = [float(r["duration_ms"]) for r in rs if r["status"] == "ok"]
        summary.append(dict(variant=variant, case=case, completed=len(ok),
                            timeouts=sum(r["status"] == "timeout" for r in rs),
                            errors=sum(r["status"] == "error" for r in rs),
                            all_correct=all(r["correct"] == "True" for r in rs if r["status"] == "ok"),
                            median_ms=round(statistics.median(ok), 3) if ok else "",
                            min_ms=round(min(ok), 3) if ok else "", max_ms=round(max(ok), 3) if ok else ""))
    med = {(s["variant"], s["case"]): s["median_ms"] for s in summary}
    for s in summary:
        if s["variant"].startswith("pg"):
            n = med.get(("neo", s["case"]))
            s["pg_over_neo_median_ratio"] = round(s["median_ms"] / n, 3) if n and s["median_ms"] != "" else ""
    with open(RESULTS_DIR / "benchmark_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for s in summary for k in s)))
        w.writeheader(); w.writerows(summary)
    for s in summary:
        print(s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["pg", "neo"])
    ap.add_argument("--sql-q7", default="baseline", choices=["baseline", "improved"])
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args()
    if a.summarize:
        summarize()
    else:
        variant = "neo" if a.engine == "neo" else ("pg-improved" if a.sql_q7 == "improved" else "pg")
        bench(a.engine, variant, a.only)

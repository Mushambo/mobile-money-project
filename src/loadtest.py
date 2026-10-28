"""Section 7.1 - concurrent analysts. One engine at a time (stop the other service).

    python src/loadtest.py --engine pg          # uses the SQL version selected in 6.3 (improved Q7)
    python src/loadtest.py --engine neo
    python src/loadtest.py --summarize          # medians over the 3 repetitions

Workloads: q4d10 = Q4 depth 10; q7b6 = Q7 length-only bound 6. Each client cycles A-B-C.
Clients 1, 4, 8, 16; 3 repetitions each. Every client process owns one persistent
connection, warms up A-B-C once, then waits on a Barrier. At release a common start time
is set; clients start cycles until start+15 s, finish any started cycle and submit each next
request immediately. 60 s per-query timeout. Correctness is checked after timing.
"""
import argparse
import csv
import json
import math
import multiprocessing as mp
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402

CLIENTS = (1, 4, 8, 16)
REPS = 3
WINDOW_S = 15
TIMEOUT_S = 60
SETS = ("A", "B", "C")
RAW = RESULTS_DIR / "loadtest_requests.csv"
SUMMARY = RESULTS_DIR / "loadtest_summary.csv"
REP_SUMMARY = RESULTS_DIR / "loadtest_repetitions.csv"

_start_value = None


def _mark_start():                      # Barrier action: runs once at release
    _start_value.value = time.time()


def _init(v):
    global _start_value
    _start_value = v


def _request(engine, workload, s):
    import queries as Q
    from db import run_neo, run_pg
    p = Q.set_params(s)
    if workload == "q4d10":
        p = {**p, "depth": 10}; q = "Q4"
    else:
        p = {**p, "bound": 6}; q = "Q7"
    if engine == "pg":
        return run_pg(Q.sql_for(q, p, improved_q7=True), Q.pg_params(q, p), timeout_s=TIMEOUT_S)
    return run_neo(Q.cypher_for(q, p), Q.neo_params(q, p), timeout_s=TIMEOUT_S)


def client(cid, engine, workload, barrier, out_q):
    from db import close
    for s in SETS:                                  # warm-up A-B-C once (also opens the connection)
        _request(engine, workload, s)
    barrier.wait()
    start = _start_value.value
    deadline = start + WINDOW_S
    log, cycle = [], 0
    while time.time() < deadline:                   # only START cycles before the deadline
        cycle += 1
        for s in SETS:                              # a started cycle is always finished
            t_wall = time.time()
            t0 = time.perf_counter()
            try:
                rows = _request(engine, workload, s)
                status = "ok"
            except Exception as e:
                rows = None
                text = f"{type(e).__name__} {e}".lower()
                status = "timeout" if ("timeout" in text or "cancel" in text) else "error"
                close()
            lat = time.perf_counter() - t0
            log.append(dict(client=cid, cycle=cycle, set=s, offset_s=round(t_wall - start, 4),
                            end_offset_s=round(time.time() - start, 4), latency_ms=round(lat * 1000, 3),
                            status=status, rows=json.dumps(rows, default=str) if rows is not None else ""))
    close()
    out_q.put(log)


def expected_answers():
    import queries as Q
    from db import normalize
    ref = json.loads((RESULTS_DIR / "reference_answers.json").read_text())
    exp = {}
    for s in SETS:
        exp[("q4d10", s)] = normalize([tuple(r) for r in ref[f"Q4-{s}-d10"]])
        exp[("q7b6", s)] = normalize([tuple(r) for r in ref[f"Q7-{s}-b6"]])
    return exp


def p95(values):
    v = sorted(values)
    return v[math.ceil(0.95 * len(v)) - 1] if v else None


def run(engine):
    from db import normalize
    exp = expected_answers()
    new = not RAW.exists()
    rawf = open(RAW, "a", newline="")
    w = csv.DictWriter(rawf, fieldnames=["engine", "workload", "clients", "rep", "client", "cycle", "set",
                                         "offset_s", "end_offset_s", "latency_ms", "status", "correct"])
    if new:
        w.writeheader()
    reps = []
    for workload in ("q4d10", "q7b6"):
        for n in CLIENTS:
            for rep in range(1, REPS + 1):
                start_v = mp.Value("d", 0.0)
                barrier = mp.Barrier(n, action=_mark_start)
                out_q = mp.Queue()
                procs = [mp.Process(target=_proc_entry, args=(i, engine, workload, barrier, out_q, start_v))
                         for i in range(n)]
                for pr in procs:
                    pr.start()
                logs = [out_q.get() for _ in procs]
                errs = [lg["__error__"] for lg in logs if isinstance(lg, dict)]
                if errs:
                    for pr in procs:
                        pr.terminate()
                    raise SystemExit("Load test stopped - a client could not run:\n  " + "\n  ".join(errs[:3])
                                     + "\nCheck that the database for this engine is running and .env is correct.")
                for pr in procs:
                    pr.join()
                reqs = [r for lg in logs for r in lg]
                # correctness after timing
                for r in reqs:
                    if r["status"] == "ok":
                        rows = [tuple(x) for x in json.loads(r["rows"])]
                        r["correct"] = normalize(rows) == exp[(workload, r["set"])]
                    else:
                        r["correct"] = False
                    del r["rows"]
                    w.writerow(dict(engine=engine, workload=workload, clients=n, rep=rep, **r))
                rawf.flush()
                elapsed = max(r["end_offset_s"] for r in reqs)          # release -> final cycle finished
                good = [r for r in reqs if r["status"] == "ok" and r["correct"]]
                lats = [r["latency_ms"] for r in reqs if r["status"] == "ok"]
                rec = dict(engine=engine, workload=workload, clients=n, rep=rep, requests=len(reqs),
                           correct=len(good), elapsed_s=round(elapsed, 3),
                           throughput_rps=round(len(good) / elapsed, 3),
                           median_ms=round(statistics.median(lats), 3) if lats else "",
                           p95_ms=round(p95(lats), 3) if lats else "",
                           errors=sum(r["status"] == "error" for r in reqs),
                           timeouts=sum(r["status"] == "timeout" for r in reqs),
                           incorrect=sum(r["status"] == "ok" and not r["correct"] for r in reqs))
                reps.append(rec)
                print(rec, flush=True)
    rawf.close()
    new = not REP_SUMMARY.exists()
    with open(REP_SUMMARY, "a", newline="") as f:
        w2 = csv.DictWriter(f, fieldnames=list(reps[0]))
        if new:
            w2.writeheader()
        w2.writerows(reps)


def _proc_entry(i, engine, workload, barrier, out_q, start_v):
    _init(start_v)
    try:
        client(i, engine, workload, barrier, out_q)
    except Exception as e:            # report instead of leaving the parent waiting forever
        barrier.abort()
        out_q.put({"__error__": f"client {i}: {type(e).__name__}: {e}"})


def summarize():
    rows = list(csv.DictReader(open(REP_SUMMARY)))
    groups = {}
    for r in rows:
        groups.setdefault((r["engine"], r["workload"], int(r["clients"])), []).append(r)
    out = []
    for (e, wl, n), rs in sorted(groups.items()):
        med = lambda k: statistics.median(float(r[k]) for r in rs if r[k] != "")  # noqa: E731
        out.append(dict(engine=e, workload=wl, clients=n, reps=len(rs), throughput_rps=round(med("throughput_rps"), 3),
                        median_ms=round(med("median_ms"), 3), p95_ms=round(med("p95_ms"), 3),
                        errors=int(med("errors")), timeouts=int(med("timeouts")), incorrect=int(med("incorrect"))))
    with open(SUMMARY, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    for o in out:
        print(o)


if __name__ == "__main__":
    mp.freeze_support()
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["pg", "neo"])
    ap.add_argument("--summarize", action="store_true")
    a = ap.parse_args()
    summarize() if a.summarize else run(a.engine)

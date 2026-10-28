"""Section 6.1 - run all 61 cases on PostgreSQL and Neo4j and compare exactly.

Usage:
    python src/compare.py                 # both engines (+ reference answers if present)
    python src/compare.py --engines pg    # PostgreSQL only (e.g. before Neo4j is loaded)
    python src/compare.py --sql-q7 improved   # use the Section 6.3 SQL version for Q7

Outputs: results/compare_status.csv (status table), results/compare_full_outputs.json
(every row from every engine), results/q7_path_checks.json (supporting-path checks).
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402
from db import close, normalize, run_neo, run_pg  # noqa: E402
import queries as Q  # noqa: E402


def verify_path_sql(accounts, length):
    """Check IDs, direction, roles, event existence and length of one account path."""
    hops = run_pg(Q.Q7_VERIFY_SQL, {"path": list(accounts)})
    ok_len = len(hops) == length == len(accounts) - 1
    ok_events = all(h[3] is not None for h in hops)
    ok_roles = all(h[4] == "person" and h[5] == "person" for h in hops)
    ok_chain = all(hops[i][2] == hops[i + 1][1] for i in range(len(hops) - 1))
    return dict(accounts=list(accounts), hops=[list(h) for h in hops], length_ok=ok_len,
                events_exist=ok_events, all_person=ok_roles, contiguous=ok_chain,
                valid=ok_len and ok_events and ok_roles and ok_chain)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["pg", "neo"], choices=["pg", "neo"])
    ap.add_argument("--sql-q7", default="improved", choices=["baseline", "improved"])
    a = ap.parse_args()
    improved = a.sql_q7 == "improved"

    ref_path = RESULTS_DIR / "reference_answers.json"
    ref = json.loads(ref_path.read_text()) if ref_path.exists() else {}

    status, full, path_checks = [], {}, {}
    for cid, q, s, p in Q.cases():
        rec = {"case": cid, "question": q, "set": s}
        outs = {}
        for eng in a.engines:
            t = time.perf_counter()
            try:
                if eng == "pg":
                    rows = run_pg(Q.sql_for(q, p, improved), Q.pg_params(q, p), timeout_s=180)
                else:
                    rows = run_neo(Q.cypher_for(q, p), Q.neo_params(q, p), timeout_s=180)
                outs[eng] = normalize(rows)
                rec[f"{eng}_rows"] = len(rows)
                rec[f"{eng}_status"] = "ok"
            except Exception as e:                       # recorded, never hidden
                outs[eng] = None
                rec[f"{eng}_rows"] = ""
                rec[f"{eng}_status"] = f"error: {type(e).__name__}: {str(e)[:120]}"
            rec[f"{eng}_seconds"] = round(time.perf_counter() - t, 3)
        if cid in ref:
            outs["ref"] = normalize([tuple(r) if isinstance(r, list) else r for r in ref[cid]])
        ok = [v for k, v in outs.items() if v is not None]
        rec["engines_match"] = (len(a.engines) == 2 and outs.get("pg") is not None
                                and outs.get("pg") == outs.get("neo"))
        rec["pg_matches_reference"] = "ref" in outs and outs.get("pg") == outs["ref"]
        if "neo" in a.engines:
            rec["neo_matches_reference"] = "ref" in outs and outs.get("neo") == outs["ref"]
        rec["status"] = "MATCH" if ok and all(v == ok[0] for v in ok) and len(ok) == len(outs) else "MISMATCH"
        full[cid] = {"params": p, **{k: v for k, v in outs.items()}}

        # Q7: lengths compared above; supporting paths verified separately
        if q == "Q7" and outs.get("pg") and outs["pg"][0][0] is not None:
            L = outs["pg"][0][0]
            checks = {}
            sql_path = run_pg(Q.Q7_PATH_SQL, {"account": p["account"], "dest": p["dest"], "len": L})
            if sql_path:
                checks["pg_path"] = verify_path_sql(sql_path[0][0], L)
            if "neo" in a.engines:
                try:
                    neo_path = run_neo(Q.q7_path_cypher(p["bound"]),
                                       {"account": p["account"], "dest": p["dest"]}, timeout_s=180)
                    if neo_path:
                        accounts, tids = neo_path[0]
                        checks["neo_path"] = verify_path_sql(accounts, L)
                        checks["neo_path"]["transfer_ids"] = list(tids)
                except Exception as e:
                    checks["neo_path"] = {"valid": False, "error": str(e)[:200]}
            path_checks[cid] = checks
            rec["paths_valid"] = all(c.get("valid") for c in checks.values())
        print(f"{cid:12s} {rec['status']:8s} " +
              " ".join(f"{e}={rec.get(e + '_rows')}/{rec.get(e + '_seconds')}s" for e in a.engines) +
              (f" paths_valid={rec['paths_valid']}" if "paths_valid" in rec else ""), flush=True)
        status.append(rec)

    RESULTS_DIR.mkdir(exist_ok=True)
    fields = sorted({k for r in status for k in r}, key=lambda k: (k not in ("case", "question", "set", "status"), k))
    with open(RESULTS_DIR / "compare_status.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(status)
    (RESULTS_DIR / "compare_full_outputs.json").write_text(json.dumps(full, indent=1, default=str))
    (RESULTS_DIR / "q7_path_checks.json").write_text(json.dumps(path_checks, indent=1, default=str))
    n_ok = sum(r["status"] == "MATCH" for r in status)
    print(f"\n{n_ok}/{len(status)} cases MATCH  (engines: {', '.join(a.engines)}"
          f"{', reference' if ref else ''}; SQL Q7 = {a.sql_q7})")
    close()


if __name__ == "__main__":
    main()

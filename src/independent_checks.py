"""Section 6.1.2 - check one device overlap and one chain/cycle directly against the
captured CSV rows (plain csv module, streaming; no database involved).

Usage:  python src/independent_checks.py
        python src/independent_checks.py --account 998 --other 220998 --device 998 \
            --cycle 20000001 20000002 20000003 20000004 --chain 20000001 20000002 20000003
"""
import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, RESULTS_DIR  # noqa: E402
from queries import SETS, hour_bounds  # noqa: E402

CAT = ZoneInfo("Africa/Kigali")


def overlap_check(account, other, device):
    rows = {}
    with open(DATA_DIR / "account_devices.csv", newline="") as f:
        for r in csv.DictReader(f):
            if int(r["device_id"]) == device and int(r["account_id"]) in (account, other):
                rows[int(r["account_id"])] = {k: int(v) for k, v in r.items()}
    a, o = rows[account], rows[other]
    s, e = max(a["first_day"], o["first_day"]), min(a["last_day"], o["last_day"])
    return dict(rows=[a, o], overlap_start=s, overlap_end=e, overlaps=s <= e)


def fetch_transfers(ids):
    want, found = set(ids), {}
    with open(DATA_DIR / "transfers.csv", newline="") as f:
        for r in csv.DictReader(f):
            tid = int(r["transfer_id"])
            if tid in want:
                found[tid] = {k: int(v) for k, v in r.items()}
                if len(found) == len(want):
                    break
    return [found[i] for i in ids]


def sequence_check(ids, account, start, end, kind):
    ts = fetch_transfers(ids)
    for t in ts:
        t["occurred_cat"] = datetime.fromtimestamp(t["occurred_at"], CAT).isoformat()
    checks = {
        "starts_at_review_account": ts[0]["sender_id"] == account,
        "first_in_hour": start <= ts[0]["occurred_at"] < end,
        "linked_receiver_to_sender": all(ts[i]["receiver_id"] == ts[i + 1]["sender_id"] for i in range(len(ts) - 1)),
        "strictly_increasing_time": all(ts[i]["occurred_at"] < ts[i + 1]["occurred_at"] for i in range(len(ts) - 1)),
        "amount_rule_90_105": all(90 * ts[i]["amount_rwf"] <= 100 * ts[i + 1]["amount_rwf"] <= 105 * ts[i]["amount_rwf"]
                                  for i in range(len(ts) - 1)),
    }
    if kind == "chain":
        checks["gaps_at_most_600s"] = all(ts[i + 1]["occurred_at"] - ts[i]["occurred_at"] <= 600 for i in range(len(ts) - 1))
        checks["four_distinct_accounts"] = len({ts[0]["sender_id"]} | {t["receiver_id"] for t in ts}) == 4
    else:
        checks["returns_to_start"] = ts[-1]["receiver_id"] == account
        checks["no_earlier_return"] = all(t["receiver_id"] != account for t in ts[:-1])
        checks["all_in_hour"] = all(start <= t["occurred_at"] < end for t in ts)
        checks["span_at_most_1800s"] = ts[-1]["occurred_at"] - ts[0]["occurred_at"] <= 1800
        checks["length_3_to_8"] = 3 <= len(ts) <= 8
    return dict(transfers=ts, checks=checks, all_pass=all(checks.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="A")
    ap.add_argument("--other", type=int, default=220998)
    ap.add_argument("--device", type=int, default=998)
    ap.add_argument("--chain", type=int, nargs="+", default=[20000001, 20000002, 20000003])
    ap.add_argument("--cycle", type=int, nargs="+", default=[20000001, 20000002, 20000003, 20000004])
    a = ap.parse_args()
    account, _, day = SETS[a.set]
    start, end = hour_bounds(day)
    out = {
        "overlap": overlap_check(account, a.other, a.device),
        "chain_Q5": sequence_check(a.chain, account, start, end, "chain"),
        "cycle_Q6": sequence_check(a.cycle, account, start, end, "cycle"),
    }
    print(json.dumps(out, indent=2))
    (RESULTS_DIR / "independent_checks.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

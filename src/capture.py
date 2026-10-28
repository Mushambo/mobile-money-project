"""Section 1.2 - capture the five generator streams to CSV.

Usage:
    python src/capture.py --preview     # 10 records per stream (screenshot)
    python src/capture.py               # full capture + audit (screenshot)

Rows are written progressively with csv.DictWriter; nothing is collected in memory.
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from pprint import pprint
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mobile_money_generator as g  # noqa: E402  (unchanged teaching module)
from config import DATA_DIR, RESULTS_DIR, STREAMS  # noqa: E402

CAT = ZoneInfo("Africa/Kigali")


def preview():
    pprint(g.dataset_info(), sort_dicts=False)
    pprint(g.FIELDS, sort_dicts=False)
    for name in STREAMS:
        print(f"\n--- iter_{name}() first 10 ---")
        stream = getattr(g, f"iter_{name}")()          # a fresh call restarts the stream
        for rec in islice(stream, 10):
            print(rec)


def capture():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    expected = g.dataset_info()["expected_counts"]
    summary = {"captured_at_cat": datetime.now(CAT).isoformat(timespec="seconds"), "streams": {}}
    audit = {"transfer_count": 0, "min_occurred_at": None, "max_occurred_at": None, "sum_amount_rwf": 0}
    grand_start = time.perf_counter()

    for name in STREAMS:
        path = DATA_DIR / f"{name}.csv"
        consumed = written = 0
        start = time.perf_counter()
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=g.FIELDS[name])
            writer.writeheader()
            for row in getattr(g, f"iter_{name}")():
                consumed += 1
                writer.writerow(row)
                written += 1
                if name == "transfers":
                    ts, amt = row["occurred_at"], row["amount_rwf"]
                    audit["transfer_count"] += 1
                    audit["sum_amount_rwf"] += amt
                    if audit["min_occurred_at"] is None or ts < audit["min_occurred_at"]:
                        audit["min_occurred_at"] = ts
                    if audit["max_occurred_at"] is None or ts > audit["max_occurred_at"]:
                        audit["max_occurred_at"] = ts
                    if written % 1_000_000 == 0:
                        print(f"  transfers: {written:>12,} written  "
                              f"{time.perf_counter() - start:8.1f} s", flush=True)
        secs = time.perf_counter() - start
        size = path.stat().st_size
        ok = consumed == written == expected[name]
        summary["streams"][name] = dict(consumed=consumed, written=written, expected=expected[name],
                                        match=ok, seconds=round(secs, 2), csv_bytes=size,
                                        csv_gb=round(size / 1e9, 4))
        print(f"{name:16s} consumed={consumed:>11,} written={written:>11,} expected={expected[name]:>11,} "
              f"{'OK' if ok else 'MISMATCH'}  {secs:8.1f} s  {size / 1e9:.4f} GB", flush=True)

    for k in ("min_occurred_at", "max_occurred_at"):
        audit[k.replace("occurred_at", "cat")] = datetime.fromtimestamp(audit[k], CAT).isoformat()
    summary["transfer_audit"] = audit
    summary["total_rows"] = sum(s["written"] for s in summary["streams"].values())
    summary["total_seconds"] = round(time.perf_counter() - grand_start, 2)
    summary["total_csv_gb"] = round(sum(s["csv_bytes"] for s in summary["streams"].values()) / 1e9, 4)

    print("\nTransfer audit:", json.dumps(audit, indent=2))
    print(f"Total rows {summary['total_rows']:,} (expected 20,993,500); "
          f"{summary['total_seconds']} s; {summary['total_csv_gb']} GB of CSV")
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "capture_audit.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved {RESULTS_DIR / 'capture_audit.json'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    preview() if a.preview else capture()

"""Section 3.2 - temporary Neo4j import copies with typed headers.

Source CSVs in data/ are left unchanged. Copies go to data/neo4j_import/ (IMPORT_DIR):
  customers.csv, accounts.csv, devices.csv        (nodes)
  owns.csv, used_device.csv, transfers.csv        (relationships)
Only the header line is replaced; data bytes are streamed across, never held in memory.
owns.csv is derived from accounts.csv in (customer_id, account_id) order.

Usage:  python src/prepare_import.py          (create copies)
        python src/prepare_import.py --clean  (remove copies after verification)
"""
import csv
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, IMPORT_DIR  # noqa: E402

# source file -> (import file, typed header).  Separate ID groups: Customer, Account, Device.
TYPED = {
    "customers.csv": ("customers.csv", "customer_id:ID(Customer),region:string"),
    "accounts.csv": ("accounts.csv", "account_id:ID(Account),:IGNORE,role:string"),
    "devices.csv": ("devices.csv", "device_id:ID(Device),access_type:string"),
    "account_devices.csv": ("used_device.csv",
                            ":START_ID(Account),:END_ID(Device),first_day:int,last_day:int,observations:int"),
    "transfers.csv": ("transfers.csv",
                      "transfer_id:long,:START_ID(Account),:END_ID(Account),occurred_at:long,amount_rwf:int"),
}
OWNS_HEADER = ":START_ID(Customer),:END_ID(Account)"


def copy_with_header(src: Path, dst: Path, header: str):
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        fin.readline()                                   # drop the plain header
        fout.write((header + "\n").encode())
        shutil.copyfileobj(fin, fout, length=16 * 1024 * 1024)


def write_owns():
    # 248,000 small pairs; sorting them is cheap and gives the required order.
    with open(DATA_DIR / "accounts.csv", newline="") as f:
        pairs = sorted((int(r["customer_id"]), int(r["account_id"])) for r in csv.DictReader(f))
    with open(IMPORT_DIR / "owns.csv", "w", newline="") as f:
        f.write(OWNS_HEADER + "\n")
        csv.writer(f, lineterminator="\n").writerows(pairs)
    return len(pairs)


def main():
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    for src, (dst, header) in TYPED.items():
        s = time.perf_counter()
        copy_with_header(DATA_DIR / src, IMPORT_DIR / dst, header)
        print(f"{src:20s} -> {dst:16s} {time.perf_counter() - s:6.1f} s   {header}")
    print(f"owns.csv rows: {write_owns():,}")
    for p in sorted(IMPORT_DIR.glob("*.csv")):
        with open(p) as f:
            print(f"  {p.name:16s} {p.stat().st_size / 1e9:.4f} GB  header: {f.readline().strip()}")
    print(f"Prepared in {time.perf_counter() - t0:.1f} s -> {IMPORT_DIR}")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        shutil.rmtree(IMPORT_DIR, ignore_errors=True)
        print(f"Removed temporary import copies in {IMPORT_DIR}")
    else:
        main()

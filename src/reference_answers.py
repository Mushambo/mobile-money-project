"""Independent reference answers for all 61 cases, computed in Python/pandas straight
from the captured CSVs (no database). Used to cross-check both engines and as the
Section 6.1 independent check. Needs about 2 GB RAM for the transfer columns.

Usage:  python src/reference_answers.py   -> results/reference_answers.json
"""
import json
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_DIR, RESULTS_DIR  # noqa: E402
from queries import cases  # noqa: E402

CAT_OFFSET = 2 * 3600  # Africa/Kigali has no DST


def load():
    t = pd.read_csv(DATA_DIR / "transfers.csv",
                    dtype=dict(transfer_id="int64", sender_id="int32", receiver_id="int32",
                               occurred_at="int64", amount_rwf="int64"))
    acc = pd.read_csv(DATA_DIR / "accounts.csv")
    cust = pd.read_csv(DATA_DIR / "customers.csv")
    ad = pd.read_csv(DATA_DIR / "account_devices.csv")
    dev = pd.read_csv(DATA_DIR / "devices.csv")
    return t, acc, cust, ad, dev


class Ref:
    def __init__(self):
        self.t, self.acc, self.cust, self.ad, self.dev = load()
        t = self.t.sort_values(["sender_id", "occurred_at"], kind="stable")
        self.by_sender = {k: g for k, g in t.groupby("sender_id", sort=False)}
        self.role = dict(zip(self.acc.account_id, self.acc.role))
        self.owner = dict(zip(self.acc.account_id, self.acc.customer_id))
        self.region = dict(zip(self.cust.customer_id, self.cust.region))
        self.access = dict(zip(self.dev.device_id, self.dev.access_type))
        # association graph (kind, id) both directions
        g = defaultdict(set)
        for a, c in zip(self.acc.account_id, self.acc.customer_id):
            g[("A", a)].add(("C", c)); g[("C", c)].add(("A", a))
        for a, d in zip(self.ad.account_id, self.ad.device_id):
            g[("A", a)].add(("D", d)); g[("D", d)].add(("A", a))
        self.assoc = g
        # distinct person->person neighbours
        pp = self.t[(self.t.sender_id <= 240_000) & (self.t.receiver_id <= 240_000)]
        pp = pp[pp.sender_id.map(self.role).eq("person") & pp.receiver_id.map(self.role).eq("person")]
        pairs = pp[["sender_id", "receiver_id"]].drop_duplicates().to_numpy()
        self.pnext = defaultdict(list)
        for s, r in pairs:
            self.pnext[int(s)].append(int(r))

    def out(self, account, lo=None, hi=None):
        g = self.by_sender.get(account)
        if g is None:
            return []
        if lo is not None:
            g = g[(g.occurred_at >= lo) & (g.occurred_at < hi)]
        return list(g.itertuples(index=False))

    def q1(self, p):
        rows = self.out(p["account"], p["start"], p["end"])
        return [(len(rows), int(sum(r.amount_rwf for r in rows)))]

    def q2(self, p):
        day = (self.t.occurred_at + CAT_OFFSET) // 86400
        g = self.t.groupby(day).amount_rwf.agg(["count", "sum"])
        import datetime as dt
        return [(dt.date.fromtimestamp(0).fromordinal(dt.date(1970, 1, 1).toordinal() + int(d)).isoformat(),
                 int(r["count"]), int(r["sum"])) for d, r in g.iterrows()]

    def q3(self, p):
        a = p["account"]
        mine = self.ad[self.ad.account_id == a]
        out = []
        for m in mine.itertuples(index=False):
            others = self.ad[(self.ad.device_id == m.device_id) & (self.ad.account_id != a)]
            for o in others.itertuples(index=False):
                s, e = max(m.first_day, o.first_day), min(m.last_day, o.last_day)
                if s <= e:
                    out.append((int(o.account_id), int(m.device_id), self.access[m.device_id], int(s), int(e)))
        return sorted(out)

    def q4(self, p):
        start = ("A", p["account"])
        seen, frontier = {start}, [start]
        for _ in range(p["depth"]):
            nxt = []
            for n in frontier:
                for m in self.assoc[n]:
                    if m not in seen:
                        seen.add(m); nxt.append(m)
            frontier = nxt
        counts = defaultdict(int)
        for k, i in seen:
            if k == "A" and i != p["account"]:
                counts[self.region[self.owner[i]]] += 1
        return sorted(counts.items())

    @staticmethod
    def _amount_ok(prev, nxt):
        return 90 * prev <= 100 * nxt <= 105 * prev

    def q5(self, p):
        a = p["account"]; res = []
        for t1 in self.out(a, p["start"], p["end"]):
            for t2 in self.out(t1.receiver_id, t1.occurred_at + 1, t1.occurred_at + 601):
                if not self._amount_ok(t1.amount_rwf, t2.amount_rwf):
                    continue
                for t3 in self.out(t2.receiver_id, t2.occurred_at + 1, t2.occurred_at + 601):
                    if not self._amount_ok(t2.amount_rwf, t3.amount_rwf):
                        continue
                    if len({a, t1.receiver_id, t2.receiver_id, t3.receiver_id}) == 4:
                        res.append((int(t1.transfer_id), int(t2.transfer_id), int(t3.transfer_id),
                                    int(t3.receiver_id)))
        return sorted(res)

    def q6(self, p):
        a, end = p["account"], p["end"]; res = []

        def extend(cur, ids, first, last, amt):
            if len(ids) >= 8:
                return
            for t in self.out(cur, last + 1, min(end, first + 1801)):
                if not self._amount_ok(amt, t.amount_rwf):
                    continue
                nids = ids + [int(t.transfer_id)]
                if t.receiver_id == a:
                    if len(nids) >= 3:
                        res.append((tuple(nids), len(nids)))
                    continue                                  # stop at first return
                extend(t.receiver_id, nids, first, t.occurred_at, t.amount_rwf)

        for t in self.out(a, p["start"], end):
            if t.receiver_id != a:
                extend(t.receiver_id, [int(t.transfer_id)], t.occurred_at, t.occurred_at, t.amount_rwf)
        return sorted(res)

    def q7(self, p):
        a, d, bound = p["account"], p["dest"], p["bound"]
        if self.role.get(a) != "person" or self.role.get(d) != "person":
            return [(None,)]
        dist = {a: 0}; q = deque([a])
        while q:
            n = q.popleft()
            if dist[n] >= bound:
                continue
            for m in self.pnext.get(n, ()):
                if m not in dist:
                    dist[m] = dist[n] + 1
                    if m == d:
                        return [(dist[m],)]
                    q.append(m)
        return [(None,)]


def main():
    t0 = time.perf_counter()
    ref = Ref()
    print(f"loaded in {time.perf_counter() - t0:.1f} s", flush=True)
    out = {}
    for cid, q, s, p in cases():
        out[cid] = getattr(ref, q.lower())(p)
        print(cid, str(out[cid])[:160], flush=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "reference_answers.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"done in {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()

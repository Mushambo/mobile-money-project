"""Section 3.3 - trace one account to its owner, a device and an outgoing transfer in both
models.   python src/trace_account.py --account 998 [--engines pg neo]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import close, run_neo, run_pg  # noqa: E402

TRACE_SQL = """
SELECT a.account_id, a.role, c.customer_id, c.region,
       ad.device_id, d.access_type, ad.first_day, ad.last_day, ad.observations,
       t.transfer_id, t.receiver_id, t.occurred_at, to_timestamp(t.occurred_at) AS occurred_cat, t.amount_rwf
FROM accounts a
JOIN customers c        ON c.customer_id = a.customer_id          -- FK accounts.customer_id
JOIN account_devices ad ON ad.account_id = a.account_id           -- FK account_devices.account_id
JOIN devices d          ON d.device_id = ad.device_id             -- FK account_devices.device_id
JOIN transfers t        ON t.sender_id = a.account_id             -- FK transfers.sender_id
WHERE a.account_id = %(account)s
ORDER BY ad.device_id, t.occurred_at, t.transfer_id
LIMIT 1
"""
TRACE_CYPHER = """
MATCH (c:Customer)-[:OWNS]->(a:Account {account_id:$account})-[u:USED_DEVICE]->(d:Device)
MATCH (a)-[t:TRANSFER]->(r:Account)
RETURN a.account_id, a.role, c.customer_id, c.region,
       d.device_id, d.access_type, u.first_day, u.last_day, u.observations,
       t.transfer_id, r.account_id, t.occurred_at,
       toString(datetime({epochSeconds:t.occurred_at, timezone:'Africa/Kigali'})) AS occurred_cat, t.amount_rwf
ORDER BY d.device_id, t.occurred_at, t.transfer_id
LIMIT 1
"""
REPEAT_SQL = """
SELECT sender_id, receiver_id, COUNT(*) AS transfers, MIN(occurred_at), MAX(occurred_at), SUM(amount_rwf)
FROM transfers WHERE sender_id = %(account)s GROUP BY 1, 2 HAVING COUNT(*) > 1 ORDER BY 3 DESC LIMIT 5
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", type=int, default=998)
    ap.add_argument("--engines", nargs="+", default=["pg", "neo"])
    a = ap.parse_args()
    cols = ["account_id", "role", "customer_id", "region", "device_id", "access_type", "first_day",
            "last_day", "observations", "transfer_id", "receiver_id", "occurred_at", "occurred_cat", "amount_rwf"]
    if "pg" in a.engines:
        print("PostgreSQL JOIN:")
        for k, v in zip(cols, run_pg(TRACE_SQL, {"account": a.account})[0]):
            print(f"  {k:13s} {v}")
        print("Repeated payments to the same receiver (would collapse into one edge):")
        for r in run_pg(REPEAT_SQL, {"account": a.account}):
            print("  ", r)
    if "neo" in a.engines:
        print("Neo4j MATCH:")
        for k, v in zip(cols, run_neo(TRACE_CYPHER, {"account": a.account})[0]):
            print(f"  {k:13s} {v}")
    close()


if __name__ == "__main__":
    main()

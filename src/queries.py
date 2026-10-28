"""Sections 4-6 - parameterized SQL/Cypher pairs for Q1-Q7 and the case list.

SQL uses psycopg %(name)s parameters; Cypher uses $name. Every query reads stored
base data only (no precomputed answers, no generator internals).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

CAT = ZoneInfo("Africa/Kigali")

# Review sets: (review account, destination, September day)
SETS = {
    "A": (998, 24755, 6),
    "B": (147228, 186823, 13),
    "C": (206978, 6573, 8),
    "D": (237998, 21755, 6),
    "E": (144228, 183823, 13),
    "F": (203978, 3573, 8),
}
Q4_DEPTHS = (4, 6, 8, 10)
Q7_BOUNDS = (4, 6)


def hour_bounds(day: int):
    """09:45:00 inclusive to 10:45:00 exclusive CAT on <day> September 2026, as epoch seconds."""
    start = int(datetime(2026, 9, day, 9, 45, tzinfo=CAT).timestamp())
    end = int(datetime(2026, 9, day, 10, 45, tzinfo=CAT).timestamp())
    return start, end


def set_params(name):
    account, dest, day = SETS[name]
    start, end = hour_bounds(day)
    return dict(account=account, dest=dest, start=start, end=end)


# --------------------------------------------------------------------------- Q1
Q1_SQL = """
SELECT COUNT(*) AS transfers, COALESCE(SUM(amount_rwf), 0) AS total_rwf
FROM transfers
WHERE sender_id = %(account)s
  AND occurred_at >= %(start)s AND occurred_at < %(end)s
"""
Q1_CYPHER = """
MATCH (a:Account {account_id:$account})
OPTIONAL MATCH (a)-[t:TRANSFER]->()
WHERE t.occurred_at >= $start AND t.occurred_at < $end
RETURN count(t) AS transfers, coalesce(sum(t.amount_rwf), 0) AS total_rwf
"""

# --------------------------------------------------------------------------- Q2
Q2_SQL = """
SELECT (to_timestamp(occurred_at) AT TIME ZONE 'Africa/Kigali')::date AS cat_date,
       COUNT(*) AS transfers, SUM(amount_rwf) AS total_rwf
FROM transfers
GROUP BY cat_date
ORDER BY cat_date
"""
Q2_CYPHER = """
MATCH ()-[t:TRANSFER]->()
WITH date(datetime({epochSeconds: t.occurred_at, timezone: 'Africa/Kigali'})) AS cat_date,
     t.amount_rwf AS amount
RETURN cat_date, count(*) AS transfers, sum(amount) AS total_rwf
ORDER BY cat_date
"""

# --------------------------------------------------------------------------- Q3
Q3_SQL = """
SELECT o.account_id AS other_account, o.device_id, d.access_type,
       GREATEST(r.first_day, o.first_day) AS overlap_start,
       LEAST(r.last_day, o.last_day)      AS overlap_end
FROM account_devices r
JOIN account_devices o ON o.device_id = r.device_id AND o.account_id <> r.account_id
JOIN devices d         ON d.device_id = r.device_id
WHERE r.account_id = %(account)s
  AND GREATEST(r.first_day, o.first_day) <= LEAST(r.last_day, o.last_day)
ORDER BY other_account, o.device_id
"""
Q3_CYPHER = """
MATCH (a:Account {account_id:$account})-[r:USED_DEVICE]->(d:Device)<-[o:USED_DEVICE]-(b:Account)
WHERE b <> a
WITH b, d,
     CASE WHEN r.first_day > o.first_day THEN r.first_day ELSE o.first_day END AS overlap_start,
     CASE WHEN r.last_day  < o.last_day  THEN r.last_day  ELSE o.last_day  END AS overlap_end
WHERE overlap_start <= overlap_end
RETURN b.account_id AS other_account, d.device_id AS device_id, d.access_type AS access_type,
       overlap_start, overlap_end
ORDER BY other_account, device_id
"""

# --------------------------------------------------------------------------- Q4
# Node kind is carried with the ID so Customer 7, Account 7 and Device 7 stay distinct.
Q4_SQL = """
WITH RECURSIVE edges(sk, si, dk, di) AS (
    SELECT 'Customer', customer_id, 'Account', account_id FROM accounts          -- OWNS
    UNION ALL SELECT 'Account', account_id, 'Customer', customer_id FROM accounts -- OWNS reversed
    UNION ALL SELECT 'Account', account_id, 'Device', device_id FROM account_devices   -- USED_DEVICE
    UNION ALL SELECT 'Device', device_id, 'Account', account_id FROM account_devices   -- reversed
), walk(kind, id, depth) AS (
    SELECT 'Account', %(account)s::integer, 0
    UNION
    SELECT e.dk, e.di, w.depth + 1
    FROM walk w JOIN edges e ON e.sk = w.kind AND e.si = w.id
    WHERE w.depth < %(depth)s
)
SELECT c.region, COUNT(*) AS accounts
FROM (SELECT DISTINCT id FROM walk WHERE kind = 'Account' AND id <> %(account)s) r
JOIN accounts a  ON a.account_id = r.id
JOIN customers c ON c.customer_id = a.customer_id
GROUP BY c.region
ORDER BY c.region
"""
# The depth is a literal inside the pattern (Cypher cannot parameterize *1..$d), so the
# runner formats it from a validated integer.
Q4_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id:$account}})
MATCH (a)-[:OWNS|USED_DEVICE*1..{depth}]-(b:Account)
WHERE b <> a
WITH DISTINCT b
MATCH (c:Customer)-[:OWNS]->(b)
RETURN c.region AS region, count(b) AS accounts
ORDER BY region
"""


def q4_cypher(depth: int) -> str:
    return Q4_CYPHER_TEMPLATE.format(depth=int(depth))


# One supporting path (shortest association path) for the report
Q4_PATH_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id:$account}}), (b:Account {{account_id:$other}})
MATCH p = shortestPath((a)-[:OWNS|USED_DEVICE*1..{depth}]-(b))
RETURN [n IN nodes(p) | labels(n)[0] + ' ' +
        toString(coalesce(n.account_id, n.customer_id, n.device_id))] AS path, length(p) AS links
"""

# --------------------------------------------------------------------------- Q5
Q5_SQL = """
SELECT t1.transfer_id AS t1, t2.transfer_id AS t2, t3.transfer_id AS t3, t3.receiver_id AS final_receiver
FROM transfers t1
JOIN transfers t2 ON t2.sender_id = t1.receiver_id
                 AND t2.occurred_at > t1.occurred_at AND t2.occurred_at <= t1.occurred_at + 600
JOIN transfers t3 ON t3.sender_id = t2.receiver_id
                 AND t3.occurred_at > t2.occurred_at AND t3.occurred_at <= t2.occurred_at + 600
WHERE t1.sender_id = %(account)s
  AND t1.occurred_at >= %(start)s AND t1.occurred_at < %(end)s
  AND 90::bigint * t1.amount_rwf <= 100::bigint * t2.amount_rwf
  AND 100::bigint * t2.amount_rwf <= 105::bigint * t1.amount_rwf
  AND 90::bigint * t2.amount_rwf <= 100::bigint * t3.amount_rwf
  AND 100::bigint * t3.amount_rwf <= 105::bigint * t2.amount_rwf
  -- four distinct accounts
  AND t1.receiver_id <> t1.sender_id
  AND t2.receiver_id NOT IN (t1.sender_id, t1.receiver_id)
  AND t3.receiver_id NOT IN (t1.sender_id, t1.receiver_id, t2.receiver_id)
ORDER BY t1, t2, t3, final_receiver
"""
Q5_CYPHER = """
MATCH (a:Account {account_id:$account})-[t1:TRANSFER]->(b:Account)
WHERE t1.occurred_at >= $start AND t1.occurred_at < $end
MATCH (b)-[t2:TRANSFER]->(c:Account)
WHERE t2.occurred_at > t1.occurred_at AND t2.occurred_at <= t1.occurred_at + 600
  AND 90 * t1.amount_rwf <= 100 * t2.amount_rwf AND 100 * t2.amount_rwf <= 105 * t1.amount_rwf
MATCH (c)-[t3:TRANSFER]->(d:Account)
WHERE t3.occurred_at > t2.occurred_at AND t3.occurred_at <= t2.occurred_at + 600
  AND 90 * t2.amount_rwf <= 100 * t3.amount_rwf AND 100 * t3.amount_rwf <= 105 * t2.amount_rwf
  AND a <> b AND a <> c AND a <> d AND b <> c AND b <> d AND c <> d
RETURN t1.transfer_id AS t1, t2.transfer_id AS t2, t3.transfer_id AS t3, d.account_id AS final_receiver
ORDER BY t1, t2, t3, final_receiver
"""

# --------------------------------------------------------------------------- Q6
# Stop at first return: a walk that reaches the start account is never extended.
Q6_SQL = """
WITH RECURSIVE walk(cur, ids, first_at, last_at, last_amount, len, returned) AS (
    SELECT t.receiver_id, ARRAY[t.transfer_id], t.occurred_at, t.occurred_at, t.amount_rwf, 1,
           t.receiver_id = %(account)s
    FROM transfers t
    WHERE t.sender_id = %(account)s
      AND t.occurred_at >= %(start)s AND t.occurred_at < %(end)s
  UNION ALL
    SELECT t.receiver_id, w.ids || t.transfer_id, w.first_at, t.occurred_at, t.amount_rwf, w.len + 1,
           t.receiver_id = %(account)s
    FROM walk w
    JOIN transfers t ON t.sender_id = w.cur
                    AND t.occurred_at > w.last_at
                    AND t.occurred_at < %(end)s
                    AND t.occurred_at <= w.first_at + 1800
    WHERE NOT w.returned AND w.len < 8
      AND 90::bigint * w.last_amount <= 100::bigint * t.amount_rwf
      AND 100::bigint * t.amount_rwf <= 105::bigint * w.last_amount
)
SELECT ids AS transfer_ids, len AS transfers
FROM walk
WHERE returned AND len BETWEEN 3 AND 8
ORDER BY ids
"""
# The per-relationship hour filter is pushed into the variable-length expansion by the
# planner (all(... IN relationships(p)) form), which keeps the search inside one hour.
Q6_CYPHER = """
MATCH (a:Account {account_id:$account})
MATCH p = (a)-[:TRANSFER*3..8]->(a)
WHERE all(t IN relationships(p) WHERE t.occurred_at >= $start AND t.occurred_at < $end)
WITH a, relationships(p) AS ts, nodes(p) AS ns
WHERE all(i IN range(1, size(ts) - 1) WHERE
          ts[i].occurred_at > ts[i-1].occurred_at
          AND 90 * ts[i-1].amount_rwf <= 100 * ts[i].amount_rwf
          AND 100 * ts[i].amount_rwf <= 105 * ts[i-1].amount_rwf)
  AND ts[size(ts)-1].occurred_at - ts[0].occurred_at <= 1800
  AND none(n IN ns[1..size(ns)-1] WHERE n = a)
RETURN [t IN ts | t.transfer_id] AS transfer_ids, size(ts) AS transfers
ORDER BY transfer_ids
"""

# --------------------------------------------------------------------------- Q7
# Baseline SQL: breadth-first walk over directed person-to-person transfers.
# UNION removes duplicate (account, depth) rows, but an account is revisited at every
# later depth and every parallel transfer row is joined (see Section 6.3).
Q7_SQL = """
WITH RECURSIVE bfs(account_id, depth) AS (
    SELECT a.account_id, 0 FROM accounts a
    WHERE a.account_id = %(account)s AND a.role = 'person'
  UNION
    SELECT t.receiver_id, b.depth + 1
    FROM bfs b
    JOIN transfers t ON t.sender_id = b.account_id
    JOIN accounts r  ON r.account_id = t.receiver_id AND r.role = 'person'
    WHERE b.depth < %(bound)s
)
SELECT MIN(depth) AS min_transfers FROM bfs WHERE account_id = %(dest)s
"""
# Improved SQL (Section 6.3): bidirectional search over distinct neighbours.
# Forward from the review account up to ceil(bound/2) steps, backward from the destination
# up to floor(bound/2) steps, both restricted to person accounts during the search; the
# minimum df + db over meeting accounts equals the shortest length within the bound.
Q7_SQL_IMPROVED = """
WITH RECURSIVE fwd(account_id, depth) AS (
    SELECT a.account_id, 0 FROM accounts a WHERE a.account_id = %(account)s AND a.role = 'person'
  UNION
    SELECT n.receiver_id, f.depth + 1
    FROM fwd f
    CROSS JOIN LATERAL (
        SELECT DISTINCT t.receiver_id FROM transfers t
        JOIN accounts r ON r.account_id = t.receiver_id AND r.role = 'person'
        WHERE t.sender_id = f.account_id) n
    WHERE f.depth < (%(bound)s + 1) / 2
), bwd(account_id, depth) AS (
    SELECT a.account_id, 0 FROM accounts a WHERE a.account_id = %(dest)s AND a.role = 'person'
  UNION
    SELECT n.sender_id, b.depth + 1
    FROM bwd b
    CROSS JOIN LATERAL (
        SELECT DISTINCT t.sender_id FROM transfers t
        JOIN accounts s ON s.account_id = t.sender_id AND s.role = 'person'
        WHERE t.receiver_id = b.account_id) n
    WHERE b.depth < %(bound)s / 2
), f AS (SELECT account_id, MIN(depth) AS d FROM fwd GROUP BY account_id),
   b AS (SELECT account_id, MIN(depth) AS d FROM bwd GROUP BY account_id)
SELECT MIN(f.d + b.d) AS min_transfers
FROM f JOIN b USING (account_id)
WHERE f.d + b.d <= %(bound)s
"""
# Native shortest path; the all(nodes ...) predicate is evaluated during the BFS,
# so the person restriction applies to the search, not afterwards.
Q7_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id:$account}}), (d:Account {{account_id:$dest}})
OPTIONAL MATCH p = shortestPath((a)-[:TRANSFER*1..{bound}]->(d))
WHERE all(n IN nodes(p) WHERE n.role = 'person')
RETURN length(p) AS min_transfers
"""


def q7_cypher(bound: int) -> str:
    return Q7_CYPHER_TEMPLATE.format(bound=int(bound))


# Path retrieval (one supporting path per successful case)
Q7_PATH_CYPHER_TEMPLATE = """
MATCH (a:Account {{account_id:$account}}), (d:Account {{account_id:$dest}})
MATCH p = shortestPath((a)-[:TRANSFER*1..{bound}]->(d))
WHERE all(n IN nodes(p) WHERE n.role = 'person')
RETURN [n IN nodes(p) | n.account_id] AS accounts,
       [r IN relationships(p) | r.transfer_id] AS transfer_ids
"""


def q7_path_cypher(bound: int) -> str:
    return Q7_PATH_CYPHER_TEMPLATE.format(bound=int(bound))


# SQL path retrieval: bidirectional search carrying the account path on each side.
Q7_PATH_SQL = """
WITH RECURSIVE fwd(account_id, depth, path) AS (
    SELECT a.account_id, 0, ARRAY[a.account_id] FROM accounts a
    WHERE a.account_id = %(account)s AND a.role = 'person'
  UNION ALL
    SELECT n.receiver_id, f.depth + 1, f.path || n.receiver_id
    FROM fwd f CROSS JOIN LATERAL (
        SELECT DISTINCT t.receiver_id FROM transfers t
        JOIN accounts r ON r.account_id = t.receiver_id AND r.role = 'person'
        WHERE t.sender_id = f.account_id) n
    WHERE f.depth < (%(len)s + 1) / 2 AND NOT n.receiver_id = ANY (f.path)
), bwd(account_id, depth, path) AS (
    SELECT a.account_id, 0, ARRAY[a.account_id] FROM accounts a
    WHERE a.account_id = %(dest)s AND a.role = 'person'
  UNION ALL
    SELECT n.sender_id, b.depth + 1, n.sender_id || b.path
    FROM bwd b CROSS JOIN LATERAL (
        SELECT DISTINCT t.sender_id FROM transfers t
        JOIN accounts s ON s.account_id = t.sender_id AND s.role = 'person'
        WHERE t.receiver_id = b.account_id) n
    WHERE b.depth < %(len)s / 2 AND NOT n.sender_id = ANY (b.path)
)
SELECT f.path || b.path[2:] AS accounts
FROM fwd f JOIN bwd b ON b.account_id = f.account_id
WHERE f.depth + b.depth = %(len)s
ORDER BY 1
LIMIT 1
"""

# Verification of any returned account path: every hop has a stored transfer in that
# direction, every account is a person, and the hop count equals the minimum length.
Q7_VERIFY_SQL = """
SELECT h.step, h.sender, h.receiver,
       (SELECT MIN(t.transfer_id) FROM transfers t
         WHERE t.sender_id = h.sender AND t.receiver_id = h.receiver) AS example_transfer_id,
       (SELECT role FROM accounts WHERE account_id = h.sender)   AS sender_role,
       (SELECT role FROM accounts WHERE account_id = h.receiver) AS receiver_role
FROM (SELECT i AS step, (%(path)s::int[])[i] AS sender, (%(path)s::int[])[i + 1] AS receiver
      FROM generate_series(1, cardinality(%(path)s::int[]) - 1) i) h
ORDER BY h.step
"""


# --------------------------------------------------------------------------- cases
def cases():
    """The 61 comparison cases: Q1 6, Q2 1, Q3 6, Q4 24, Q5 6, Q6 6, Q7 12."""
    out = []
    for q in ("Q1",):
        out += [(f"{q}-{s}", q, s, set_params(s)) for s in SETS]
    out.append(("Q2-month", "Q2", "month", {}))
    out += [(f"Q3-{s}", "Q3", s, set_params(s)) for s in SETS]
    out += [(f"Q4-{s}-d{d}", "Q4", s, {**set_params(s), "depth": d}) for s in SETS for d in Q4_DEPTHS]
    out += [(f"Q5-{s}", "Q5", s, set_params(s)) for s in SETS]
    out += [(f"Q6-{s}", "Q6", s, set_params(s)) for s in SETS]
    out += [(f"Q7-{s}-b{b}", "Q7", s, {**set_params(s), "bound": b}) for s in SETS for b in Q7_BOUNDS]
    return out


def sql_for(q, params, improved_q7=False):
    return {"Q1": Q1_SQL, "Q2": Q2_SQL, "Q3": Q3_SQL, "Q4": Q4_SQL, "Q5": Q5_SQL, "Q6": Q6_SQL,
            "Q7": Q7_SQL_IMPROVED if improved_q7 else Q7_SQL}[q]


def cypher_for(q, params):
    if q == "Q4":
        return q4_cypher(params["depth"])
    if q == "Q7":
        return q7_cypher(params["bound"])
    return {"Q1": Q1_CYPHER, "Q2": Q2_CYPHER, "Q3": Q3_CYPHER, "Q5": Q5_CYPHER, "Q6": Q6_CYPHER}[q]


def pg_params(q, params):
    """Only pass the parameters a query uses (psycopg ignores none; keep it explicit)."""
    keys = {"Q1": ("account", "start", "end"), "Q2": (), "Q3": ("account",),
            "Q4": ("account", "depth"), "Q5": ("account", "start", "end"),
            "Q6": ("account", "start", "end"), "Q7": ("account", "dest", "bound")}[q]
    return {k: params[k] for k in keys}


def neo_params(q, params):
    keys = {"Q1": ("account", "start", "end"), "Q2": (), "Q3": ("account",),
            "Q4": ("account",), "Q5": ("account", "start", "end"),
            "Q6": ("account", "start", "end"), "Q7": ("account", "dest")}[q]
    return {k: params[k] for k in keys}

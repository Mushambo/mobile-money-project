-- Q4 check (Section 8.3): how many accounts reached within 10 links depend on a
-- public terminal or on a handset that stopped being used before day 29 (replaced phone).
-- Run:  psql -U postgres -d mobile_money -f sql\q4_weak_links.sql
\timing on
WITH RECURSIVE
review(set_name, account_id) AS (
    VALUES ('A',998),('B',147228),('C',206978),('D',237998),('E',144228),('F',203978)
),
dev_edges AS (                       -- device links, flagged as weak or strong
    SELECT ad.account_id, ad.device_id,
           (d.access_type = 'public_terminal' OR ad.last_day < 29) AS weak
    FROM account_devices ad JOIN devices d USING (device_id)
),
edges(sk, si, dk, di, weak) AS (
    SELECT 'C', customer_id, 'A', account_id, false FROM accounts
    UNION ALL SELECT 'A', account_id, 'C', customer_id, false FROM accounts
    UNION ALL SELECT 'A', account_id, 'D', device_id, weak FROM dev_edges
    UNION ALL SELECT 'D', device_id, 'A', account_id, weak FROM dev_edges
),
walk_all(set_name, start_id, kind, id, depth) AS (
    SELECT set_name, account_id, 'A', account_id, 0 FROM review
    UNION
    SELECT w.set_name, w.start_id, e.dk, e.di, w.depth + 1
    FROM walk_all w JOIN edges e ON e.sk = w.kind AND e.si = w.id
    WHERE w.depth < 10
),
walk_strong(set_name, start_id, kind, id, depth) AS (
    SELECT set_name, account_id, 'A', account_id, 0 FROM review
    UNION
    SELECT w.set_name, w.start_id, e.dk, e.di, w.depth + 1
    FROM walk_strong w JOIN edges e ON e.sk = w.kind AND e.si = w.id AND NOT e.weak
    WHERE w.depth < 10
),
all_n AS (SELECT set_name, count(DISTINCT id) AS n FROM walk_all
          WHERE kind = 'A' AND id <> start_id GROUP BY set_name),
strong_n AS (SELECT set_name, count(DISTINCT id) AS n FROM walk_strong
             WHERE kind = 'A' AND id <> start_id GROUP BY set_name)
SELECT a.set_name AS set, a.n AS reached_10_links,
       COALESCE(s.n, 0) AS without_weak_links,
       a.n - COALESCE(s.n, 0) AS depend_on_weak_links,
       round(100.0 * (a.n - COALESCE(s.n, 0)) / a.n, 1) AS pct_dependent
FROM all_n a LEFT JOIN strong_n s USING (set_name)
ORDER BY a.set_name;

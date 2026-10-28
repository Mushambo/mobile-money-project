-- psycopg parameters: %(name)s
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
ORDER BY c.region;

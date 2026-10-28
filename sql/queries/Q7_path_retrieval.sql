-- psycopg parameters: %(name)s
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
LIMIT 1;

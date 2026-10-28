-- psycopg parameters: %(name)s
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
WHERE f.d + b.d <= %(bound)s;

-- psycopg parameters: %(name)s
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
SELECT MIN(depth) AS min_transfers FROM bfs WHERE account_id = %(dest)s;

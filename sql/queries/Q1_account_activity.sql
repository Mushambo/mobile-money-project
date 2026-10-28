-- psycopg parameters: %(name)s
SELECT COUNT(*) AS transfers, COALESCE(SUM(amount_rwf), 0) AS total_rwf
FROM transfers
WHERE sender_id = %(account)s
  AND occurred_at >= %(start)s AND occurred_at < %(end)s;

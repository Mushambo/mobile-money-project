-- psycopg parameters: %(name)s
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
ORDER BY ids;

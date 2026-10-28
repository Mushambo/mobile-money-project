-- psycopg parameters: %(name)s
SELECT (to_timestamp(occurred_at) AT TIME ZONE 'Africa/Kigali')::date AS cat_date,
       COUNT(*) AS transfers, SUM(amount_rwf) AS total_rwf
FROM transfers
GROUP BY cat_date
ORDER BY cat_date;

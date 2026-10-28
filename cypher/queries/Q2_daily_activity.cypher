// parameters: $name
MATCH ()-[t:TRANSFER]->()
WITH date(datetime({epochSeconds: t.occurred_at, timezone: 'Africa/Kigali'})) AS cat_date,
     t.amount_rwf AS amount
RETURN cat_date, count(*) AS transfers, sum(amount) AS total_rwf
ORDER BY cat_date;

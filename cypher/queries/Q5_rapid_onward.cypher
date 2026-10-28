// parameters: $name
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
ORDER BY t1, t2, t3, final_receiver;

// parameters: $name
MATCH (a:Account {account_id:$account})
OPTIONAL MATCH (a)-[t:TRANSFER]->()
WHERE t.occurred_at >= $start AND t.occurred_at < $end
RETURN count(t) AS transfers, coalesce(sum(t.amount_rwf), 0) AS total_rwf;

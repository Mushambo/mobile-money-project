// parameters: $name
MATCH (a:Account {account_id:$account})
MATCH p = (a)-[:TRANSFER*3..8]->(a)
WHERE all(t IN relationships(p) WHERE t.occurred_at >= $start AND t.occurred_at < $end)
WITH a, relationships(p) AS ts, nodes(p) AS ns
WHERE all(i IN range(1, size(ts) - 1) WHERE
          ts[i].occurred_at > ts[i-1].occurred_at
          AND 90 * ts[i-1].amount_rwf <= 100 * ts[i].amount_rwf
          AND 100 * ts[i].amount_rwf <= 105 * ts[i-1].amount_rwf)
  AND ts[size(ts)-1].occurred_at - ts[0].occurred_at <= 1800
  AND none(n IN ns[1..size(ns)-1] WHERE n = a)
RETURN [t IN ts | t.transfer_id] AS transfer_ids, size(ts) AS transfers
ORDER BY transfer_ids;

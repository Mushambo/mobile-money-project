// parameters: $name
MATCH (a:Account {account_id:$account}), (b:Account {account_id:$other})
MATCH p = shortestPath((a)-[:OWNS|USED_DEVICE*1..4]-(b))
RETURN [n IN nodes(p) | labels(n)[0] + ' ' +
        toString(coalesce(n.account_id, n.customer_id, n.device_id))] AS path, length(p) AS links;

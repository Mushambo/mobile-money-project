// parameters: $name
MATCH (a:Account {account_id:$account}), (d:Account {account_id:$dest})
MATCH p = shortestPath((a)-[:TRANSFER*1..4]->(d))
WHERE all(n IN nodes(p) WHERE n.role = 'person')
RETURN [n IN nodes(p) | n.account_id] AS accounts,
       [r IN relationships(p) | r.transfer_id] AS transfer_ids;

// parameters: $name
MATCH (a:Account {account_id:$account}), (d:Account {account_id:$dest})
OPTIONAL MATCH p = shortestPath((a)-[:TRANSFER*1..6]->(d))
WHERE all(n IN nodes(p) WHERE n.role = 'person')
RETURN length(p) AS min_transfers;

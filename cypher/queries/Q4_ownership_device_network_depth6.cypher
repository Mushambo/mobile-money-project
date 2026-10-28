// parameters: $name
MATCH (a:Account {account_id:$account})
MATCH (a)-[:OWNS|USED_DEVICE*1..6]-(b:Account)
WHERE b <> a
WITH DISTINCT b
MATCH (c:Customer)-[:OWNS]->(b)
RETURN c.region AS region, count(b) AS accounts
ORDER BY region;

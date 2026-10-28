// parameters: $name
MATCH (a:Account {account_id:$account})-[r:USED_DEVICE]->(d:Device)<-[o:USED_DEVICE]-(b:Account)
WHERE b <> a
WITH b, d,
     CASE WHEN r.first_day > o.first_day THEN r.first_day ELSE o.first_day END AS overlap_start,
     CASE WHEN r.last_day  < o.last_day  THEN r.last_day  ELSE o.last_day  END AS overlap_end
WHERE overlap_start <= overlap_end
RETURN b.account_id AS other_account, d.device_id AS device_id, d.access_type AS access_type,
       overlap_start, overlap_end
ORDER BY other_account, device_id;

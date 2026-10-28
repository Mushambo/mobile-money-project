-- psycopg parameters: %(name)s
SELECT o.account_id AS other_account, o.device_id, d.access_type,
       GREATEST(r.first_day, o.first_day) AS overlap_start,
       LEAST(r.last_day, o.last_day)      AS overlap_end
FROM account_devices r
JOIN account_devices o ON o.device_id = r.device_id AND o.account_id <> r.account_id
JOIN devices d         ON d.device_id = r.device_id
WHERE r.account_id = %(account)s
  AND GREATEST(r.first_day, o.first_day) <= LEAST(r.last_day, o.last_day)
ORDER BY other_account, o.device_id;

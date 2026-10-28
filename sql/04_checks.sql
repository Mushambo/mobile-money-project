-- Section 2.2.3  Post-load checks. Compare with results/capture_audit.json.
--   psql -d mobile_money -f sql/04_checks.sql
SHOW timezone;

SELECT 'customers' AS tbl, count(*) FROM customers
UNION ALL SELECT 'accounts', count(*) FROM accounts
UNION ALL SELECT 'devices', count(*) FROM devices
UNION ALL SELECT 'account_devices', count(*) FROM account_devices
UNION ALL SELECT 'transfers', count(*) FROM transfers;

SELECT count(*) AS transfer_count, min(occurred_at) AS min_occurred_at, max(occurred_at) AS max_occurred_at,
       to_timestamp(min(occurred_at)) AS min_cat, to_timestamp(max(occurred_at)) AS max_cat,
       sum(amount_rwf) AS sum_amount_rwf
FROM transfers;

SELECT role, count(*) FROM accounts GROUP BY role ORDER BY role;   -- agent 2000, merchant 6000, person 240000

-- Every constraint should show convalidated = true
SELECT conrelid::regclass AS tbl, conname, contype, convalidated, pg_get_constraintdef(oid) AS definition
FROM pg_constraint WHERE connamespace = 'public'::regnamespace ORDER BY 1, 2;

SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY 1, 2;

-- Sizes in decimal GB (1 GB = 1,000,000,000 bytes)
SELECT c.relname AS tbl,
       round(pg_table_size(c.oid)   / 1e9, 4) AS data_gb,
       round(pg_indexes_size(c.oid) / 1e9, 4) AS index_gb,
       round(pg_total_relation_size(c.oid) / 1e9, 4) AS total_gb
FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r'
ORDER BY 1;
SELECT round(pg_database_size(current_database()) / 1e9, 4) AS database_gb;

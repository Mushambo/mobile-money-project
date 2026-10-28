-- Section 2.1/2.2  Keys, foreign keys, checks and indexes (timed separately from loading).
--   psql -d mobile_money -f sql/03_constraints_indexes.sql
\timing on

-- Primary keys
ALTER TABLE customers       ADD CONSTRAINT customers_pk       PRIMARY KEY (customer_id);
ALTER TABLE devices         ADD CONSTRAINT devices_pk         PRIMARY KEY (device_id);
ALTER TABLE accounts        ADD CONSTRAINT accounts_pk        PRIMARY KEY (account_id);
ALTER TABLE account_devices ADD CONSTRAINT account_devices_pk PRIMARY KEY (account_id, device_id);
ALTER TABLE transfers       ADD CONSTRAINT transfers_pk       PRIMARY KEY (transfer_id);

-- Foreign keys: ownership, device use, both transfer endpoints
ALTER TABLE accounts        ADD CONSTRAINT accounts_customer_fk FOREIGN KEY (customer_id) REFERENCES customers;
ALTER TABLE account_devices ADD CONSTRAINT ad_account_fk        FOREIGN KEY (account_id)  REFERENCES accounts;
ALTER TABLE account_devices ADD CONSTRAINT ad_device_fk         FOREIGN KEY (device_id)   REFERENCES devices;
ALTER TABLE transfers       ADD CONSTRAINT transfers_sender_fk  FOREIGN KEY (sender_id)   REFERENCES accounts (account_id);
ALTER TABLE transfers       ADD CONSTRAINT transfers_receiver_fk FOREIGN KEY (receiver_id) REFERENCES accounts (account_id);

-- Value rules
ALTER TABLE accounts        ADD CONSTRAINT accounts_role_chk  CHECK (role IN ('person','merchant','agent'));
ALTER TABLE devices         ADD CONSTRAINT devices_type_chk   CHECK (access_type IN ('handset','public_terminal'));
ALTER TABLE customers       ADD CONSTRAINT customers_region_chk CHECK (region IN ('Kigali','Northern','Southern','Eastern','Western'));
ALTER TABLE transfers       ADD CONSTRAINT transfers_amount_chk CHECK (amount_rwf > 0);
ALTER TABLE account_devices ADD CONSTRAINT ad_obs_chk         CHECK (observations > 0);
ALTER TABLE account_devices ADD CONSTRAINT ad_days_chk        CHECK (0 <= first_day AND first_day <= last_day AND last_day <= 29);

-- Indexes required by the brief
CREATE INDEX accounts_customer_idx  ON accounts (customer_id, account_id);
CREATE INDEX ad_device_idx          ON account_devices (device_id, account_id);
CREATE INDEX transfers_sender_idx   ON transfers (sender_id, occurred_at)   INCLUDE (receiver_id, amount_rwf, transfer_id);
CREATE INDEX transfers_receiver_idx ON transfers (receiver_id, occurred_at) INCLUDE (sender_id, amount_rwf, transfer_id);
CREATE INDEX transfers_time_brin    ON transfers USING brin (occurred_at);

VACUUM (ANALYZE) customers, devices, accounts, account_devices, transfers;

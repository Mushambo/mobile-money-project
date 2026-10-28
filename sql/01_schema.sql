-- Section 2.1  Five tables. Run in the project database:  psql -d mobile_money -f sql/01_schema.sql
-- Keys/constraints are added AFTER bulk loading (sql/03_constraints_indexes.sql) so that
-- loading and index/constraint setup can be timed separately.
ALTER DATABASE mobile_money SET timezone TO 'Africa/Kigali';
SET timezone TO 'Africa/Kigali';

DROP TABLE IF EXISTS transfers, account_devices, accounts, devices, customers CASCADE;

CREATE TABLE customers (
    customer_id  INTEGER NOT NULL,          -- customer (wallet holder) identifier
    region       TEXT    NOT NULL           -- Kigali | Northern | Southern | Eastern | Western
);

CREATE TABLE accounts (
    account_id   INTEGER NOT NULL,          -- wallet identifier
    customer_id  INTEGER NOT NULL,          -- owning customer
    role         TEXT    NOT NULL           -- person | merchant | agent
);

CREATE TABLE devices (
    device_id    INTEGER NOT NULL,          -- device identifier
    access_type  TEXT    NOT NULL           -- handset | public_terminal
);

CREATE TABLE account_devices (
    account_id   INTEGER  NOT NULL,         -- wallet observed on the device
    device_id    INTEGER  NOT NULL,
    first_day    SMALLINT NOT NULL,         -- inclusive day number, 0 = 1 Sep 2026 CAT
    last_day     SMALLINT NOT NULL,         -- inclusive day number, 29 = 30 Sep 2026 CAT
    observations INTEGER  NOT NULL          -- count of observations within [first_day, last_day]
);

CREATE TABLE transfers (
    transfer_id  BIGINT  NOT NULL,          -- event identifier
    sender_id    INTEGER NOT NULL,          -- paying wallet
    receiver_id  INTEGER NOT NULL,          -- receiving wallet
    occurred_at  BIGINT  NOT NULL,          -- Unix epoch seconds (UTC instant; CAT = UTC+02:00)
    amount_rwf   INTEGER NOT NULL           -- positive whole Rwandan francs
);

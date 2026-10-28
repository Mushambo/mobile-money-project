// Section 3.2.4  Verification. Expected values in comments.
MATCH (n:Customer) RETURN 'Customer' AS label, count(n) AS n          // 228,000
UNION ALL MATCH (n:Account) RETURN 'Account' AS label, count(n) AS n  // 248,000
UNION ALL MATCH (n:Device)  RETURN 'Device'  AS label, count(n) AS n; // 228,600

MATCH (n) RETURN count(n) AS nodes;                                   // 704,600
MATCH ()-[r]->() RETURN count(r) AS relationships;                    // 20,536,900
MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS n ORDER BY type; // OWNS 248,000 TRANSFER 20,003,300 USED_DEVICE 285,600

MATCH (a:Account) RETURN a.role AS role, count(*) AS n ORDER BY role; // agent 2,000 merchant 6,000 person 240,000

// one owner per account: both must be 0
MATCH (a:Account) WHERE NOT ()-[:OWNS]->(a) RETURN count(a) AS accounts_without_owner;
MATCH (a:Account) WHERE COUNT { ()-[:OWNS]->(a) } > 1 RETURN count(a) AS accounts_with_many_owners;

// unique transfer_id: distinct = total
MATCH ()-[t:TRANSFER]->() RETURN count(t) AS transfers, count(DISTINCT t.transfer_id) AS distinct_ids;

// audit totals (compare to results/capture_audit.json)
MATCH ()-[t:TRANSFER]->()
RETURN count(t) AS transfer_count, min(t.occurred_at) AS min_occurred_at,
       max(t.occurred_at) AS max_occurred_at, sum(t.amount_rwf) AS sum_amount_rwf;

// IDs are stored as integers (true means integer comparison works)
MATCH (a:Account {account_id: 998}) RETURN a.account_id, valueType(a.account_id) AS id_type;

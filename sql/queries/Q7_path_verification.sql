-- psycopg parameters: %(name)s
SELECT h.step, h.sender, h.receiver,
       (SELECT MIN(t.transfer_id) FROM transfers t
         WHERE t.sender_id = h.sender AND t.receiver_id = h.receiver) AS example_transfer_id,
       (SELECT role FROM accounts WHERE account_id = h.sender)   AS sender_role,
       (SELECT role FROM accounts WHERE account_id = h.receiver) AS receiver_role
FROM (SELECT i AS step, (%(path)s::int[])[i] AS sender, (%(path)s::int[])[i + 1] AS receiver
      FROM generate_series(1, cardinality(%(path)s::int[]) - 1) i) h
ORDER BY h.step;

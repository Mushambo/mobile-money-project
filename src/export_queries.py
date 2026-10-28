"""Write every SQL/Cypher query from queries.py to sql/queries and cypher/queries for reading."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queries as Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sql_dir, cy_dir = ROOT / "sql" / "queries", ROOT / "cypher" / "queries"
sql_dir.mkdir(parents=True, exist_ok=True); cy_dir.mkdir(parents=True, exist_ok=True)
sql = {"Q1_account_activity": Q.Q1_SQL, "Q2_daily_activity": Q.Q2_SQL, "Q3_shared_devices": Q.Q3_SQL,
       "Q4_ownership_device_network": Q.Q4_SQL, "Q5_rapid_onward": Q.Q5_SQL, "Q6_circular": Q.Q6_SQL,
       "Q7_shortest_baseline": Q.Q7_SQL, "Q7_shortest_improved": Q.Q7_SQL_IMPROVED,
       "Q7_path_retrieval": Q.Q7_PATH_SQL, "Q7_path_verification": Q.Q7_VERIFY_SQL}
cy = {"Q1_account_activity": Q.Q1_CYPHER, "Q2_daily_activity": Q.Q2_CYPHER, "Q3_shared_devices": Q.Q3_CYPHER,
      "Q4_ownership_device_network_depth{n}": Q.Q4_CYPHER_TEMPLATE, "Q5_rapid_onward": Q.Q5_CYPHER,
      "Q6_circular": Q.Q6_CYPHER, "Q7_shortest_bound{n}": Q.Q7_CYPHER_TEMPLATE,
      "Q7_path_bound{n}": Q.Q7_PATH_CYPHER_TEMPLATE, "Q4_supporting_path_depth{n}": Q.Q4_PATH_CYPHER_TEMPLATE}
for name, text in sql.items():
    (sql_dir / f"{name}.sql").write_text("-- psycopg parameters: %(name)s\n" + text.strip() + ";\n")
for name, text in cy.items():
    if "{n}" in name:
        for n in ((4, 6, 8, 10) if "Q4" in name else (4, 6)):
            body = text.format(depth=n, bound=n).strip()
            (cy_dir / f"{name.format(n=n)}.cypher").write_text("// parameters: $name\n" + body + ";\n")
    else:
        (cy_dir / f"{name}.cypher").write_text("// parameters: $name\n" + text.strip() + ";\n")
print("wrote", len(list(sql_dir.glob('*'))), "SQL and", len(list(cy_dir.glob('*'))), "Cypher files")

"""Schema and evidence diagrams for the report (Graphviz 'dot' must be installed).
Evidence diagrams are drawn from the loaded PostgreSQL data, not from the generator.
    python src/diagrams.py        -> results/diagrams/*.png (+ .dot sources)"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402
from db import close, run_pg  # noqa: E402
import queries as Q  # noqa: E402

OUT = RESULTS_DIR / "diagrams"
CAT = ZoneInfo("Africa/Kigali")
FONT = 'fontname="Helvetica"'


def render(name, dot):
    (OUT / f"{name}.dot").write_text(dot)
    subprocess.run(["dot", "-Tpng", "-Gdpi=160", "-o", str(OUT / f"{name}.png"), str(OUT / f"{name}.dot")], check=True)
    print("drew", name)


def cat(ts):
    return datetime.fromtimestamp(ts, CAT).strftime("%d Sep %H:%M:%S")


RELATIONAL = f"""digraph G {{ rankdir=LR; node [shape=plain {FONT} fontsize=10]; edge [{FONT} fontsize=9 color="#555555"];
customers [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
<tr><td bgcolor="#336791"><font color="white"><b>customers</b></font></td></tr>
<tr><td align="left" port="pk"><b>customer_id</b> INTEGER PK</td></tr><tr><td align="left">region TEXT</td></tr></table>>];
accounts [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
<tr><td bgcolor="#336791"><font color="white"><b>accounts</b></font></td></tr>
<tr><td align="left" port="pk"><b>account_id</b> INTEGER PK</td></tr><tr><td align="left" port="fk">customer_id INTEGER FK</td></tr>
<tr><td align="left">role TEXT (person|merchant|agent)</td></tr></table>>];
devices [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
<tr><td bgcolor="#336791"><font color="white"><b>devices</b></font></td></tr>
<tr><td align="left" port="pk"><b>device_id</b> INTEGER PK</td></tr><tr><td align="left">access_type TEXT (handset|public_terminal)</td></tr></table>>];
account_devices [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
<tr><td bgcolor="#336791"><font color="white"><b>account_devices</b></font></td></tr>
<tr><td align="left" port="a"><b>account_id</b> INTEGER PK, FK</td></tr><tr><td align="left" port="d"><b>device_id</b> INTEGER PK, FK</td></tr>
<tr><td align="left">first_day SMALLINT (0-29)</td></tr><tr><td align="left">last_day SMALLINT (0-29)</td></tr>
<tr><td align="left">observations INTEGER &gt; 0</td></tr></table>>];
transfers [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">
<tr><td bgcolor="#336791"><font color="white"><b>transfers</b></font></td></tr>
<tr><td align="left"><b>transfer_id</b> BIGINT PK</td></tr><tr><td align="left" port="s">sender_id INTEGER FK</td></tr>
<tr><td align="left" port="r">receiver_id INTEGER FK</td></tr><tr><td align="left">occurred_at BIGINT (epoch s)</td></tr>
<tr><td align="left">amount_rwf INTEGER &gt; 0 (RWF)</td></tr></table>>];
accounts:fk -> customers:pk [label="owned by (N:1)"];
account_devices:a -> accounts:pk [label="N:1"]; account_devices:d -> devices:pk [label="N:1"];
transfers:s -> accounts:pk [label="sender"]; transfers:r -> accounts:pk [label="receiver"];
}}"""

GRAPH = f"""digraph G {{ rankdir=LR; node [shape=ellipse style=filled {FONT} fontsize=10]; edge [{FONT} fontsize=9];
C [label="Customer\\ncustomer_id:int\\nregion:string" fillcolor="#ffd6a5"];
A [label="Account\\naccount_id:int\\nrole:string" fillcolor="#bde0fe"];
D [label="Device\\ndevice_id:int\\naccess_type:string" fillcolor="#caffbf"];
C -> A [label="OWNS"];
A -> D [label="USED_DEVICE\\nfirst_day:int, last_day:int,\\nobservations:int"];
A -> A [label="TRANSFER (one per event)\\ntransfer_id:long, occurred_at:long,\\namount_rwf:int"];
}}"""


def chain_diagram(name, ids, title):
    rows = run_pg("SELECT transfer_id, sender_id, receiver_id, occurred_at, amount_rwf FROM transfers "
                  "WHERE transfer_id = ANY(%(ids)s) ORDER BY occurred_at", {"ids": ids})
    roles = dict(run_pg("SELECT account_id, role FROM accounts WHERE account_id = ANY(%(a)s)",
                        {"a": [r[1] for r in rows] + [r[2] for r in rows]}))
    lines = [f'digraph G {{ rankdir=LR; labelloc=t; label="{title}"; {FONT}; '
             f'node [shape=box style="rounded,filled" fillcolor="#eef3fb" {FONT} fontsize=10]; edge [{FONT} fontsize=9];']
    for acc in dict.fromkeys([rows[0][1]] + [r[2] for r in rows]):
        lines.append(f'a{acc} [label="Account {acc}\\n{roles[acc]}"];')
    for t in rows:
        lines.append(f'a{t[1]} -> a{t[2]} [label="#{t[0]}\\n{cat(t[3])} CAT\\n{t[4]:,} RWF"];')
    lines.append("}")
    render(name, "\n".join(lines))


def association_diagram(name, account, depth, title):
    sql = """
    WITH RECURSIVE edges(sk, si, dk, di) AS (
        SELECT 'Customer', customer_id, 'Account', account_id FROM accounts
        UNION ALL SELECT 'Account', account_id, 'Customer', customer_id FROM accounts
        UNION ALL SELECT 'Account', account_id, 'Device', device_id FROM account_devices
        UNION ALL SELECT 'Device', device_id, 'Account', account_id FROM account_devices),
    walk(kind, id, depth, pk, pid) AS (
        SELECT 'Account', %(a)s::int, 0, NULL::text, NULL::int
        UNION
        SELECT e.dk, e.di, w.depth + 1, w.kind, w.id FROM walk w JOIN edges e ON e.sk = w.kind AND e.si = w.id
        WHERE w.depth < %(d)s)
    SELECT DISTINCT ON (kind, id) kind, id, depth, pk, pid FROM walk ORDER BY kind, id, depth, pk, pid"""
    nodes = run_pg(sql, {"a": account, "d": depth})
    first = {(k, i): d for k, i, d, _, _ in nodes}
    dev = dict(run_pg("SELECT device_id, access_type FROM devices WHERE device_id = ANY(%(d)s)",
                      {"d": [i for k, i, *_ in nodes if k == "Device"]}))
    style = {"Account": "#bde0fe", "Customer": "#ffd6a5", "Device": "#caffbf"}
    lines = [f'graph G {{ layout=neato; overlap=false; sep="+6"; labelloc=t; label="{title}"; {FONT}; '
             f'node [style=filled {FONT} fontsize=9]; edge [color="#777777"];']
    for (k, i), d in first.items():
        extra = f"\\n{dev[i]}" if k == "Device" else ""
        pen = ' penwidth=3 color="#c0392b"' if (k, i) == ("Account", account) else ""
        lines.append(f'"{k}{i}" [label="{k} {i}{extra}\\n(link {d})" fillcolor="{style[k]}"{pen}];')
    seen = set()
    for k, i, d, pk, pid in run_pg(sql.replace("DISTINCT ON (kind, id) ", "").replace(
            "ORDER BY kind, id, depth, pk, pid", "ORDER BY 1"), {"a": account, "d": depth}):
        if pk and first.get((k, i)) == d:
            e = tuple(sorted([f"{pk}{pid}", f"{k}{i}"]))
            if e not in seen:
                seen.add(e)
                lines.append(f'"{pk}{pid}" -- "{k}{i}";')
    lines.append("}")
    render(name, "\n".join(lines))


def q7_path_diagram(name, s, bound=6):
    p = Q.set_params(s)
    L = run_pg(Q.Q7_SQL_IMPROVED, {"account": p["account"], "dest": p["dest"], "bound": bound})[0][0]
    if L is None:
        return
    path = run_pg(Q.Q7_PATH_SQL, {"account": p["account"], "dest": p["dest"], "len": L})[0][0]
    hops = run_pg(Q.Q7_VERIFY_SQL, {"path": path})
    lines = [f'digraph G {{ rankdir=LR; labelloc=t; label="Q7 set {s}: one shortest person-only route ({L} transfers)"; {FONT}; '
             f'node [shape=box style="rounded,filled" fillcolor="#eef3fb" {FONT} fontsize=10]; edge [{FONT} fontsize=9];']
    for step, a, b, tid, *_ in hops:
        when = run_pg("SELECT occurred_at FROM transfers WHERE transfer_id = %(t)s", {"t": tid})[0][0]
        lines.append(f'a{a} -> a{b} [label="e.g. #{tid}\\n{cat(when)}"];')
    lines.append("}")
    render(name, "\n".join(lines))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    render("relational_schema", RELATIONAL)
    render("graph_schema", GRAPH)
    chain_diagram("q5_chain_B", [20000092, 20000093, 20000094], "Q5 set B: rapid onward chain")
    chain_diagram("q6_cycle_A", [20000001, 20000002, 20000003, 20000004], "Q6 set A: circular payments")
    association_diagram("q4_network_A_depth4", 998, 4, "Q4 set A: ownership/device links within 4")
    association_diagram("q4_network_D_depth4", 237998, 4, "Q4 set D: ownership/device links within 4")
    q7_path_diagram("q7_route_B", "B")
    close()

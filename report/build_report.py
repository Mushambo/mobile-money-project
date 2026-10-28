"""Builds report/Project2_Report_DRAFT.docx from the files in results/.
Yellow boxes = screenshots you must take on your own machine.
Orange text   = values to fill from your own Neo4j runs.
Re-run after new results:  python report/build_report.py"""
import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
doc = Document()
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2); s.top_margin = s.bottom_margin = Cm(1.8)


def shade(cell_or_par, color):
    el = cell_or_par._tc.get_or_add_tcPr() if hasattr(cell_or_par, "_tc") else cell_or_par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    el.append(shd)


def H(text, lvl=1):
    doc.add_heading(text, lvl)


def P(text, bold_lead=None):
    par = doc.add_paragraph()
    if bold_lead:
        par.add_run(bold_lead).bold = True
    par.add_run(text)
    return par


def SHOT(text):
    par = doc.add_paragraph()
    r = par.add_run("SCREENSHOT TO INSERT: " + text); r.bold = True; r.font.size = Pt(9)
    shade(par, "FFF2B3")


def NEO(text):
    par = doc.add_paragraph()
    r = par.add_run("FILL FROM YOUR NEO4J RUN: " + text); r.font.color.rgb = RGBColor(0xC0, 0x50, 0x00); r.bold = True


def T(headers, rows, widths=None, size=8.5):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(str(h)); r.bold = True; r.font.size = Pt(size)
        shade(c, "DCE6F2")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def IMG(path, width=16, caption=None):
    if Path(path).exists():
        doc.add_picture(str(path), width=Cm(width)); doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if caption:
            c = doc.add_paragraph(caption); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.runs[0].italic = True; c.runs[0].font.size = Pt(8.5)


cap = json.loads((R / "capture_audit.json").read_text())
full = json.loads((R / "compare_full_outputs.json").read_text())
status = list(csv.DictReader(open(R / "compare_status.csv")))
bench = list(csv.DictReader(open(R / "benchmark_summary.csv")))
load = list(csv.DictReader(open(R / "loadtest_summary.csv")))
ws = json.loads((R / "workspace_info.json").read_text())
ind = json.loads((R / "independent_checks.json").read_text())
SETS = {"A": (998, 24755, 6), "B": (147228, 186823, 13), "C": (206978, 6573, 8),
        "D": (237998, 21755, 6), "E": (144228, 183823, 13), "F": (203978, 3573, 8)}

# ------------------------------------------------------------------ title
t = doc.add_heading("Mobile Money Investigations with PostgreSQL and Neo4j", 0)
P("Advanced Big Data Analytics – Project 2 (issued 12 October 2026, due 26 October 2026 23:59 CAT)")
T(["Member", "Student ID", "Main responsibility"],
  [["<Name 1>", "<ID>", "<e.g. capture, PostgreSQL, Q1–Q3>"], ["<Name 2>", "<ID>", "<e.g. Neo4j import, Q4–Q7>"],
   ["<Name 3>", "<ID>", "<e.g. benchmarks, load test, report>"]], [5, 3, 8])
P("GitHub: <URL>   ZIP: <file name>. Full outputs, raw repetitions and plans are in results/ of the code submission.")
par = P("How to use this draft: every number below was produced by the submitted code. PostgreSQL figures come from a "
        "reference run (2 vCPU, 8.4 GB RAM, Linux, PostgreSQL 16.15). Re-run the README steps on your own machine, "
        "rebuild this file with python report/build_report.py, insert the yellow-box screenshots and fill the orange "
        "Neo4j items, then export to PDF. Delete this paragraph before submission.")
shade(par, "F2F2F2")

# ------------------------------------------------------------------ 1
H("1 Capture the data")
H("1.1 Workspace", 2)
pg = ws.get("postgresql_settings", {})
T(["Item", "Value"], [
    ["OS", ws.get("os")], ["CPU (logical / physical)", f"{ws.get('cpu')} ({ws.get('logical_cpus')} / {ws.get('physical_cpus')})"],
    ["RAM", f"{ws.get('ram_gb')} GB"], ["Python / numpy", f"{ws.get('python')} / {ws.get('numpy')}"],
    ["PostgreSQL / psycopg", f"{ws.get('postgresql', '')[:40]} / {ws.get('psycopg')}"],
    ["PostgreSQL memory", f"shared_buffers {pg.get('shared_buffers')}, work_mem {pg.get('work_mem')}, "
                          f"maintenance_work_mem {pg.get('maintenance_work_mem')}, effective_cache_size {pg.get('effective_cache_size')}"],
    ["PostgreSQL TimeZone", pg.get("TimeZone")],
    ["Neo4j / Python driver", ws.get("neo4j", "<Neo4j Community version>") if "neo4j" in ws else "<fill: CALL dbms.components()> / <driver>"],
    ["Neo4j memory", "<fill: heap initial/max, page cache from workspace_info.json>"]], [5, 12])
SHOT("python src/workspace_info.py output plus a successful psql \\conninfo and Neo4j Browser/cypher-shell connection; "
     "SHOW timezone = Africa/Kigali. Taskbar and clock visible.")
H("1.2 capture.py", 2)
P("capture.py imports the unchanged generator as g, prints dataset_info(), FIELDS and ten records of each stream with "
  "itertools.islice, then streams every record through csv.DictWriter (header first, one row at a time). It counts consumed "
  "and written rows, logs every million transfers and keeps the transfer audit totals without storing the stream.")
T(["Stream", "Consumed", "Written", "Expected", "Seconds", "CSV GB"],
  [[k, f"{v['consumed']:,}", f"{v['written']:,}", f"{v['expected']:,}", v["seconds"], v["csv_gb"]] for k, v in cap["streams"].items()]
  + [["Total", f"{cap['total_rows']:,}", "", "20,993,500", cap["total_seconds"], cap["total_csv_gb"]]], [3.5, 2.5, 2.5, 2.5, 2, 2])
a = cap["transfer_audit"]
P(f"Transfer audit: count {a['transfer_count']:,}; earliest occurred_at {a['min_occurred_at']} ({a['min_cat']}); latest "
  f"{a['max_occurred_at']} ({a['max_cat']}); sum amount_rwf {a['sum_amount_rwf']:,} RWF.")
SHOT("python src/capture.py --preview (ten records per stream) and the completed five-stream totals of python src/capture.py.")

# ------------------------------------------------------------------ 2
H("2 Build PostgreSQL")
H("2.1 Tables and constraints", 2)
IMG(R / "diagrams/relational_schema.png", 16, "Figure 1 Relational schema (PK bold, FK arrows)")
T(["Field", "Meaning and unit"], [
    ["customer_id / account_id / device_id", "Integer entity identifiers (primary keys)"],
    ["region", "Owner region: Kigali, Northern, Southern, Eastern, Western"],
    ["role", "Wallet role: person, merchant or agent"], ["access_type", "handset or public_terminal"],
    ["first_day, last_day", "Inclusive observation day numbers, 0 = 1 Sep 2026 CAT … 29 = 30 Sep; CHECK 0 ≤ first ≤ last ≤ 29"],
    ["observations", "Count of observations of that account on that device within the interval; CHECK > 0"],
    ["transfer_id", "BIGINT event identifier, one row per payment"],
    ["sender_id, receiver_id", "Paying and receiving wallets (both FK to accounts)"],
    ["occurred_at", "BIGINT Unix epoch seconds (UTC instant; displayed in Africa/Kigali, UTC+02:00)"],
    ["amount_rwf", "INTEGER whole Rwandan francs; CHECK > 0. A transfer value, not a balance or fee"]], [5, 12])
P("All columns are NOT NULL. Primary keys: each entity/event ID, and (account_id, device_id) for account_devices. Foreign keys: "
  "accounts.customer_id → customers; account_devices.account_id → accounts; account_devices.device_id → devices; "
  "transfers.sender_id and transfers.receiver_id → accounts. Definitions: sql/01_schema.sql and sql/03_constraints_indexes.sql.")
SHOT("\\d+ of the five tables and the constraint list from sql/04_checks.sql (convalidated = t for all 16).")
H("2.2 Bulk load and checks", 2)
P("Loading (\\copy, parents first) took 12.9 s in total (transfers 12.5 s). Keys, foreign keys, checks, the five required "
  "indexes and VACUUM ANALYZE took a further 53.1 s, timed separately (results/pg_load_log.txt, pg_constraints_indexes_log.txt).")
T(["Check", "Result", "Expected"], [
    ["Row counts", "228,000 / 248,000 / 228,600 / 285,600 / 20,003,300", "capture.py counts"],
    ["Audit totals", f"{a['transfer_count']:,}; {a['min_occurred_at']}–{a['max_occurred_at']}; {a['sum_amount_rwf']:,} RWF", "identical"],
    ["Roles", "person 240,000; merchant 6,000; agent 2,000", "same"],
    ["Constraints", "16 constraints, all validated", ""],
    ["Sizes (1 GB = 10^9 B)", "transfers data 1.2057 GB + indexes 2.4335 GB; database 3.7261 GB", ""]], [3.5, 9, 4])
SHOT("sql/04_checks.sql output: counts, audit totals, roles, validated constraints, indexes and sizes.")

# ------------------------------------------------------------------ 3
H("3 Build Neo4j")
H("3.1 Mapping the same facts", 2)
IMG(R / "diagrams/graph_schema.png", 13, "Figure 2 Graph schema")
T(["Source field", "Graph element"], [
    ["customers.customer_id, region", "(:Customer {customer_id:int, region:string})"],
    ["accounts.account_id, role", "(:Account {account_id:int, role:string})"],
    ["accounts.customer_id", "(:Customer)-[:OWNS]->(:Account) via owns.csv (column ignored in Account node file)"],
    ["devices.device_id, access_type", "(:Device {device_id:int, access_type:string})"],
    ["account_devices.*", "(:Account)-[:USED_DEVICE {first_day, last_day, observations}]->(:Device)"],
    ["transfers.*", "(:Account)-[:TRANSFER {transfer_id:long, occurred_at:long, amount_rwf:int}]->(:Account), one per event"]], [6, 11])
H("3.2 Import", 2)
P("prepare_import.py writes temporary copies with typed headers (data bytes streamed, sources unchanged) and derives owns.csv "
  "in (customer_id, account_id) order. Headers: customer_id:ID(Customer),region:string | account_id:ID(Account),:IGNORE,role:string | "
  "device_id:ID(Device),access_type:string | :START_ID(Customer),:END_ID(Account) | :START_ID(Account),:END_ID(Device),first_day:int,"
  "last_day:int,observations:int | transfer_id:long,:START_ID(Account),:END_ID(Account),occurred_at:long,amount_rwf:int.")
par = P("neo4j-admin database import full neo4j --overwrite-destination=true --id-type=integer --nodes=Customer=customers.csv "
        "--nodes=Account=accounts.csv --nodes=Device=devices.csv --relationships=OWNS=owns.csv "
        "--relationships=USED_DEVICE=used_device.csv --relationships=TRANSFER=transfers.csv")
par.runs[0].font.name = "Consolas"; par.runs[0].font.size = Pt(8)
NEO("import seconds; constraint/index setup seconds; store GB (data/databases/neo4j) and transaction-log GB (data/transactions/neo4j).")
T(["Check (cypher/03_checks.cypher)", "Expected", "Neo4j result"], [
    ["Customer / Account / Device nodes", "228,000 / 248,000 / 228,600", ""], ["Total nodes", "704,600", ""],
    ["OWNS / USED_DEVICE / TRANSFER", "248,000 / 285,600 / 20,003,300", ""], ["Total relationships", "20,536,900", ""],
    ["Roles", "person 240,000, merchant 6,000, agent 2,000", ""], ["Accounts without / with >1 owner", "0 / 0", ""],
    ["Distinct transfer_id", "20,003,300", ""], ["Audit totals", f"{a['min_occurred_at']}, {a['max_occurred_at']}, {a['sum_amount_rwf']:,}", ""]], [6, 6, 5])
SHOT("import completion summary; SHOW CONSTRAINTS / SHOW INDEXES (all ONLINE); 03_checks results; then prepare_import.py --clean.")
H("3.3 One account in both models", 2)
P("Account 998 (person) is owned by Customer 998 (Kigali), observed on handset 998 (days 0–29, 39 observations) and its first "
  "outgoing transfer is #113540 to merchant 240004 on 1 Sep 08:43:29 CAT for 2,100 RWF (src/trace_account.py). In SQL each step "
  "is a JOIN on a foreign key (accounts.customer_id, account_devices.account_id/device_id, transfers.sender_id); in Neo4j the same "
  "foreign keys are stored as relationships (OWNS, USED_DEVICE, TRANSFER) that are followed directly from node to node. The "
  "account_devices table and the transfers table become relationships with properties. Account 998 paid account 1111 nine "
  "separate times (and 63 seven times). Collapsing repeats into one edge would erase each transfer_id, its timestamp and amount, "
  "so Q1 counts, Q2 daily totals, the strict time order and 600 s gaps of Q5 and the amount rule of Q5/Q6 could no longer be evaluated.")
SHOT("trace_account.py output: SQL JOIN row and Cypher MATCH row side by side (identical values).")

# ------------------------------------------------------------------ 4
H("4 Routine business questions")
P("Hour windows: 09:45:00 inclusive to 10:45:00 exclusive CAT, converted in Python (queries.hour_bounds). All queries are in "
  "src/queries.py, with readable copies in sql/queries and cypher/queries.")
H("4.1 Q1 Account activity", 2)
rows = []
for s, (acc, dest, day) in SETS.items():
    c, v = full[f"Q1-{s}"]["pg"][0]
    rows.append([s, acc, f"{day} Sep", c, f"{v:,}", "MATCH" if any(r["case"] == f"Q1-{s}" and r["status"] == "MATCH" for r in status) else ""])
T(["Set", "Account", "Date", "Outgoing count", "Total RWF", "SQL = reference"], rows)
P("Outgoing value is not a balance: it ignores incoming transfers, the opening balance, cash-in/cash-out at agents, fees and "
  "reversals, none of which are in these records.")
SHOT("SQL and Cypher Q1 results for all six sets (one consolidated screenshot).")
H("4.2 Q2 Daily activity", 2)
IMG(R / "charts/q2_daily.png", 16, "Figure 3 Daily transfer count and value (CAT days)")
q2 = full["Q2-month"]["pg"]
P(f"30 days returned; counts sum to {sum(r[1] for r in q2):,} and values to {sum(r[2] for r in q2):,} RWF, reconciling exactly "
  "with the capture audit. Pattern: count is almost flat (≈666,667 per day from 06:00 to 22:00 CAT), but 6–15 September carry "
  "~150–330 extra transfers per day and up to +190 million RWF (14–15 Sep 7.86 bn vs about 7.67–7.70 bn on other days). These "
  "extra large-value transfers are the scenario payments examined in Section 5. Transfer value is not provider revenue: revenue "
  "comes from fees, and value counts money that merely moves (and may move several times) between wallets.")
SHOT("Q2 SQL and Cypher results (30 rows), the reconciliation check and the chart.")
H("4.3 Q3 Shared devices", 2)
rows = []
for s in SETS:
    rs = full[f"Q3-{s}"]["pg"]
    rows.append([s, SETS[s][0], len(rs), "; ".join(f"{r[0]}@{r[1]} [{r[3]},{r[4]}]" for r in rs)])
T(["Set", "Account", "Rows", "other account @ device [overlap days] (all handsets)"], rows, [1, 2, 1.2, 13], 7.5)
P("Legitimate sharing: account 998 and account 220998 share handset 998 for days 0–29 because both wallets belong to Customer "
  "998 (a secondary wallet on the owner's phone); B's handset 147226 is a household phone also used by accounts 147226–147230. "
  "Overlap only means both accounts were observed on the device at some point within the overlapping days, not at the same "
  "moment: intervals [2,7] and [5,11] overlap on [5,7] even if one person used the phone in the morning and another at night.")
SHOT("Q3 results/counts for all six sets in both engines.")

# ------------------------------------------------------------------ 5
H("5 Connected accounts")
H("5.1 Q4 Ownership and device network", 2)
rows = []
for s in SETS:
    for d in (4, 6, 8, 10):
        rs = full[f"Q4-{s}-d{d}"]["pg"]
        rows.append([s, d, sum(r[1] for r in rs), ", ".join(f"{r[0]} {r[1]}" for r in rs)])
T(["Set", "Links", "Accounts", "By owner region"], rows, [1.2, 1.2, 2, 12.5], 7.5)
IMG(R / "charts/q4_count_vs_depth.png", 12, "Figure 4 Accounts reached versus depth")
par = P("[Record the prediction your group made after seeing depths 4 and 6, BEFORE running 8 and 10, and compare it here.] ")
shade(par, "FFF2E0")
P("Measured totals: A 10→43→175→187, B 46→178→188→228, C 146→483→832→1,433, D 10→44→180→192, E 47→183→193→230, "
  "F 147→488→837→1,426. A, B, D and E grow sharply once and then "
  "level off; C and F keep growing roughly threefold every two links because their early neighbourhood already includes "
  "a household phone and a replacement handset, each opening further households. Supporting "
  "path (Figure 5): Account 998 – Device 228001 – Account 24755 – Device 24751 – Account 24751 (four links). Deeper links add "
  "weak associations: by 8–10 links an account is connected only because a phone was shared by a household member of someone "
  "who shared a different phone with a third person; no single observation links it to the review account.")
IMG(R / "diagrams/q4_network_A_depth4.png", 14, "Figure 5 Ownership/device network of set A within four links")
SHOT("all 24 Q4 comparisons (SQL vs Cypher), the plot and one supporting path from Neo4j (Q4_PATH_CYPHER in queries.py).")
H("5.2 Q5 Rapid onward payments", 2)
rows = [[s, len(full[f"Q5-{s}"]["pg"]), "; ".join(str(tuple(r)) for r in full[f"Q5-{s}"]["pg"]) or "none"] for s in SETS]
T(["Set", "Chains", "(t1, t2, t3, final receiver)"], rows, [1.2, 1.5, 14])
IMG(R / "diagrams/q5_chain_B.png", 15, "Figure 6 Set B chain")
P("Example (B): #20000092 147228→155147 at 13 Sep 10:00:17 CAT for 1,050,000 RWF; #20000093 155147→163066 at 10:00:57 for "
  "1,029,000 (98%); #20000094 163066→170985 at 10:01:37 for 1,008,420 (98%). The chain does not prove the same funds moved: "
  "wallets are fungible, each intermediary may already have held enough balance, and similar amounts 40 s apart can be "
  "coincidental or ordinary (e.g. paying a supplier after being paid). Without balances, the data cannot trace specific money.")
SHOT("six matching Q5 counts in both engines and the B chain with IDs, CAT times and amounts.")
H("5.3 Q6 Circular payments", 2)
rows = [[s, len(full[f"Q6-{s}"]["pg"]), "; ".join(f"{list(r[0])} (len {r[1]})" for r in full[f"Q6-{s}"]["pg"]) or "none"] for s in SETS]
T(["Set", "Cycles", "Transfer-ID sequence"], rows, [1.2, 1.5, 14])
IMG(R / "diagrams/q6_cycle_A.png", 15, "Figure 7 Set A cycle")
P("A: 998→8917→16836→24755→998 on 6 Sep between 10:00:00 and 10:02:00 CAT, 200,000 → 196,000 → 192,080 → 188,238 RWF. C: a "
  "six-transfer cycle 206978→…→6573→206978 on 8 Sep 10:00:42–10:04:02, 300,000 falling 2% per hop to 271,176 RWF. Further "
  "evidence to request: wallet balances before and after, KYC/identity and relationship of the four owners, the device and "
  "location that initiated each payment, fees charged, any cash-out at agents afterwards and the history of this group in "
  "other months.")
SHOT("six Q6 counts in both engines and one cycle.")
H("5.4 Q7 Shortest transfer connection", 2)
pc = json.loads((R / "q7_path_checks.json").read_text())
rows = []
for s in SETS:
    l4, l6 = full[f"Q7-{s}-b4"]["pg"][0][0], full[f"Q7-{s}-b6"]["pg"][0][0]
    path = pc.get(f"Q7-{s}-b6", {}).get("pg_path", {})
    rows.append([s, SETS[s][0], SETS[s][1], l4 if l4 is not None else "no route ≤4", l6 if l6 is not None else "no route ≤6",
                 " → ".join(map(str, path.get("accounts", []))), "valid" if path.get("valid") else ""])
T(["Set", "From", "To", "Bound 4", "Bound 6", "One supporting path (SQL)", "Check"], rows, [1, 1.6, 1.6, 1.8, 1.8, 8, 1.2], 7.5)
P("Every path was checked hop by hop: a stored transfer exists in that direction (example transfer_id recorded), both accounts "
  "are persons, the hops are contiguous and their number equals the minimum (results/q7_path_checks.json). B's SQL path "
  "(147228→147793→147197→148101→178904→186823) differs from the scenario route but is equally short, illustrating that "
  "shortest paths are not unique. No route within four transfers only means no connection that short among person accounts; "
  "longer routes, routes through merchants/agents, cash, or other providers are not excluded. A structural route ignores time "
  "and amount, so its transfers may run backwards in time (as in the brief's teaching example) and need not carry the same funds.")
IMG(R / "diagrams/q7_route_B.png", 16, "Figure 8 One shortest person-only route for set B")
SHOT("all 12 length comparisons and path checks (results/compare_status.csv and q7_path_checks.json).")

# ------------------------------------------------------------------ 6
H("6 Correctness and performance")
H("6.1 Comparison program", 2)
n_ok = sum(r["status"] == "MATCH" for r in status)
P(f"compare.py calls run_pg and run_neo, normalizes integers/dates/lists, sorts and compares exactly; Q7 lengths are compared "
  f"separately from supporting-path validity. In the reference run all {n_ok}/61 PostgreSQL results equal the independent "
  "pandas answers (reference_answers.py), for both the baseline and improved Q7. Independent CSV checks (independent_checks.py): "
  f"overlap of 998 and 220998 on device 998 = days [{ind['overlap']['overlap_start']},{ind['overlap']['overlap_end']}] (pass); "
  f"Q5 chain A all checks {ind['chain_Q5']['all_pass']}; Q6 cycle A all checks {ind['cycle_Q6']['all_pass']}.")
counts = {}
for r in status:
    counts.setdefault(r["question"], [0, 0]); counts[r["question"]][0] += 1; counts[r["question"]][1] += r["status"] == "MATCH"
T(["Question", "Cases", "PostgreSQL = reference", "Neo4j = PostgreSQL"], [[q, c[0], c[1], "<fill>"] for q, c in counts.items()]
  + [["Total", 61, n_ok, "<fill>"]])
NEO("run python src/compare.py with both services up; paste the 61-case table; describe and resolve any mismatch.")
SHOT("61-case status table and the independent CSV checks.")
H("6.2 Timing a fixed selection", 2)
rows = []
for b in bench:
    if b["variant"] == "pg":
        imp = next((x for x in bench if x["variant"] == "pg-improved" and x["case"] == b["case"]), None)
        rows.append([b["case"], b["median_ms"], b["min_ms"], b["max_ms"], imp["median_ms"] if imp else "", "", ""])
T(["Case", "PG median ms", "PG min", "PG max", "PG improved median", "Neo4j median ms", "PG/Neo ratio"], rows, size=7.5)
IMG(R / "charts/benchmark_medians.png", 16, "Figure 9 Median query time per case (log scale)")
P("Plans (results/plans): Q2 is a parallel sequential scan of 20 M rows with hash aggregation (≈4.3 s); Q4 B depth 10 runs in "
  "8 ms because the recursive term only touches a few hundred index entries. Baseline Q7 B bound 6: the Recursive Union processes "
  "187,957 frontier rows, fetches 14.6 million transfer index entries and keeps 427,955 rows after UNION de-duplication, "
  "26.8 s in total; the planner estimated 314 rows per iteration against 1.45 million actual. Neo4j's shortestPath instead "
  "runs a bidirectional breadth-first search that stops when the frontiers meet.")
NEO("21 Neo4j medians and ratios (benchmark.py --summarize) and PROFILE of Q2, Q4 B d10, Q7 B b6; explain one processing difference.")
SHOT("benchmark summary, EXPLAIN (ANALYZE, BUFFERS) and PROFILE plans.")
H("6.3 One SQL improvement", 2)
P("Wasted work identified from the plan: each frontier account re-reads every parallel transfer (78 per sender on average), "
  "accounts already reached are expanded again at later depths, and the search explores 6 levels from one side only. "
  "Prediction: searching from both ends over distinct person neighbours (forward ⌈b/2⌉, backward ⌊b/2⌋, minimum df+db where "
  "they meet) should cut the explored states from ~16^6 to ~2×16^3 and give a 100× or better speed-up. Result: all 12 Q7 cases "
  "still match; B/E bound 4 fell from 405/277 ms to 6.7/6.4 ms and bound 6 from 22,635/22,758 ms to 46.6/50.4 ms (≈450×). "
  "The improved version is selected for Section 7 and the final comparison. Both versions are kept (Q7_SQL, Q7_SQL_IMPROVED).")
SHOT("12-case recheck, the four revised timings and before/after plans (pg_Q7_B_bound6.txt vs pg_Q7_B_bound6_improved.txt).")

# ------------------------------------------------------------------ 7
H("7 Concurrent requests")
H("7.1 Load test", 2)
P("loadtest.py starts one process per client with its own persistent connection, warms up A-B-C once, synchronizes on a "
  "multiprocessing Barrier whose action sets the common start time, starts cycles until start+15 s, finishes the started cycle "
  "and logs each request; correctness is checked after timing. Medians of three repetitions:")
rows = [[r["engine"], r["workload"], r["clients"], r["throughput_rps"], r["median_ms"], r["p95_ms"], r["errors"], r["timeouts"], r["incorrect"]]
        for r in load]
T(["Engine", "Workload", "Clients", "Throughput req/s", "Median ms", "p95 ms", "Errors", "Timeouts", "Incorrect"], rows, size=8)
NEO("the eight Neo4j combinations (python src/loadtest.py --engine neo, then --summarize).")
SHOT("active client processes during a run and all 16 combination summaries.")
H("7.2 Scaling", 2)
IMG(R / "charts/loadtest_scaling.png", 16, "Figure 10 Throughput and p95 against client count")
P("On the 2-vCPU reference machine PostgreSQL throughput rises from 1 to 4 clients (Q4 d10 ≈82 → ≈153 req/s; Q7 b6 ≈23 → "
  "≈44 req/s) and is flat from 4 to 16 clients, while p95 grows roughly in proportion to clients (Q4 ≈30 → ≈245 ms; Q7 ≈58 → "
  "≈459 ms). Both CPUs are saturated, so extra clients only queue: throughput (system capacity) stops improving while each "
  "individual response gets slower. No errors or timeouts occurred and every completion was correct. Repeat on your machine "
  "and compare with Neo4j before claiming whether any graph advantage survives the SQL improvement.")
NEO("1 vs 16 client comparison for Neo4j, CPU/memory evidence (Task Manager/htop) and whether a graph advantage remains.")

# ------------------------------------------------------------------ 8
H("8 Decisions")
H("8.1 Investigation priority", 2)
T(["Pair", "Q3 devices", "Q4 network (10 links)", "Q5 / Q6", "Q7 (bound 6)", "Review first"], [
    ["A / D", "Both share a handset with their 3 group members for days 0–29 plus an own-customer wallet",
     "A 187, D 192 accounts", "A: 1 chain + 4-transfer cycle (200,000 RWF, 2 min); D: none", "A 3, D 3", "A"],
    ["B / E", "Both: household phone (5 customers) + group device", "B 228, E 230", "B: 1 chain of 1,050,000 RWF in 80 s; E: none",
     "B 5, E 5", "B"],
    ["C / F", "Both: household phone (one member joined it on day 11 after a phone replacement) + group device", "C 1,433, F 1,426",
     "C: 1 chain + 6-transfer cycle (300,000 RWF, 3 min 20 s); F: none", "C 5, F 5", "C"]], [1.3, 4, 2.6, 4.5, 1.8, 1.6], 7.5)
P("Detailed pair A/D. Device and network evidence cannot separate them: each shares one handset with exactly its three group "
  "members for the whole month and reaches a similar number of accounts. The transfers differ. A sent 200,000 RWF to 8917 at "
  "10:00:00 on 6 Sep; it moved on to 16836 (196,000) and 24755 (192,080) 40 s apart and returned to A as 188,238 RWF at "
  "10:02:00 – a cycle losing 2% per hop. D's group passed 45,000 RWF around the same four-account loop (20001651–20001654) but "
  "two days apart (6, 8, 10 and 12 Sep) with equal amounts, which fails the 600 s and 1,800 s windows and looks like a "
  "rotating savings group (ikimina) or family support. A is reviewed first.")
P("Ordinary explanation for A: four colleagues using one shop phone might pass a float between them to settle a joint purchase, "
  "each keeping a 2% commission. Missing evidence – balances, KYC links between owners, who initiated each payment, what happened "
  "to the 188,238 RWF afterwards – could confirm this (raising no concern) or show money returning to its origin after layering "
  "(raising priority). These records justify enquiries, not a finding of fraud.")
IMG(R / "diagrams/q6_cycle_A.png", 13, "Figure 11 Transfer cycle for A (from Section 5.3)")
IMG(R / "diagrams/q4_network_D_depth4.png", 13, "Figure 12 Ownership–device network for D within four links")
H("8.2 Model recommendation (≤500 words)", 2)
par = P("[Write after your Neo4j results are in. Structure to follow: (1) Reporting (Q1–Q2): evidence from Q2 timings, plan "
        "(parallel seq scan + hash aggregate vs relationship scan) and load/storage (PG load 12.9 s + 53.1 s setup, 3.73 GB vs "
        "Neo4j import/setup seconds and store GB). (2) Traversal (Q4–Q7): Cypher patterns are shorter and the native shortest "
        "path avoided the 22.6 s baseline SQL, but the improved SQL (≈50 ms) shows much of the gap was algorithm, not model – "
        "separate graph-modelling benefits (relationships stored as adjacency, readable variable-length patterns) from "
        "implementation effects (bidirectional BFS, pruning var-expand). (3) Concurrency: compare saturation points. Include "
        "evidence against your choice. Propose a freshness target for copying operational data to the graph (e.g. ≤15 minutes "
        "via change-data capture) and the consequence of stale data (missed chains/cycles involving the newest transfers). State "
        "two limits: one synthetic month on one machine; no write workload or replication measured.]")
shade(par, "FFF2E0")
H("8.3 Individual judgement", 2)
par = P("Each member writes 150–200 words in their own name on a different measured finding, its explanation and a check that "
        "could overturn it (e.g. Member 1: Q7 baseline vs improved SQL; Member 2: load-test saturation at 4 clients; "
        "Member 3: Q4 growth with depth). Do not reuse text from this draft.")
shade(par, "FFF2E0")
T(["Member", "Contributions", "LLM / external assistance and how it was checked"],
  [["<Name 1>", "", ""], ["<Name 2>", "", ""], ["<Name 3>", "",
   "e.g. Claude (Anthropic) used to draft code and this report skeleton; every query re-run, answers verified against "
   "independent pandas results and CSV rows; Neo4j queries tested by the group."]], [3, 6, 8])

# ------------------------------------------------------------------ 9
H("9 Reproducibility")
P("README.md lists every command in execution order; .env.example holds placeholder secrets; CSVs and database stores stay "
  "local. verify_generator.py confirms the generator SHA-256 2ea0e59d…455a is unchanged.")
SHOT("final rerun of python src/compare.py (61 cases complete) and both services stopped (pg_ctl status / neo4j status).")

out = ROOT / "report" / "Project2_Report_DRAFT.docx"
doc.save(out)
print("saved", out)

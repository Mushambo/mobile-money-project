"""Charts for the report (results/charts/*.png). Each chart is drawn only if its input exists.
    python src/plots.py
Inputs: compare_full_outputs.json (Q2, Q4), benchmark_summary.csv, loadtest_summary.csv."""
import csv
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402

OUT = RESULTS_DIR / "charts"
C = {"pg": "#336791", "pg-improved": "#5fa8d3", "neo": "#018bff", "A": "#1b9e77", "B": "#d95f02",
     "C": "#7570b3", "D": "#66a61e", "E": "#e7298a", "F": "#a6761d"}
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def _full():
    f = RESULTS_DIR / "compare_full_outputs.json"
    return json.loads(f.read_text()) if f.exists() else None


def daily():
    full = _full()
    if not full:
        return
    rows = full["Q2-month"].get("pg") or full["Q2-month"].get("neo") or full["Q2-month"].get("ref")
    days = [date.fromisoformat(r[0]) for r in rows]
    counts = [r[1] for r in rows]
    values = [r[2] / 1e9 for r in rows]
    fig, ax1 = plt.subplots(figsize=(8, 3.6))
    ax1.bar(days, counts, color="#9ecae1", label="Transfers (count)")
    ax1.set_ylabel("Transfers per CAT day (count)")
    ax1.set_ylim(min(counts) * 0.995, max(counts) * 1.002)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax2 = ax1.twinx()
    ax2.plot(days, values, color="#d95f02", marker="o", ms=3, label="Value (billion RWF)")
    ax2.set_ylabel("Transfer value per day (billion RWF)")
    ax1.set_title("Q2 Daily transfer activity, September 2026 (CAT)")
    fig.autofmt_xdate()
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, loc="lower center", ncol=2, frameon=False)
    fig.savefig(OUT / "q2_daily.png"); plt.close(fig)


def q4_depth():
    full = _full()
    if not full:
        return
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for s in "ABCDEF":
        ys = []
        for d in (4, 6, 8, 10):
            rows = full[f"Q4-{s}-d{d}"].get("pg") or full[f"Q4-{s}-d{d}"].get("ref")
            ys.append(sum(r[1] for r in rows))
        ax.plot((4, 6, 8, 10), ys, marker="o", color=C[s], label=f"Set {s}")
    ax.set_xticks((4, 6, 8, 10)); ax.set_xlabel("Maximum links (OWNS / USED_DEVICE)")
    ax.set_ylabel("Distinct other accounts reached")
    ax.set_title("Q4 Accounts reached versus search depth")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "q4_count_vs_depth.png"); plt.close(fig)


def bench():
    f = RESULTS_DIR / "benchmark_summary.csv"
    if not f.exists():
        return
    rows = [r for r in csv.DictReader(open(f)) if r["median_ms"]]
    cases = list(dict.fromkeys(r["case"] for r in rows if r["variant"] in ("pg", "neo")))
    variants = [v for v in ("pg", "pg-improved", "neo") if any(r["variant"] == v for r in rows)]
    fig, ax = plt.subplots(figsize=(10, 4))
    width = 0.8 / len(variants)
    for i, v in enumerate(variants):
        xs, ys = [], []
        for j, c in enumerate(cases):
            m = [float(r["median_ms"]) for r in rows if r["variant"] == v and r["case"] == c]
            if m:
                xs.append(j + i * width); ys.append(m[0])
        ax.bar(xs, ys, width, color=C[v], label={"pg": "PostgreSQL", "pg-improved": "PostgreSQL (improved Q7)",
                                                  "neo": "Neo4j"}[v])
    ax.set_yscale("log"); ax.set_ylabel("Median of 5 runs (ms, log scale)")
    ax.set_xticks([j + width * (len(variants) - 1) / 2 for j in range(len(cases))])
    ax.set_xticklabels(cases, rotation=60, ha="right")
    ax.set_title("Section 6.2 Median query time per case")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(OUT / "benchmark_medians.png"); plt.close(fig)


def load():
    f = RESULTS_DIR / "loadtest_summary.csv"
    if not f.exists():
        return
    rows = list(csv.DictReader(open(f)))
    fig, axes = plt.subplots(2, 2, figsize=(9, 6))
    for col, wl in enumerate(("q4d10", "q7b6")):
        for e in ("pg", "neo"):
            rs = sorted((r for r in rows if r["engine"] == e and r["workload"] == wl), key=lambda r: int(r["clients"]))
            if not rs:
                continue
            x = [int(r["clients"]) for r in rs]
            name = "PostgreSQL" if e == "pg" else "Neo4j"
            axes[0][col].plot(x, [float(r["throughput_rps"]) for r in rs], marker="o", color=C[e], label=name)
            axes[1][col].plot(x, [float(r["p95_ms"]) for r in rs], marker="o", color=C[e], label=name)
        title = {"q4d10": "Q4 depth 10", "q7b6": "Q7 length-only bound 6"}[wl]
        axes[0][col].set_title(f"{title}: throughput"); axes[0][col].set_ylabel("Correct requests / s")
        axes[1][col].set_title(f"{title}: p95 latency"); axes[1][col].set_ylabel("p95 latency (ms)")
        for r in (0, 1):
            axes[r][col].set_xticks(list(range(0, 17, 4))); axes[r][col].set_xlabel("Concurrent clients")
            axes[r][col].legend(frameon=False)
    fig.tight_layout(); fig.savefig(OUT / "loadtest_scaling.png"); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (daily, q4_depth, bench, load):
        fn()
    print("charts in", OUT, sorted(p.name for p in OUT.glob("*.png")))

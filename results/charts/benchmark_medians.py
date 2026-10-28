from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
CHARTS = RESULTS / "charts"

SUMMARY = RESULTS / "benchmark_summary.csv"
RAW = RESULTS / "benchmark_raw.csv"

CHARTS.mkdir(parents=True, exist_ok=True)

if not SUMMARY.exists():
    raise FileNotFoundError(f"Benchmark summary not found: {SUMMARY}")

df = pd.read_csv(SUMMARY)

required = {"variant", "case", "median_ms"}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing required columns: {sorted(missing)}")

df["median_ms"] = pd.to_numeric(df["median_ms"], errors="coerce")
df["variant"] = df["variant"].astype(str).str.lower()
df["case"] = df["case"].astype(str)

# Keep actual, positive measured medians only.
valid = df[
    df["median_ms"].notna()
    & (df["median_ms"] > 0)
    & df["variant"].isin(["pg", "neo"])
].copy()

if valid.empty:
    raise ValueError("No valid PostgreSQL/Neo4j median measurements found.")

# Pivot actual measurements by query/case and database engine.
pivot = valid.pivot_table(
    index="case",
    columns="variant",
    values="median_ms",
    aggfunc="median"
)

# Prefer PostgreSQL first, then Neo4j.
order = [v for v in ["pg", "neo"] if v in pivot.columns]
pivot = pivot[order]

def draw_chart(log_scale=False):
    ax = pivot.plot(
        kind="bar",
        figsize=(max(12, len(pivot) * 0.65), 6),
        width=0.8
    )

    ax.set_title(
        "PostgreSQL vs Neo4j: Median Query Execution Time"
        + (" (Log Scale)" if log_scale else "")
    )
    ax.set_xlabel("Query / Benchmark Case")
    ax.set_ylabel("Median execution time (ms)")
    ax.legend(
        [name.upper() for name in pivot.columns],
        title="Engine"
    )

    if log_scale:
        ax.set_yscale("log")

    ax.tick_params(axis="x", labelrotation=45)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    plt.tight_layout()

    filename = (
        "benchmark_medians_log.png"
        if log_scale else "benchmark_medians.png"
    )
    output = CHARTS / filename
    plt.savefig(output, dpi=160, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {output}")

draw_chart(log_scale=False)
draw_chart(log_scale=True)

# Save the plotted measurements for later review.
pivot.to_csv(CHARTS / "benchmark_medians_summary.csv")
print(f"Summary saved: {CHARTS / 'benchmark_medians_summary.csv'}")

# Report missing/timeout cases rather than displaying them as zero.
print("\nCases with unavailable median measurements:")
unavailable = df[
    df["median_ms"].isna()
    & df["variant"].isin(["pg", "neo"])
]
if unavailable.empty:
    print("None")
else:
    cols = [
        c for c in
        ["variant", "case", "completed", "timeouts", "errors"]
        if c in unavailable.columns
    ]
    print(unavailable[cols].to_string(index=False))

# Optional data-quality information from raw benchmark runs.
if RAW.exists():
    raw = pd.read_csv(RAW)
    print("\nRaw benchmark data:")
    print(f"Total recorded runs: {len(raw)}")

    if "status" in raw.columns:
        print("Run statuses:")
        print(raw["status"].value_counts(dropna=False).to_string())

    if "correct" in raw.columns:
        print("\nCorrectness counts:")
        print(raw["correct"].value_counts(dropna=False).to_string())

print("\nBenchmark chart generation completed.")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
from update_transform_log import update_transform_log

DATASETS = {
    # name: (input path, require a positive ClosePrice?)
    "listings": (r'cleaned_raw_listing_data.csv', False),   # listings may not have closed yet
    "sold": (r'cleaned_raw_sold_data.csv', True),
}
OUTPUT_DIR = r"week_2_final_deliverables"

RESIDENTIAL_TYPES = {"residential"}

NULL_FLAG_THRESHOLD = 90.0      # percent
DROP_HIGH_NULL_COLS = False     # True = also drop flagged columns from the saved CSV
NUMERIC_COLS = ["ClosePrice", "LivingArea", "DaysOnMarket"]
PERCENTILES = [0.01, 0.05, 0.10, 0.25, 0.75, 0.90, 0.95, 0.99]
# --------------------------------------------------------------------------

pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 50)


class Report:
    """Collects printed output so it can also be written to a text file."""

    def __init__(self):
        self.lines = []

    def __call__(self, text=""):
        print(text)
        self.lines.append(str(text))

    def save(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines) + "\n")


def null_summary(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    out = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "null_count": df.isna().sum(),
        "null_pct": (df.isna().sum() / n * 100).round(2) if n else 0.0,
        "non_null_count": df.notna().sum(),
        "n_unique": df.nunique(dropna=True),
    })
    out["flag_over_threshold"] = out["null_pct"] > NULL_FLAG_THRESHOLD
    out.index.name = "column"
    return out.sort_values("null_pct", ascending=False)


def numeric_summary(df: pd.DataFrame, cols) -> pd.DataFrame:
    rows = {}
    for c in cols:
        if c not in df:
            continue
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if s.empty:
            rows[c] = {"count": 0}
            continue
        d = {"count": len(s), "min": s.min(), "max": s.max(),
             "mean": s.mean(), "median": s.median(), "std": s.std()}
        for p in PERCENTILES:
            d[f"p{int(p * 100)}"] = s.quantile(p)
        rows[c] = d
    cols_order = (["count", "min", "p1", "p5", "p10", "p25", "median", "mean",
                   "p75", "p90", "p95", "p99", "max", "std"])
    return pd.DataFrame(rows).T.reindex(columns=cols_order)


def process(name: str, path: str, require_close_price: bool) -> None:
    rep = Report()
    rep("=" * 78)
    rep(f"{name.upper()}  ({path})")
    rep("=" * 78)

    df = pd.read_csv(path, low_memory=False)
    raw_rows = len(df)
    nulls_before = null_summary(df)   # raw null profile, kept for before/after comparison
    rep(f"Loaded {raw_rows:,} rows x {df.shape[1]} columns")

    # ---- 1. unique property types ----
    rep("\n[1] UNIQUE PROPERTY TYPES FOUND")
    if "PropertyType" not in df:
        raise KeyError(f"PropertyType column missing from {path}")
    pt_clean = df["PropertyType"].astype("string").str.strip()
    counts = pt_clean.fillna("(missing)").value_counts()
    keep_flag = {v: (v.lower() in RESIDENTIAL_TYPES) for v in counts.index}
    pt_table = pd.DataFrame({
        "count": counts,
        "pct": (counts / raw_rows * 100).round(2),
        "kept": [keep_flag[v] for v in counts.index],
    })
    rep(pt_table.to_string())

    # ---- 2. filtering logic ----
    rep("\n[2] FILTERING LOGIC (applied in order)")
    steps = []

    def apply(label, mask):
        nonlocal df
        before = len(df)
        df = df[mask(df)].copy()
        steps.append((label, before, len(df), before - len(df)))

    apply(f"PropertyType in {sorted(RESIDENTIAL_TYPES)} (case-insensitive, trimmed)",
          lambda d: d["PropertyType"].astype("string").str.strip().str.lower()
                     .isin(RESIDENTIAL_TYPES).fillna(False))
    if require_close_price and "ClosePrice" in df:
        apply("ClosePrice is non-null and > 0 (closed sales only)",
              lambda d: pd.to_numeric(d["ClosePrice"], errors="coerce") > 0)
    if "LivingArea" in df:
        apply("Remove impossible LivingArea (<= 0); nulls retained",
              lambda d: ~(pd.to_numeric(d["LivingArea"], errors="coerce") <= 0))
    if "DaysOnMarket" in df:
        apply("Remove negative DaysOnMarket (< 0); nulls retained",
              lambda d: ~(pd.to_numeric(d["DaysOnMarket"], errors="coerce") < 0))

    attrition = pd.DataFrame(steps, columns=["filter", "rows_before", "rows_after", "rows_removed"])
    rep(attrition.to_string(index=False))
    rep(f"\nTotal: {raw_rows:,} -> {len(df):,} rows "
        f"({len(df) / raw_rows * 100:.1f}% retained)" if raw_rows else "No rows loaded")

    # ---- 3. null summary ----
    nulls_after = null_summary(df)
    rep("\n[3] NULL-COUNT SUMMARY (after filtering; all columns, sorted by % null)")
    rep(nulls_after.to_string())

    # ---- 4. missing value report ----
    rep(f"\n[4] MISSING VALUE REPORT: columns > {NULL_FLAG_THRESHOLD:.0f}% null")
    flagged_after = nulls_after[nulls_after["flag_over_threshold"]]
    flagged_before = nulls_before[nulls_before["flag_over_threshold"]]
    if flagged_after.empty:
        rep("None after filtering.")
    else:
        rep(flagged_after[["dtype", "null_count", "null_pct"]].to_string())
    only_before = sorted(set(flagged_before.index) - set(flagged_after.index))
    only_after = sorted(set(flagged_after.index) - set(flagged_before.index))
    if only_before:
        rep(f"\nFlagged in raw data but NOT after filtering: {only_before}")
    if only_after:
        rep(f"Newly flagged after filtering: {only_after}")
    rep(f"\nTotal flagged (filtered data): {len(flagged_after)} of {df.shape[1]} columns")

    # ---- 5. numeric distribution ----
    rep("\n[5] NUMERIC DISTRIBUTION SUMMARY (filtered data, non-null values)")
    num = numeric_summary(df, NUMERIC_COLS)
    rep(num.to_string(float_format=lambda x: f"{x:,.1f}"))
    missing_cols = [c for c in NUMERIC_COLS if c not in df]
    if missing_cols:
        rep(f"\n[warn] columns not found: {missing_cols}")

    # ---- 6. save ----
    out = df
    if DROP_HIGH_NULL_COLS and not flagged_after.empty:
        out = df.drop(columns=flagged_after.index.tolist())
        rep(f"\nDropped {len(flagged_after)} high-null columns from saved CSV")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = f"residential_{name}.csv"
    df_name = out_path.replace('_', ' ').replace('.csv','') + 'data'
    out.to_csv(out_path, index=False)
    update_transform_log(df = out, name = df_name, action = f'Residential Only Data & Drop Columns with 90%+ Null from {name}', destination = out_path)

    nulls_after.to_csv(os.path.join(OUTPUT_DIR, f"{name}_null_summary.csv"))
    num.to_csv(os.path.join(OUTPUT_DIR, f"{name}_numeric_summary.csv"))
    rep(f"\n[6] SAVED: {out_path}  ({len(out):,} rows x {out.shape[1]} columns)")
    rep.save(os.path.join(OUTPUT_DIR, f"{name}_report.txt"))


if __name__ == "__main__":
    for ds_name, (ds_path, need_close) in DATASETS.items():
        if not os.path.exists(ds_path):
            print(f"[skip] {ds_path} not found", file=sys.stderr)
            continue
        process(ds_name, ds_path, need_close)
        print()

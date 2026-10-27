import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def numeric_summary_plots(df, output_dir=r"week_2_final_deliverables"):
    import os
    os.makedirs(output_dir, exist_ok=True)

    numeric_cols = df.select_dtypes(include=np.number).columns

    # Percentile summary
    percentile_summary = []

    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()

        if len(s) == 0:
            continue

        percentile_summary.append({
            "column": col,
            "count": len(s),
            "min": s.min(),
            "p1": s.quantile(0.01),
            "p5": s.quantile(0.05),
            "p25": s.quantile(0.25),
            "median": s.quantile(0.50),
            "p75": s.quantile(0.75),
            "p95": s.quantile(0.95),
            "p99": s.quantile(0.99),
            "max": s.max(),
            "mean": s.mean(),
            "std": s.std(),
            "missing_pct": df[col].isna().mean() * 100
        })

        # Histogram
        plt.figure(figsize=(8, 4))
        sns.histplot(s, bins=30)
        plt.title(f"Histogram: {col}")
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{col}_hist.png")
        plt.close()

        # Boxplot
        plt.figure(figsize=(8, 2))
        sns.boxplot(x=s)
        plt.title(f"Boxplot: {col}")
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{col}_box.png")
        plt.close()

    percentile_df = pd.DataFrame(percentile_summary)
    percentile_df.to_csv(
        f"{output_dir}/percentile_summary.csv",
        index=False
    )

    return percentile_df

# EDA for listings and sold MLS data

LISTINGS_PATH = "listings.csv"
SOLD_PATH = "sold.csv"

NEEDED_COLS = [
    "PropertyType", "PropertySubType", "CountyOrParish",
    "ClosePrice", "ListPrice", "OriginalListPrice", "DaysOnMarket",
    "ListingContractDate", "PurchaseContractDate", "CloseDate",
]
DATE_COLS = ["ListingContractDate", "PurchaseContractDate", "CloseDate"]
MIN_COUNTY_SALES = 30   # ignore counties with fewer rows when ranking
TOP_N_COUNTIES = 10


def load(path: str) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns
    cols = [c for c in NEEDED_COLS if c in header]
    missing = sorted(set(NEEDED_COLS) - set(cols))
    if missing:
        print(f"  [warn] columns not found in {path}: {missing}")
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    for c in DATE_COLS:
        if c in df:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in ["ClosePrice", "ListPrice", "OriginalListPrice", "DaysOnMarket"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def property_type_share(df: pd.DataFrame) -> None:
    section("1. Residential vs. other property type share")
    if "PropertyType" not in df:
        print("PropertyType not available")
        return
    pt = df["PropertyType"].fillna("(missing)").str.strip()
    share = (pt.value_counts(normalize=True) * 100).round(2)
    print(pd.DataFrame({"count": pt.value_counts(), "pct": share}))
    is_res = pt.str.contains("residential", case=False)
    print(f"\nResidential: {is_res.mean() * 100:.2f}%  |  Other: {(~is_res).mean() * 100:.2f}%")
    if "PropertySubType" in df:
        print("\nTop PropertySubType values:")
        print(df["PropertySubType"].fillna("(missing)").value_counts().head(10))


def price_summary(df: pd.DataFrame) -> None:
    section("2. Median and average prices")
    rows = {}
    for col in ["ClosePrice", "ListPrice", "OriginalListPrice"]:
        if col in df:
            s = df[col].where(df[col] > 0).dropna()
            rows[col] = {
                "n": len(s), "median": s.median(), "mean": s.mean(),
                "min": s.min(), "p95": s.quantile(0.95), "max": s.max(),
            }
    if rows:
        print(pd.DataFrame(rows).T.round(0).to_string(float_format="{:,.0f}".format))
    else:
        print("No price columns available")


def dom_distribution(df: pd.DataFrame) -> None:
    section("3. Days on Market distribution")
    if "DaysOnMarket" not in df:
        print("DaysOnMarket not available")
        return
    dom = df["DaysOnMarket"].dropna()
    print(f"non-null: {len(dom):,} of {len(df):,}")
    print(f"negative: {(dom < 0).sum():,}  |  zero: {(dom == 0).sum():,}")
    dom = dom[dom >= 0]
    print(dom.describe(percentiles=[.1, .25, .5, .75, .9, .95, .99]).round(1))
    bins = [-1, 7, 14, 30, 60, 90, 180, 365, np.inf]
    labels = ["0-7", "8-14", "15-30", "31-60", "61-90", "91-180", "181-365", "365+"]
    buckets = pd.cut(dom, bins=bins, labels=labels).value_counts(sort=False)
    print("\nBuckets (days):")
    print(pd.DataFrame({"count": buckets, "pct": (buckets / buckets.sum() * 100).round(2)}))


def above_below_list(df: pd.DataFrame) -> None:
    section("4. Sold above vs. below list price")
    for ref in ["ListPrice", "OriginalListPrice"]:
        if "ClosePrice" not in df or ref not in df:
            continue
        d = df[(df["ClosePrice"] > 0) & (df[ref] > 0)]
        if d.empty:
            print(f"vs {ref}: no rows with both prices")
            continue
        diff = d["ClosePrice"] - d[ref]
        cat = np.select([diff > 0, diff < 0], ["above", "below"], default="at")
        pct = pd.Series(cat).value_counts(normalize=True).mul(100).round(2)
        ratio = (d["ClosePrice"] / d[ref])
        print(f"\nvs {ref} (n={len(d):,})")
        print(pct.to_string())
        print(f"median close/list ratio: {ratio.median():.4f}  |  mean: {ratio.mean():.4f}")


def date_consistency(df: pd.DataFrame) -> None:
    section("5. Date consistency checks")
    n = len(df)
    for c in DATE_COLS:
        if c in df:
            print(f"{c}: {df[c].isna().sum():,} null ({df[c].isna().mean() * 100:.1f}%)"
                  f", range {df[c].min()} to {df[c].max()}")

    checks = [
        ("CloseDate", "<", "ListingContractDate", "close before listing"),
        ("CloseDate", "<", "PurchaseContractDate", "close before purchase contract"),
        ("PurchaseContractDate", "<", "ListingContractDate", "purchase contract before listing"),
    ]
    print()
    for a, op, b, label in checks:
        if a in df and b in df:
            bad = (df[a] < df[b])
            print(f"{label}: {bad.sum():,} rows ({bad.sum() / n * 100:.2f}%)")

    if "CloseDate" in df:
        now = pd.Timestamp.today()
        print(f"close date in the future: {(df['CloseDate'] > now).sum():,}")
        print(f"close date before 2000: {(df['CloseDate'] < '2000-01-01').sum():,}")

    # DaysOnMarket should roughly match the gap between listing and purchase contract
    if {"DaysOnMarket", "ListingContractDate", "PurchaseContractDate"} <= set(df.columns):
        gap = (df["PurchaseContractDate"] - df["ListingContractDate"]).dt.days
        mismatch = (df["DaysOnMarket"] - gap).abs() > 7
        valid = gap.notna() & df["DaysOnMarket"].notna()
        print(f"DaysOnMarket differs from listing->contract gap by >7 days: "
              f"{mismatch[valid].sum():,} of {valid.sum():,} comparable rows")

    if "DaysOnMarket" in df:
        print(f"negative DaysOnMarket: {(df['DaysOnMarket'] < 0).sum():,}")


def top_counties(df: pd.DataFrame) -> None:
    section(f"6. Counties with the highest median price (min {MIN_COUNTY_SALES} rows)")
    if "CountyOrParish" not in df:
        print("CountyOrParish not available")
        return
    price_col = "ClosePrice" if "ClosePrice" in df and df["ClosePrice"].gt(0).sum() > 0 else "ListPrice"
    print(f"price column used: {price_col}")
    d = df[df[price_col] > 0]
    g = (d.groupby("CountyOrParish")[price_col]
           .agg(n="count", median="median", mean="mean")
           .query("n >= @MIN_COUNTY_SALES")
           .sort_values("median", ascending=False)
           .head(TOP_N_COUNTIES))
    print(g.round(0).to_string(float_format="{:,.0f}".format))


def eda_run(name: str, path: str) -> None:
    print("=" * 70)
    print(f"{name.upper()}  ({path})")
    print("=" * 70)
    df = load(path)
    print(f"rows: {len(df):,}")
    property_type_share(df)
    price_summary(df)
    dom_distribution(df)
    above_below_list(df)
    date_consistency(df)
    top_counties(df)

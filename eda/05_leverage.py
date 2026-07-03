"""
Leverage analysis: the risk profile of trades.
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = scan.head(LARGE_SAMPLE_ROWS).collect()
    opens = sample.filter(pl.col("action") == "Open")

    print("╔══════════════════════════════════════════════╗")
    print("║         LEVERAGE DISTRIBUTION               ║")
    print("╚══════════════════════════════════════════════╝")

    lev = opens["leverage"]
    print(f"  Count:    {len(lev):>10,}")
    print(f"  Min:      {lev.min():>10.1f}x")
    print(f"  Max:      {lev.max():>10.1f}x")
    print(f"  Mean:     {lev.mean():>10.1f}x")
    print(f"  Median:   {lev.median():>10.1f}x")
    print(f"  Std:      {lev.std():>10.1f}x")

    qs = lev.quantile([0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    print(f"  P01:      {qs[0]:>10.1f}x")
    print(f"  P05:      {qs[1]:>10.1f}x")
    print(f"  P10:      {qs[2]:>10.1f}x")
    print(f"  P25:      {qs[3]:>10.1f}x")
    print(f"  P50:      {qs[4]:>10.1f}x")
    print(f"  P75:      {qs[5]:>10.1f}x")
    print(f"  P90:      {qs[6]:>10.1f}x")
    print(f"  P95:      {qs[7]:>10.1f}x")
    print(f"  P99:      {qs[8]:>10.1f}x")

    # ── Leverage buckets ───────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         LEVERAGE BUCKETS                     ║")
    print("╚══════════════════════════════════════════════╝")
    buckets = opens.with_columns(
        pl.when(pl.col("leverage") == 0).alias("bucket"),
        pl.when((pl.col("leverage") > 0) & (pl.col("leverage") <= 2)).alias("bucket"),
        pl.when((pl.col("leverage") > 2) & (pl.col("leverage") <= 5)).alias("bucket"),
        pl.when((pl.col("leverage") > 5) & (pl.col("leverage") <= 10)).alias("bucket"),
        pl.when((pl.col("leverage") > 10) & (pl.col("leverage") <= 20)).alias("bucket"),
        pl.when((pl.col("leverage") > 20) & (pl.col("leverage") <= 50)).alias("bucket"),
        pl.when((pl.col("leverage") > 50) & (pl.col("leverage") <= 100)).alias(
            "bucket"
        ),
        pl.when(pl.col("leverage") > 100).alias("bucket"),
    )
    # Simpler approach
    opens_buckets = opens.with_columns(
        pl.col("leverage")
        .cut(
            [0, 2, 5, 10, 20, 50, 100],
            labels=["0x", "1-2x", "2-5x", "5-10x", "10-20x", "20-50x", "50-100x"],
        )
        .alias("lev_bucket")
    )
    # Add >100x manually
    opens_buckets = opens_buckets.with_columns(
        pl.when(pl.col("leverage") > 100)
        .alias("lev_bucket")
        .otherwise(pl.col("lev_bucket"))
    )

    bucket_counts = opens.with_columns(
        pl.when(pl.col("leverage") == 0).alias("lev_bucket"),
        pl.when((pl.col("leverage") > 0) & (pl.col("leverage") <= 2)).alias(
            "lev_bucket"
        ),
        pl.when((pl.col("leverage") > 2) & (pl.col("leverage") <= 5)).alias(
            "lev_bucket"
        ),
        pl.when((pl.col("leverage") > 5) & (pl.col("leverage") <= 10)).alias(
            "lev_bucket"
        ),
        pl.when((pl.col("leverage") > 10) & (pl.col("leverage") <= 20)).alias(
            "lev_bucket"
        ),
        pl.when((pl.col("leverage") > 20) & (pl.col("leverage") <= 50)).alias(
            "lev_bucket"
        ),
        pl.when((pl.col("leverage") > 50) & (pl.col("leverage") <= 100)).alias(
            "lev_bucket"
        ),
        pl.when(pl.col("leverage") > 100).alias("lev_bucket"),
    )
    # Simpler: use integer division
    opens_buckets = opens.with_columns(
        pl.when(pl.col("leverage") <= 0).alias("bucket"),
        pl.when((pl.col("leverage") > 0) & (pl.col("leverage") <= 2)).alias("bucket"),
        pl.when((pl.col("leverage") > 2) & (pl.col("leverage") <= 5)).alias("bucket"),
        pl.when((pl.col("leverage") > 5) & (pl.col("leverage") <= 10)).alias("bucket"),
        pl.when((pl.col("leverage") > 10) & (pl.col("leverage") <= 20)).alias("bucket"),
        pl.when((pl.col("leverage") > 20) & (pl.col("leverage") <= 50)).alias("bucket"),
        pl.when((pl.col("leverage") > 50) & (pl.col("leverage") <= 100)).alias(
            "bucket"
        ),
        pl.when(pl.col("leverage") > 100).alias("bucket"),
    )
    # Let's do it properly
    opens = opens.with_columns(
        pl.col("leverage")
        .cut(
            [0, 2, 5, 10, 20, 50, 100],
            labels=["0x", "1-2x", "2-5x", "5-10x", "10-20x", "20-50x", "50-100x"],
            left_closed=False,
        )
        .alias("lev_bucket")
    )
    opens = opens.with_columns(
        pl.when(pl.col("leverage") > 100)
        .alias("lev_bucket")
        .otherwise(pl.col("lev_bucket"))
    )

    for row in (
        opens.group_by("lev_bucket")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .iter_rows()
    ):
        print(f"  {row[0]:<10s}  {row[1]:>10,}")

    # ── Leverage × side ────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         LEVERAGE × SIDE                      ║")
    print("╚══════════════════════════════════════════════╝")
    for side in ["Long", "Short"]:
        s = opens.filter(pl.col("side") == side)["leverage"]
        print(
            f"  {side:<7s}  mean={s.mean():.1f}x  median={s.median():.1f}x  max={s.max():.0f}x  n={len(s):,}"
        )

    # ── Leverage × volume ──────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         LEVERAGE × POSITION SIZE            ║")
    print("╚══════════════════════════════════════════════╝")
    opens = opens.with_columns(
        pl.col("sizeUsd")
        .cut(
            [100, 1000, 10000, 100000],
            labels=["<100", "100-1K", "1K-10K", "10K-100K", ">100K"],
            left_closed=False,
        )
        .alias("size_bucket")
    )
    # Fix: handle >100K
    opens = opens.with_columns(
        pl.when(pl.col("sizeUsd") > 100000)
        .alias("size_bucket")
        .otherwise(pl.col("size_bucket"))
    )
    # That's getting messy. Let me just do it the simple way.
    # Actually drop the cut approach and use simple conditions
    opens = sample.filter(pl.col("action") == "Open")
    print(
        f"{'Size Range':<15s} {'Count':>8s} {'AvgLev':>7s} {'MedLev':>7s} {'AvgColl':>10s}"
    )
    sizes = [
        (0, 100, "<$100"),
        (100, 1000, "$100-1K"),
        (1000, 10000, "$1K-10K"),
        (10000, 100000, "$10K-100K"),
        (100000, float("inf"), ">$100K"),
    ]
    for lo, hi, label in sizes:
        subset = opens.filter((pl.col("sizeUsd") > lo) & (pl.col("sizeUsd") <= hi))
        if len(subset) > 0:
            print(
                f"  {label:<15s} {len(subset):>8,} {subset['leverage'].mean():>6.1f}x {subset['leverage'].median():>6.1f}x ${subset['collateralUsd'].mean():>8,.0f}"
            )


if __name__ == "__main__":
    main()

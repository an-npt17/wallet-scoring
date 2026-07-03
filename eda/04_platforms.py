"""
Platform analysis: how does trading behavior differ across protocols?
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = scan.head(LARGE_SAMPLE_ROWS).collect()
    opens = sample.filter(pl.col("action") == "Open")

    print("╔══════════════════════════════════════════════╗")
    print("║         PLATFORM COMPARISON                  ║")
    print("╚══════════════════════════════════════════════╝")

    platform_stats = (
        opens.group_by("platform")
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("sizeUsd").sum().alias("total_volume"),
                pl.col("sizeUsd").mean().alias("avg_size"),
                pl.col("sizeUsd").median().alias("median_size"),
                pl.col("collateralUsd").mean().alias("avg_collateral"),
                pl.col("leverage").mean().alias("avg_leverage"),
                pl.col("leverage").median().alias("median_leverage"),
                (pl.col("side") == "Long").mean().alias("long_pct"),
                pl.col("ownerAccount").n_unique().alias("unique_traders"),
                pl.col("asset").n_unique().alias("unique_assets"),
            ]
        )
        .sort("total_volume", descending=True)
    )

    print(
        f"{'Platform':<15s} {'Trades':>8s} {'Volume':>14s} {'AvgSize':>10s} {'AvgColl':>10s} {'AvgLev':>7s} {'Long%':>7s} {'Users':>7s} {'Assets':>6s}"
    )
    print("-" * 84)
    for row in platform_stats.iter_rows():
        print(
            f"{row[0]:<15s} {row[1]:>8,} {row[2]:>12,.0f} {row[3]:>8,.0f} {row[5]:>8,.0f} {row[6]:>5.1f}x {row[8]:>6.1f}% {row[9]:>7,} {row[10]:>6,}"
        )

    # ── Platform × asset overlap ───────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         PLATFORM × ASSET HEATMAP            ║")
    print("╚══════════════════════════════════════════════╝")
    cross = (
        opens.group_by(["platform", "asset"])
        .agg(pl.col("sizeUsd").sum().alias("volume"))
        .sort(["platform", "volume"], descending=[False, True])
    )
    for plat in opens["platform"].unique():
        top = cross.filter(pl.col("platform") == plat).head(5)
        assets = ", ".join(f"{r['asset']}({r['volume']:,.0f})" for r in top.iter_rows())
        print(f"  {plat:<15s} → {assets}")

    # ── Leverage distribution per platform ─────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         LEVERAGE DECILES PER PLATFORM       ║")
    print("╚══════════════════════════════════════════════╝")
    for plat in opens["platform"].unique():
        plat_lev = opens.filter(pl.col("platform") == plat)["leverage"]
        qs = plat_lev.quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
        print(
            f"  {plat:<15s}  P10:{qs[0]:6.1f}  P25:{qs[1]:6.1f}  P50:{qs[2]:6.1f}  P75:{qs[3]:6.1f}  P90:{qs[4]:6.1f}  P99:{qs[5]:6.1f}"
        )

    # ── Chains used per platform ───────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         PLATFORM × CHAIN                     ║")
    print("╚══════════════════════════════════════════════╝")
    chain_cross = (
        sample.group_by(["platform", "chain"])
        .agg(pl.len().alias("count"))
        .sort(["platform", "count"], descending=[False, True])
    )
    for row in chain_cross.iter_rows():
        print(f"  {row[0]:<15s}  {row[1]:<15s}  {row[2]:>10,}")


if __name__ == "__main__":
    main()

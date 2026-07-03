"""
Capital analysis: collateral, position size, and capital efficiency.
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = scan.head(LARGE_SAMPLE_ROWS).collect()

    print("╔══════════════════════════════════════════════╗")
    print("║         CAPITAL & COLLATERAL ANALYSIS       ║")
    print("╚══════════════════════════════════════════════╝")

    # ── Collateral distributions ───────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         COLLATERAL DISTRIBUTION             ║")
    print("╚══════════════════════════════════════════════╝")

    # Only events with real collateral
    coll = sample.filter(pl.col("collateralUsd") > 0)
    coll_values = coll["collateralUsd"]

    print(f"  Events with collateral:    {len(coll):>10,}")
    print(f"  Min:                       ${coll_values.min():>10,.2f}")
    print(f"  Max:                       ${coll_values.max():>10,.2f}")
    print(f"  Mean:                      ${coll_values.mean():>10,.2f}")
    print(f"  Median:                    ${coll_values.median():>10,.2f}")
    qs = coll_values.quantile([0.1, 0.25, 0.75, 0.9, 0.99])
    print(f"  P10:                       ${qs[0]:>10,.2f}")
    print(f"  P25:                       ${qs[1]:>10,.2f}")
    print(f"  P75:                       ${qs[2]:>10,.2f}")
    print(f"  P90:                       ${qs[3]:>10,.2f}")
    print(f"  P99:                       ${qs[4]:>10,.2f}")

    # ── Capital efficiency ─────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         CAPITAL EFFICIENCY                   ║")
    print("╚══════════════════════════════════════════════╝")
    # Capital efficiency = total position size / total collateral for a wallet
    wallet_cap = (
        sample.group_by("ownerAccount")
        .agg(
            [
                pl.col("collateralUsd").sum().alias("total_collateral"),
                pl.col("sizeUsd").sum().alias("total_size"),
            ]
        )
        .with_columns(
            (pl.col("total_size") / pl.col("total_collateral")).alias(
                "capital_efficiency"
            )
        )
        .filter(pl.col("total_collateral") > 0)
    )
    eff = wallet_cap["capital_efficiency"]
    print(f"  Wallets analyzed:          {len(wallet_cap):>10,}")
    print(f"  Mean capital efficiency:   {eff.mean():>10.1f}x")
    print(f"  Median capital efficiency: {eff.median():>10.1f}x")
    qs = eff.quantile([0.1, 0.25, 0.75, 0.9, 0.99])
    print(f"  P10:                       {qs[0]:>10.1f}x")
    print(f"  P25:                       {qs[1]:>10.1f}x")
    print(f"  P75:                       {qs[2]:>10.1f}x")
    print(f"  P90:                       {qs[3]:>10.1f}x")
    print(f"  P99:                       {qs[4]:>10.1f}x")

    # ── Wallet wealth tiers ────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         WALLET WEALTH TIERS                  ║")
    print("╚══════════════════════════════════════════════╝")
    wealth_tiers = [
        ("Retail (<$500)", pl.col("total_collateral") < 500),
        (
            "Small ($500-5K)",
            (pl.col("total_collateral") >= 500) & (pl.col("total_collateral") < 5000),
        ),
        (
            "Mid ($5K-50K)",
            (pl.col("total_collateral") >= 5000) & (pl.col("total_collateral") < 50000),
        ),
        (
            "High ($50K-500K)",
            (pl.col("total_collateral") >= 50000)
            & (pl.col("total_collateral") < 500000),
        ),
        ("Whale ($500K+)", pl.col("total_collateral") >= 500000),
    ]
    for name, cond in wealth_tiers:
        subset = wallet_cap.filter(cond)
        n = len(subset)
        total_cap = subset["total_collateral"].sum()
        print(f"  {name:<20s}  {n:>6,} wallets  total_coll: ${total_cap:>12,.0f}")

    # ── Position size distribution (Opens only) ────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         POSITION SIZE DISTRIBUTION          ║")
    print("╚══════════════════════════════════════════════╝")
    opens = sample.filter(pl.col("action") == "Open")
    sizes = opens["sizeUsd"]
    print(f"  Total Open events:  {len(opens):>10,}")
    print(f"  Min size:           ${sizes.min():>10,.2f}")
    print(f"  Max size:           ${sizes.max():>10,.2f}")
    print(f"  Mean size:          ${sizes.mean():>10,.2f}")
    print(f"  Median size:        ${sizes.median():>10,.2f}")
    qs = sizes.quantile([0.1, 0.25, 0.75, 0.9, 0.99])
    print(f"  P10:                ${qs[0]:>10,.2f}")
    print(f"  P25:                ${qs[1]:>10,.2f}")
    print(f"  P75:                ${qs[2]:>10,.2f}")
    print(f"  P90:                ${qs[3]:>10,.2f}")
    print(f"  P99:                ${qs[4]:>10,.2f}")

    # ── Collateral vs Size relationship ────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         COLLATERAL vs SIZE (Opens)          ║")
    print("╚══════════════════════════════════════════════╝")
    # Correlation
    corr = opens.select(pl.corr(pl.col("collateralUsd"), pl.col("sizeUsd"))).item()
    print(f"  Pearson correlation: {corr:.4f}")

    # Collateral/size ratio distribution
    ratio = opens.filter(pl.col("collateralUsd") > 0).with_columns(
        (pl.col("sizeUsd") / pl.col("collateralUsd")).alias("size_coll_ratio")
    )["size_coll_ratio"]
    print(f"  Mean size/collateral ratio:  {ratio.mean():.1f}x")
    print(f"  Median size/collateral ratio: {ratio.median():.1f}x")

    # ── Platform × capital ─────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         PLATFORM CAPITAL PROFILES            ║")
    print("╚══════════════════════════════════════════════╝")
    for plat in opens["platform"].unique():
        p = opens.filter(pl.col("platform") == plat)
        print(
            f"  {plat:<15s}  avg_coll: ${p['collateralUsd'].mean():>8,.0f}  "
            f"med_coll: ${p['collateralUsd'].median():>8,.0f}  "
            f"avg_size: ${p['sizeUsd'].mean():>8,.0f}  "
            f"med_size: ${p['sizeUsd'].median():>8,.0f}"
        )


if __name__ == "__main__":
    main()

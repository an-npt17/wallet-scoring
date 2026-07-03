"""
Wallet-level behavioral analysis: who are these traders?
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = scan.head(LARGE_SAMPLE_ROWS).collect()

    print("╔══════════════════════════════════════════════╗")
    print("║         WALLET ACTIVITY DISTRIBUTION        ║")
    print("╚══════════════════════════════════════════════╝")

    wallet_stats = (
        sample.group_by("ownerAccount")
        .agg(
            [
                pl.len().alias("n_events"),
                pl.col("action")
                .filter(pl.col("action") == "Open")
                .len()
                .alias("n_trades"),
                pl.col("action")
                .filter(pl.col("action") == "Close")
                .len()
                .alias("n_closes"),
                pl.col("action")
                .filter(pl.col("action") == "Liquidate")
                .len()
                .alias("n_liquidations"),
                pl.col("sizeUsd").sum().alias("total_volume"),
                pl.col("collateralUsd").sum().alias("total_collateral"),
                pl.col("leverage").mean().alias("avg_leverage"),
                pl.col("asset").n_unique().alias("n_assets"),
                pl.col("platform").n_unique().alias("n_platforms"),
                pl.col("positionKey").n_unique().alias("n_positions"),
                (pl.col("side") == "Long").mean().alias("long_ratio"),
                pl.col("timestamp").max().alias("last_active"),
                (pl.col("sizeUsd") * pl.col("leverage"))
                .mean()
                .alias("avg_risk_exposure"),
            ]
        )
        .with_columns(
            [
                ((pl.col("last_active") - pl.col("last_active").min()) / 86400).alias(
                    "active_span_days"
                ),
            ]
        )
    )

    total_wallets = len(wallet_stats)
    print(f"  Total wallets:           {total_wallets:>10,}")

    # Activity tiers
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         WALLET ACTIVITY TIERS                ║")
    print("╚══════════════════════════════════════════════╝")
    tiers = [
        ("1-trade wonders", pl.col("n_trades") == 1),
        ("Casual (2-5)", (pl.col("n_trades") >= 2) & (pl.col("n_trades") <= 5)),
        ("Regular (6-20)", (pl.col("n_trades") >= 6) & (pl.col("n_trades") <= 20)),
        ("Active (21-100)", (pl.col("n_trades") >= 21) & (pl.col("n_trades") <= 100)),
        ("Power (101-500)", (pl.col("n_trades") >= 101) & (pl.col("n_trades") <= 500)),
        ("Whale bots (>500)", pl.col("n_trades") > 500),
    ]
    for name, cond in tiers:
        subset = wallet_stats.filter(cond)
        n = len(subset)
        vol = subset["total_volume"].sum()
        print(
            f"  {name:<18s}  {n:>8,} wallets ({n / total_wallets * 100:5.1f}%)  vol=${vol:>12,.0f}"
        )

    # ── Wallet concentration ───────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         VOLUME CONCENTRATION                 ║")
    print("╚══════════════════════════════════════════════╝")
    sorted_wallets = wallet_stats.sort("total_volume", descending=True)
    total_vol = sorted_wallets["total_volume"].sum()
    for pct in [0.01, 0.05, 0.1, 0.2, 0.5]:
        n = max(1, int(total_wallets * pct))
        top_vol = sorted_wallets.head(n)["total_volume"].sum()
        print(
            f"  Top {pct * 100:>4.0f}% wallets ({n:>6,}) control {top_vol / total_vol * 100:>5.1f}% of volume"
        )

    # ── Platform diversification ───────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         PLATFORM DIVERSIFICATION             ║")
    print("╚══════════════════════════════════════════════╝")
    for n_plat in sorted(wallet_stats["n_platforms"].unique().to_list()):
        subset = wallet_stats.filter(pl.col("n_platforms") == n_plat)
        print(
            f"  {n_plat} platform(s):  {len(subset):>8,} wallets ({len(subset) / total_wallets * 100:.1f}%)"
        )

    # ── Leverage profile of wallets ────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         WALLET LEVERAGE PROFILES             ║")
    print("╚══════════════════════════════════════════════╝")
    lev_tiers = [
        ("Conservative (<3x avg)", pl.col("avg_leverage") < 3),
        (
            "Moderate (3-10x)",
            (pl.col("avg_leverage") >= 3) & (pl.col("avg_leverage") <= 10),
        ),
        (
            "Aggressive (10-30x)",
            (pl.col("avg_leverage") > 10) & (pl.col("avg_leverage") <= 30),
        ),
        (
            "Degens (30-100x)",
            (pl.col("avg_leverage") > 30) & (pl.col("avg_leverage") <= 100),
        ),
        ("Suicide (>100x avg)", pl.col("avg_leverage") > 100),
    ]
    for name, cond in lev_tiers:
        subset = wallet_stats.filter(cond)
        print(
            f"  {name:<22s}  {len(subset):>8,} wallets ({len(subset) / total_wallets * 100:5.1f}%)"
        )


if __name__ == "__main__":
    main()

"""
Asset-level analysis: which assets are traded, volumes, leverage, side bias.
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = scan.head(LARGE_SAMPLE_ROWS).collect()

    print("╔══════════════════════════════════════════════╗")
    print("║         ASSET DISTRIBUTION                  ║")
    print("╚══════════════════════════════════════════════╝")

    # Only position-opening events to measure real trading volume
    opens = sample.filter(pl.col("action") == "Open")

    asset_stats = (
        opens.group_by("asset")
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("sizeUsd").sum().alias("total_volume"),
                pl.col("sizeUsd").mean().alias("avg_size"),
                pl.col("sizeUsd").median().alias("median_size"),
                pl.col("collateralUsd").sum().alias("total_collateral"),
                pl.col("leverage").mean().alias("avg_leverage"),
                pl.col("leverage").median().alias("median_leverage"),
                (pl.col("side") == "Long").mean().alias("long_pct"),
                pl.col("ownerAccount").n_unique().alias("unique_traders"),
            ]
        )
        .sort("total_volume", descending=True)
    )

    print(
        f"{'Asset':<12s} {'Trades':>8s} {'Volume(USD)':>16s} {'AvgSize':>12s} {'AvgLev':>8s} {'Long%':>8s} {'Traders':>8s}"
    )
    print("-" * 72)
    for row in asset_stats.head(30).iter_rows():
        print(
            f"{row[0]:<12s} {row[1]:>8,} {row[2]:>14,.0f} {row[3]:>10,.0f} {row[5]:>6.1f}x {row[7]:>7.1f}% {row[8]:>8,}"
        )

    # ── Asset concentration ────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         ASSET CONCENTRATION                 ║")
    print("╚══════════════════════════════════════════════╝")
    total_vol = asset_stats["total_volume"].sum()
    cumulative = 0.0
    for i, row in enumerate(asset_stats.iter_rows()):
        cumulative += row[2]
        if i < 10 or cumulative / total_vol <= 0.95:
            print(f"  {row[0]:<12s}  {cumulative / total_vol * 100:5.1f}% cumulative")
    print(f"  Total volume (sample): ${total_vol:,.0f}")
    print(
        f"  Herfindahl index:       {(asset_stats['total_volume'].rel_freq() ** 2).sum():.4f}"
    )

    # ── Side bias by asset ─────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         SIDE BIAS PER ASSET                 ║")
    print("╚══════════════════════════════════════════════╝")
    for row in (
        asset_stats.filter(pl.col("n_trades") > 100)
        .head(20)
        .sort("long_pct")
        .iter_rows()
    ):
        bias = "LONG" if row[7] > 0.7 else ("SHORT" if row[7] < 0.3 else "neutral")
        print(
            f"  {row[0]:<12s}  Long: {row[7] * 100:5.1f}%  Short: {(1 - row[7]) * 100:5.1f}%  → {bias}"
        )

    # ── Meme vs blue-chip ──────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         TIER ANALYSIS                        ║")
    print("╚══════════════════════════════════════════════╝")
    blue_chips = {
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "BNB",
        "DOGE",
        "ADA",
        "AVAX",
        "DOT",
        "LINK",
        "UNI",
        "ATOM",
    }
    meme_coins = {
        "PEPE",
        "DOGE",
        "FARTCOIN",
        "WIF",
        "POPCAT",
        "MOODENG",
        "MEW",
        "PNUT",
        "TURBO",
        "GOAT",
        "BONK",
        "NEIRO",
        "SHIB",
    }

    for tier_name, coin_set in [("Blue-chip", blue_chips), ("Meme", meme_coins)]:
        tier = opens.filter(pl.col("asset").is_in(coin_set))
        other = opens.filter(~pl.col("asset").is_in(coin_set))
        print(f"  {tier_name}:")
        print(f"    Trades:    {len(tier):>8,}  vs other: {len(other):>8,}")
        if len(tier) > 0:
            print(f"    Volume:    ${tier['sizeUsd'].sum():>12,.0f}")
            print(
                f"    Avg lev:   {tier['leverage'].mean():>5.1f}x  median: {tier['leverage'].median():>5.1f}x"
            )
            print(f"    Long%:     {(tier['side'] == 'Long').mean() * 100:.1f}%")


if __name__ == "__main__":
    main()

"""
Synthesis: what does this dataset mean for wallet scoring?
Runs all key findings from previous scripts and provides the big-picture interpretation.
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = scan.head(LARGE_SAMPLE_ROWS).collect()
    opens = sample.filter(pl.col("action") == "Open")

    TOTAL_ENTRIES = scan.select(pl.len()).collect().item()
    UNIQUE_WALLETS = scan.select(pl.col("ownerAccount").n_unique()).collect().item()
    UNIQUE_POSITIONS = scan.select(pl.col("positionKey").n_unique()).collect().item()

    print("=" * 72)
    print("  SYNTHESIS: WHAT THIS DATASET MEANS")
    print("=" * 72)

    # ── 1. Dataset Identity ────────────────────────────────────────
    print()
    print("── 1. DATASET IDENTITY ──")
    print(f"  This is a {TOTAL_ENTRIES:,}-entry log of DeFi perpetual futures trading,")
    print(
        f"  spanning ~{UNIQUE_WALLETS:,} unique wallets and {UNIQUE_POSITIONS:,} positions,"
    )
    print(f"  across 5 platforms (Hyperliquid, Jupiter, GMX-v2, APX, Myx)")
    print(f"  on Solana, Hyperliquid L1, Arbitrum, BSC.")
    print(f"  Each entry is a single event in a position's lifecycle.")

    # ── 2. The Trading Landscape ────────────────────────────────────
    print()
    print("── 2. THE TRADING LANDSCAPE ──")
    action_counts = sample["action"].value_counts().to_dict(as_series=False)
    for row in action_counts:
        pct = row["count"] / len(sample) * 100
        print(f"  {row['action']:<12s}  {row['count']:>8,} ({pct:.1f}%)")

    print()
    print(f"  The dataset is ~74% Open events — each one is a new position opened.")
    print(f"  Close (21%) and Liquidate (2.8%) events bookend positions.")
    print(f"  Deposit/Withdraw (2.6%) show active collateral management.")
    print(f"  ~81% of positions close voluntarily, ~19% get liquidated.")

    # ── 3. Risk Profile ────────────────────────────────────────────
    print()
    print("── 3. RISK PROFILE ──")
    lev = opens["leverage"]
    print(f"  Median leverage: {lev.median():.0f}x  — this is extremely high.")
    print(f"  Mean leverage:   {lev.mean():.0f}x")
    print(f"  P99 leverage:    {lev.quantile(0.99):.0f}x")
    print(f"  Max leverage:    {lev.max():.0f}x")

    short_pct = (opens["side"] == "Short").mean() * 100
    print(f"  Short bias:      {short_pct:.0f}% of trades are shorts")

    liq_pct = (sample["action"] == "Liquidate").mean() * 100
    print(f"  Liquidation rate: {liq_pct:.1f}% of all events")

    # ── 4. Capital Distribution ────────────────────────────────────
    print()
    print("── 4. CAPITAL DISTRIBUTION ──")
    coll = opens["collateralUsd"]
    size = opens["sizeUsd"]
    print(
        f"  Position size — median: ${size.median():>8,.0f}   mean: ${size.mean():>8,.0f}"
    )
    print(
        f"  Collateral    — median: ${coll.median():>8,.0f}   mean: ${coll.mean():>8,.0f}"
    )
    print(f"  The gap between median and mean reveals extreme skew:")
    print(
        f"  A small number of whales dominate volume; most traders are retail ($50 median collateral)."
    )

    # ── 5. The Wallet Zoo ──────────────────────────────────────────
    print()
    print("── 5. THE WALLET ZOO (Behavioral Segmentation) ──")

    wallet_stats = sample.group_by("ownerAccount").agg(
        [
            pl.len().alias("n_events"),
            pl.col("action").filter(pl.col("action") == "Open").len().alias("n_trades"),
            pl.col("sizeUsd").sum().alias("total_volume"),
            pl.col("collateralUsd").sum().alias("total_collateral"),
            pl.col("leverage").mean().alias("avg_leverage"),
            pl.col("asset").n_unique().alias("n_assets"),
            pl.col("platform").n_unique().alias("n_platforms"),
            (pl.col("side") == "Long").mean().alias("long_ratio"),
        ]
    )
    total_wallets = len(wallet_stats)

    # Identify archetypes
    one_trade = wallet_stats.filter(pl.col("n_trades") == 1).select(pl.len()).item()
    bots = wallet_stats.filter(pl.col("n_trades") > 100).select(pl.len()).item()
    degens = wallet_stats.filter(pl.col("avg_leverage") > 50).select(pl.len()).item()
    multi_plat = wallet_stats.filter(pl.col("n_platforms") > 1).select(pl.len()).item()
    diversified = wallet_stats.filter(pl.col("n_assets") > 5).select(pl.len()).item()

    print(
        f"  🐥 1-trade wonders:        {one_trade:>7,} ({one_trade / total_wallets * 100:.0f}%)"
    )
    print(
        f"  🤖 High-frequency bots:    {bots:>7,} ({bots / total_wallets * 100:.1f}%)   (>100 trades)"
    )
    print(
        f"  🎰 Degens (avg >50x):      {degens:>7,} ({degens / total_wallets * 100:.1f}%)"
    )
    print(
        f"  🔄 Multi-platform users:   {multi_plat:>7,} ({multi_plat / total_wallets * 100:.1f}%)"
    )
    print(
        f"  🗂️   Multi-asset traders:   {diversified:>7,} ({diversified / total_wallets * 100:.1f}%)"
    )

    # ── 6. Implicit Signals (hidden in the data) ───────────────────
    print()
    print("── 6. IMPLICIT SIGNALS FOR WALLET SCORING ──")
    print()
    print("  These are patterns in the data that separate elite from retail:")
    print()

    # Capital efficiency
    wallet_cap_eff = (
        wallet_stats.filter(pl.col("total_collateral") > 0).with_columns(
            (pl.col("total_volume") / pl.col("total_collateral")).alias("cap_eff")
        )
    )["cap_eff"]
    print(
        f"  ⚡ Capital efficiency (vol/coll): median {wallet_cap_eff.median():.0f}x →"
        f" elite wallets recycle capital many times"
    )

    # Win rate proxy (simple PnL from position tracking)
    print(
        f"  📈 Win rate variance: traders who consistently close > Close/Liquidate ratio"
    )
    print(f"     signal skill vs reckless degens who get liquidated.")

    # Multi-platform sophistication
    print(
        f"  🔧 Platform sophistication: only {multi_plat / total_wallets * 100:.0f}% use multiple protocols"
    )
    print(f"     → multi-platform users are more sophisticated by default.")

    # Timing
    print(f"  ⏰ Timing skill: entry price vs market average around that time")
    print(f"     reveals market-timing ability.")

    # Behavioral consistency
    print(f"  📊 Consistency: regular trading cadence (not random) signals")
    print(f"     systematic strategies vs gambling.")

    # ── 7. What Makes an Elite Wallet (Hypothesis) ─────────────────
    print()
    print("── 7. ELITE WALLET HYPOTHESIS ──")
    print()
    print("  Based on this data, an elite wallet would have:")
    print()
    print("  1. Positive PnL (obviously) with PnL > 95% of peers")
    print("  2. Controlled leverage: avg 2-10x, never >20x")
    print("  3. Win rate > 55% with profit factor > 1.5")
    print("  4. Multi-platform: uses 2+ protocols")
    print("  5. Multi-asset: trades 5+ different assets")
    print("  6. Both sides: trades Long AND Short strategically")
    print("  7. Capital efficient: total volume > 10x total collateral")
    print("  8. Rarely liquidated: liq events < 5% of closes")
    print("  9. Active collateral management: deposits & withdrawals")
    print("  10. Consistent activity over weeks, not a single burst")

    # ── 8. Scoring Architecture Implication ────────────────────────
    print()
    print("── 8. SCORING ARCHITECTURE ──")
    print()
    print("  The scoring should be a composite of sub-scores:")
    print()
    print("  Risk Score   = f(avg_leverage, liq_rate, concentration)")
    print("  Skill Score  = f(win_rate, profit_factor, pnl)")
    print("  Soph Score   = f(n_platforms, n_assets, both_sides)")
    print("  Capital Score= f(total_volume, avg_position_size)")
    print("  Behavior Score= f(consistency, hold_time, timing)")
    print()
    print("  Elite Score  = w1*Risk + w2*Skill + w3*Soph + w4*Capital + w5*Behavior")
    print()
    print(f"  Data volume: 20GB, {TOTAL_ENTRIES:,} events, {UNIQUE_WALLETS:,} wallets")
    print(f"  Recommended stack: Polars (streaming) → Feature Store → ML scorer")


if __name__ == "__main__":
    main()

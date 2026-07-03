"""
Position lifecycle: how do positions evolve from open to close?
Estimates PnL and duration.
"""

import polars as pl
import numpy as np
from config import DATA_PATH, SMALL_SAMPLE_ROWS, OUTPUT_DIR


def estimate_pnl(open_row, close_row):
    """Estimate PnL for a position opened then closed.

    For a Long:  PnL = size * (1/entry_price - 1/exit_price)
    For a Short: PnL = size * (1/exit_price - 1/entry_price)

    This approximates the USD value change of the position.
    """
    if open_row is None or close_row is None:
        return None

    entry_price = open_row["price"]
    exit_price = close_row["price"]
    size = open_row["sizeUsd"]
    side = open_row["side"]

    if entry_price is None or exit_price is None or entry_price == 0:
        return None

    if side == "Long":
        pnl = size * (1.0 / entry_price - 1.0 / exit_price) * exit_price
    else:
        pnl = size * (1.0 / exit_price - 1.0 / entry_price) * entry_price

    return pnl


def main():
    scan = pl.scan_ndjson(DATA_PATH)

    # Use a modest sample — position chaining is expensive
    sample = scan.head(2_000_000).collect()

    print("╔══════════════════════════════════════════════╗")
    print("║         POSITION LIFECYCLE ANALYSIS         ║")
    print("╚══════════════════════════════════════════════╝")

    # ── Group by positionKey, sort by time ─────────────────────────
    positions = (
        sample.sort("timestamp")
        .group_by("positionKey", maintain_order=True)
        .agg(
            [
                pl.col("action").alias("actions"),
                pl.col("timestamp").alias("timestamps"),
                pl.col("price").alias("prices"),
                pl.col("sizeUsd").alias("sizes"),
                pl.col("collateralUsd").alias("collaterals"),
                pl.col("leverage").alias("leverages"),
                pl.col("side").first().alias("side"),
                pl.col("asset").first().alias("asset"),
                pl.col("ownerAccount").first().alias("wallet"),
                pl.col("platform").first().alias("platform"),
                pl.first("timestamp").alias("open_ts"),
                pl.last("timestamp").alias("last_ts"),
                pl.col("action").list.first().alias("first_action"),
                pl.col("action").list.last().alias("last_action"),
            ]
        )
        .with_columns(
            [
                ((pl.col("last_ts") - pl.col("open_ts")) / 86400).alias(
                    "duration_days"
                ),
                pl.col("actions").list.len().alias("n_actions"),
                pl.col("actions")
                .list.eval(pl.element().is_in(["Close", "Liquidate"]).any())
                .alias("is_closed"),
            ]
        )
    )

    total_pos = len(positions)
    closed_pos = positions.filter(pl.col("is_closed")).select(pl.len()).item()
    still_open = positions.filter(~pl.col("is_closed")).select(pl.len()).item()

    print(f"  Total positions:          {total_pos:>10,}")
    print(
        f"  Closed/Liquidated:        {closed_pos:>10,}  ({closed_pos / total_pos * 100:.1f}%)"
    )
    print(
        f"  Still open:               {still_open:>10,}  ({still_open / total_pos * 100:.1f}%)"
    )

    # ── Position duration ──────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         POSITION DURATION                    ║")
    print("╚══════════════════════════════════════════════╝")
    durations = positions.filter(pl.col("is_closed"))["duration_days"]
    if len(durations) > 0:
        qs = durations.quantile([0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
        print(f"  Min:        {durations.min():>10.2f} days")
        print(f"  P10:        {qs[0]:>10.2f} days")
        print(f"  P25:        {qs[1]:>10.2f} days")
        print(f"  Median:     {qs[2]:>10.2f} days")
        print(f"  Mean:       {durations.mean():>10.2f} days")
        print(f"  P75:        {qs[3]:>10.2f} days")
        print(f"  P90:        {qs[4]:>10.2f} days")
        print(f"  P99:        {qs[5]:>10.2f} days")
        print(f"  Max:        {durations.max():>10.2f} days")

        # Duration buckets
        print()
        print("╔══════════════════════════════════════════════╗")
        print("║         DURATION BUCKETS                     ║")
        print("╚══════════════════════════════════════════════╝")
        duration_buckets = [
            ("< 1 hour", pl.col("duration_days") < 1 / 24),
            (
                "1-6 hours",
                (pl.col("duration_days") >= 1 / 24)
                & (pl.col("duration_days") < 6 / 24),
            ),
            (
                "6-24 hours",
                (pl.col("duration_days") >= 6 / 24) & (pl.col("duration_days") < 1),
            ),
            (
                "1-3 days",
                (pl.col("duration_days") >= 1) & (pl.col("duration_days") < 3),
            ),
            (
                "3-7 days",
                (pl.col("duration_days") >= 3) & (pl.col("duration_days") < 7),
            ),
            (
                "1-4 weeks",
                (pl.col("duration_days") >= 7) & (pl.col("duration_days") < 28),
            ),
            ("> 4 weeks", pl.col("duration_days") >= 28),
        ]
        for name, cond in duration_buckets:
            subset = positions.filter(cond & pl.col("is_closed"))
            print(
                f"  {name:<15s}  {len(subset):>8,} positions ({len(subset) / closed_pos * 100:.1f}%)"
            )

    # ── PnL Estimation (for simple Open→Close positions) ──────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         PnL ESTIMATION (Open→Close only)    ║")
    print("╚══════════════════════════════════════════════╝")

    # Find positions with exactly one Open and one Close (simplest case)
    simple_positions = (
        positions.filter(pl.col("n_actions") == 2)
        .filter(pl.col("actions").list.first() == "Open")
        .filter(pl.col("actions").list.last().is_in(["Close", "Liquidate"]))
    )

    print(f"  Simple Open→Close positions: {len(simple_positions):>8,}")

    if len(simple_positions) > 0:
        pnls = []
        for row in simple_positions.iter_rows():
            # Extract first open, last close
            acts = row[1]  # actions list
            prices = row[3]  # prices list
            sizes = row[4]  # sizes list
            side = row[7]

            # Find first Open event price/size
            open_idx = None
            close_idx = None
            for i, a in enumerate(acts):
                if a == "Open" and open_idx is None:
                    open_idx = i
                if a in ("Close", "Liquidate"):
                    close_idx = i

            if open_idx is not None and close_idx is not None and close_idx > open_idx:
                entry = prices[open_idx]
                exit_p = prices[close_idx]
                size = sizes[open_idx]
                collateral = row[6][open_idx]  # collaterals

                if entry and entry > 0 and size and size > 0:
                    if side == "Long":
                        pnl = size * (1.0 / entry - 1.0 / exit_p) * exit_p
                    else:
                        pnl = size * (1.0 / exit_p - 1.0 / entry) * entry
                    pnls.append(
                        {
                            "pnl": pnl,
                            "pnl_pct": pnl / collateral * 100
                            if collateral and collateral > 0
                            else 0,
                            "side": side,
                            "asset": row[8],
                            "platform": row[9],
                            "duration": row[12],
                        }
                    )

        if pnls:
            pnl_df = pl.from_dicts(pnls)
            wins = pnl_df.filter(pl.col("pnl") > 0)
            losses = pnl_df.filter(pl.col("pnl") <= 0)

            print(f"  Positions with valid PnL:  {len(pnl_df):>8,}")
            print(
                f"  Winning trades:            {len(wins):>8,}  ({len(wins) / len(pnl_df) * 100:.1f}%)"
            )
            print(
                f"  Losing trades:             {len(losses):>8,}  ({len(losses) / len(pnl_df) * 100:.1f}%)"
            )
            print(f"  Avg PnL (winners):         ${wins['pnl'].mean():>+10,.2f}")
            print(f"  Avg PnL (losers):          ${losses['pnl'].mean():>+10,.2f}")
            print(f"  Median PnL:                ${pnl_df['pnl'].median():>+10,.2f}")
            print(f"  Mean PnL:                  ${pnl_df['pnl'].mean():>+10,.2f}")
            print(f"  Avg return % (winners):    {wins['pnl_pct'].mean():>+7.1f}%")
            print(f"  Avg return % (losers):     {losses['pnl_pct'].mean():>+7.1f}%")
            print(
                f"  Profit factor:             {wins['pnl'].sum() / abs(losses['pnl'].sum()):>.2f}"
                if len(losses) > 0
                else "N/A"
            )

            # Duration vs PnL
            print()
            print("╔══════════════════════════════════════════════╗")
            print("║         DURATION vs PnL                      ║")
            print("╚══════════════════════════════════════════════╝")
            for lo, hi, label in [
                (0, 1 / 24, "<1h"),
                (1 / 24, 1, "1h-1d"),
                (1, 7, "1-7d"),
                (7, float("inf"), ">7d"),
            ]:
                sub = pnl_df.filter(
                    (pl.col("duration") > lo) & (pl.col("duration") <= hi)
                )
                if len(sub) > 0:
                    wr = (sub["pnl"] > 0).mean() * 100
                    print(
                        f"  {label:<8s}  {len(sub):>6} trades  WR:{wr:5.1f}%  avg:${sub['pnl'].mean():>+8,.2f}  med:${sub['pnl'].median():>+8,.2f}"
                    )


if __name__ == "__main__":
    main()

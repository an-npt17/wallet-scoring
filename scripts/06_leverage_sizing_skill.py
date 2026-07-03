"""
Leverage and sizing skill analysis — operationalizing Van Loon (2018).

What this answers:
  - Does position size (sizeUsd) predict trade outcome? (sizing skill test)
  - Does higher leverage correlate with worse outcomes? (leverage penalty)
  - What is leverage-adjusted ROI vs raw ROI? (risk normalization)
  - Are Deposit/Withdraw events used to add to winners or losers?

Sizing skill operationalization (Van Loon 2018):
  For each wallet, split trades into above/below median sizeUsd.
  Sizing skill = win_rate(large trades) - win_rate(small trades)
  Positive value → wallet bets bigger when confident (good sizing)
  Negative value → wallet bets bigger on losers (poor sizing / martingale)

Data: uses the local logs.json export (faster than querying MongoDB for
      full event-level data). Reads only Open and Close events.

Run:
    uv run python scripts/06_leverage_sizing_skill.py
"""

import sys
from pathlib import Path

import polars as pl


_DATA_PATHS = [Path("logs.json")] + sorted(Path("data").glob("logs_*.json"))
_SAMPLE_N = 5_000_000


def _print_box(title: str) -> None:
    border = "╔" + "═" * 58 + "╗"
    inner = f"║  {title:<56}║"
    close = "╚" + "═" * 58 + "╝"
    print(border)
    print(inner)
    print(close)


def _load_sample() -> pl.DataFrame:
    data_path = next((p for p in _DATA_PATHS if p.exists()), None)
    if data_path is None:
        print("ERROR: no logs.json or data/logs_*.json found", file=sys.stderr)
        sys.exit(1)
    print(f"  Loading sample from {data_path} ...")
    scan = pl.scan_ndjson(str(data_path))
    return scan.head(_SAMPLE_N).collect()


def main() -> None:
    _print_box("LEVERAGE & SIZING SKILL ANALYSIS")

    df = _load_sample()
    print(f"  Sample rows loaded:  {len(df):>12,}")
    print()

    # ── Keep only Open events with valid price/size ────────────────
    opens = df.filter(
        (pl.col("action") == "Open")
        & pl.col("sizeUsd").is_not_null()
        & pl.col("collateralUsd").is_not_null()
        & pl.col("leverage").is_not_null()
        & (pl.col("sizeUsd") > 0)
        & (pl.col("collateralUsd") > 0)
    )
    print(f"  Open events:         {len(opens):>12,}")

    # ── Find matched Open→Close pairs ─────────────────────────────
    closes = (
        df.filter(pl.col("action") == "Close")
        .select(
            [
                "positionKey",
                "price",
                "timestamp",
            ]
        )
        .rename({"price": "close_price", "timestamp": "close_ts"})
    )

    opens_sub = opens.select(
        [
            "ownerAccount",
            "positionKey",
            "side",
            "asset",
            "platform",
            "price",
            "sizeUsd",
            "collateralUsd",
            "leverage",
            "timestamp",
        ]
    ).rename({"price": "open_price", "timestamp": "open_ts"})

    # Join on positionKey — take only the last close per position
    closes_dedup = closes.sort("close_ts", descending=True).unique(
        subset=["positionKey"], keep="first"
    )
    matched = opens_sub.join(closes_dedup, on="positionKey", how="inner")

    # ── Compute PnL ────────────────────────────────────────────────
    matched = matched.with_columns(
        [
            pl.when(pl.col("side") == "Long")
            .then(
                pl.col("sizeUsd")
                * (pl.col("close_price") - pl.col("open_price"))
                / pl.col("open_price")
            )
            .otherwise(
                pl.col("sizeUsd")
                * (pl.col("open_price") - pl.col("close_price"))
                / pl.col("open_price")
            )
            .alias("pnl"),
        ]
    )
    matched = matched.with_columns(
        [
            (pl.col("pnl") / pl.col("collateralUsd")).alias("roi"),
            (pl.col("pnl") > 0).alias("win"),
        ]
    )
    print(f"  Matched Open→Close:  {len(matched):>12,}")
    print()

    # ── Leverage vs outcome ────────────────────────────────────────
    _print_box("LEVERAGE vs OUTCOME")
    lev_buckets = [
        ("<2x", pl.col("leverage") < 2),
        ("2-5x", (pl.col("leverage") >= 2) & (pl.col("leverage") < 5)),
        ("5-10x", (pl.col("leverage") >= 5) & (pl.col("leverage") < 10)),
        ("10-20x", (pl.col("leverage") >= 10) & (pl.col("leverage") < 20)),
        ("20-50x", (pl.col("leverage") >= 20) & (pl.col("leverage") < 50)),
        (">50x", pl.col("leverage") >= 50),
    ]
    print(f"  {'Leverage':<10} {'N':>8} {'Win%':>8} {'Avg ROI':>10} {'Avg PnL':>12}")
    print("  " + "-" * 52)
    for label, mask in lev_buckets:
        sub = matched.filter(mask)
        if len(sub) == 0:
            continue
        wr = sub["win"].mean() or 0.0
        avg_roi = sub["roi"].mean() or 0.0
        avg_pnl = sub["pnl"].mean() or 0.0
        print(
            f"  {label:<10} {len(sub):>8,} {wr:>7.1%} {avg_roi:>+9.2%} ${avg_pnl:>+11,.2f}"
        )
    print()

    # ── Sizing skill per wallet ────────────────────────────────────
    _print_box("SIZING SKILL (Van Loon 2018) PER WALLET")
    print("  Sizing skill = win_rate(large trades) - win_rate(small trades)")
    print("  Positive = wallet bets bigger on winners (good sizing)")
    print("  Negative = wallet bets bigger on losers (poor sizing / martingale)")
    print()

    # Per-wallet median sizeUsd
    wallet_medians = matched.group_by("ownerAccount").agg(
        pl.col("sizeUsd").median().alias("median_size")
    )
    matched_with_median = matched.join(wallet_medians, on="ownerAccount", how="left")
    matched_with_median = matched_with_median.with_columns(
        (pl.col("sizeUsd") >= pl.col("median_size")).alias("is_large")
    )

    sizing_skill = (
        matched_with_median.group_by("ownerAccount")
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("win").filter(pl.col("is_large")).mean().alias("large_wr"),
                pl.col("win").filter(~pl.col("is_large")).mean().alias("small_wr"),
            ]
        )
        .filter(pl.col("n_trades") >= 10)
        .with_columns((pl.col("large_wr") - pl.col("small_wr")).alias("sizing_skill"))
        .drop_nulls(["sizing_skill"])
    )

    print(f"  Wallets with ≥10 trades:  {len(sizing_skill):>8,}")
    if len(sizing_skill) > 0:
        ss = sizing_skill["sizing_skill"]
        positive_sizers = (ss > 0).sum()
        print(
            f"  Positive sizing skill:    {positive_sizers:>8,}  ({positive_sizers / len(ss) * 100:.1f}%)"
        )
        print(
            f"  Negative sizing skill:    {int((ss < 0).sum()):>8,}  ({int((ss < 0).sum()) / len(ss) * 100:.1f}%)"
        )
        print(f"  Mean sizing skill:        {ss.mean():>+8.3f}")
        print(f"  Median sizing skill:      {ss.median():>+8.3f}")
        print()
        print("  Distribution:")
        for lo, hi, label in [
            (-1.0, -0.2, "Strong negative (<-0.2)"),
            (-0.2, -0.05, "Weak negative (-0.2 to -0.05)"),
            (-0.05, 0.05, "Neutral (-0.05 to +0.05)"),
            (0.05, 0.2, "Weak positive (+0.05 to +0.2)"),
            (0.2, 1.0, "Strong positive (>+0.2)"),
        ]:
            n = int(((ss > lo) & (ss <= hi)).sum())
            print(f"    {label:<35}  {n:>7,}  ({n / len(ss) * 100:.1f}%)")
    print()

    # ── Deposit/Withdraw pattern (sizing into position) ────────────
    _print_box("DEPOSIT/WITHDRAW PATTERNS")
    dep_with = df.filter(pl.col("action").is_in(["Deposit", "Withdraw"]))
    dep = df.filter(pl.col("action") == "Deposit")
    wit = df.filter(pl.col("action") == "Withdraw")
    print(f"  Total Deposit events:   {len(dep):>10,}")
    print(f"  Total Withdraw events:  {len(wit):>10,}")
    if len(dep) > 0 and len(wit) > 0:
        print(f"  Deposit/Withdraw ratio: {len(dep) / len(wit):>10.2f}")
    if len(dep_with) > 0:
        avg_deposit = dep["collateralUsd"].mean()
        print(
            f"  Avg deposit size:       ${avg_deposit:>+10,.2f}"
            if avg_deposit
            else "  Avg deposit size:       N/A"
        )
        # How many wallets deposit (add collateral) vs withdraw
        dep_wallets = dep["ownerAccount"].n_unique()
        wit_wallets = wit["ownerAccount"].n_unique()
        print(f"  Wallets that deposit:   {dep_wallets:>10,}")
        print(f"  Wallets that withdraw:  {wit_wallets:>10,}")
    print()
    print("  NOTE: Deposits after a position opens = adding to a position")
    print("        Persistent depositors may be averaging down (poor sizing).")
    print("        This pattern needs cross-matching with subsequent PnL.")


if __name__ == "__main__":
    main()

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

Data: samples from MongoDB logs collection (Open/Close/Deposit/Withdraw events).

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/06_leverage_sizing_skill.py
"""

import argparse
import asyncio
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db, time_match_stage

_SAMPLE_SIZE = 500_000
_PROJECTION = {
    "_id": 0,
    "ownerAccount": 1,
    "positionKey": 1,
    "action": 1,
    "side": 1,
    "asset": 1,
    "platform": 1,
    "price": 1,
    "sizeUsd": 1,
    "collateralUsd": 1,
    "leverage": 1,
    "timestamp": 1,
}


def _print_box(title: str) -> None:
    border = "╔" + "═" * 58 + "╗"
    inner = f"║  {title:<56}║"
    close = "╚" + "═" * 58 + "╝"
    print(border)
    print(inner)
    print(close)


async def _load_sample(args: argparse.Namespace) -> pl.DataFrame:
    db = get_db()
    col = db["logs"]
    time_filter = time_match_stage("timestamp", args.start, args.end)
    total = await col.count_documents(time_filter)
    print(f"  Total log events in DB:  {total:>12,}")
    pipeline = ([{"$match": time_filter}] if time_filter else []) + [
        {"$sample": {"size": _SAMPLE_SIZE}},
        {"$project": _PROJECTION},
    ]
    cursor = await col.aggregate(pipeline)
    docs = await cursor.to_list()
    return pl.from_dicts(docs, infer_schema_length=1000)


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    _print_box("LEVERAGE & SIZING SKILL ANALYSIS")

    pbar = tqdm(total=3, desc="06 leverage_sizing", unit="step", dynamic_ncols=True)

    pbar.set_postfix_str(f"sampling {_SAMPLE_SIZE:,} log events")
    df = await _load_sample(args)
    print(f"  Sample rows loaded:  {len(df):>12,}")
    print()
    pbar.update()

    pbar.set_postfix_str("matching Open→Close pairs")

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
        .select(["positionKey", "price", "timestamp"])
        .rename({"price": "close_price", "timestamp": "close_ts"})
    )

    opens_sub = opens.select([
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
    ]).rename({"price": "open_price", "timestamp": "open_ts"})

    closes_dedup = closes.sort("close_ts", descending=True).unique(
        subset=["positionKey"], keep="first"
    )
    matched = opens_sub.join(closes_dedup, on="positionKey", how="inner")

    # ── Compute PnL ────────────────────────────────────────────────
    matched = matched.with_columns(
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
        .alias("pnl")
    ).with_columns([
        (pl.col("pnl") / pl.col("collateralUsd")).alias("roi"),
        (pl.col("pnl") > 0).alias("win"),
    ])
    print(f"  Matched Open→Close:  {len(matched):>12,}")
    print()
    pbar.update()

    pbar.set_postfix_str("analysing leverage + sizing")

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
    lev_labels: list[str] = []
    lev_wrs: list[float] = []
    for label, mask in lev_buckets:
        sub = matched.filter(mask)
        if len(sub) == 0:
            continue
        wr = sub["win"].mean() or 0.0
        avg_roi = sub["roi"].mean() or 0.0
        avg_pnl = sub["pnl"].mean() or 0.0
        lev_labels.append(label)
        lev_wrs.append(float(wr))
        print(
            f"  {label:<10} {len(sub):>8,} {wr:>7.1%} {avg_roi:>+9.2%} ${avg_pnl:>+11,.2f}"
        )
    print()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(lev_labels, lev_wrs)
    ax.set_title("Win rate by leverage bucket")
    ax.set_ylabel("win rate")
    save_fig(fig, out_dir, "win_rate_by_leverage.png")

    # ── Sizing skill per wallet ────────────────────────────────────
    _print_box("SIZING SKILL (Van Loon 2018) PER WALLET")
    print("  Sizing skill = win_rate(large trades) - win_rate(small trades)")
    print("  Positive = wallet bets bigger on winners (good sizing)")
    print("  Negative = wallet bets bigger on losers (poor sizing / martingale)")
    print()

    wallet_medians = matched.group_by("ownerAccount").agg(
        pl.col("sizeUsd").median().alias("median_size")
    )
    matched_with_median = (
        matched.join(wallet_medians, on="ownerAccount", how="left")
        .with_columns((pl.col("sizeUsd") >= pl.col("median_size")).alias("is_large"))
    )

    sizing_skill = (
        matched_with_median.group_by("ownerAccount")
        .agg([
            pl.len().alias("n_trades"),
            pl.col("win").filter(pl.col("is_large")).mean().alias("large_wr"),
            pl.col("win").filter(~pl.col("is_large")).mean().alias("small_wr"),
        ])
        .filter(pl.col("n_trades") >= 10)
        .with_columns((pl.col("large_wr") - pl.col("small_wr")).alias("sizing_skill"))
        .drop_nulls(["sizing_skill"])
    )

    print(f"  Wallets with ≥10 trades:  {len(sizing_skill):>8,}")
    if len(sizing_skill) > 0:
        ss = sizing_skill["sizing_skill"]
        positive_sizers = int((ss > 0).sum())
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

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(ss, bins=50)
        ax.axvline(0, color="black", linewidth=1)
        ax.set_title("Sizing skill distribution (Van Loon 2018)")
        ax.set_xlabel("sizing skill = win_rate(large) - win_rate(small)")
        ax.set_ylabel("n wallets")
        save_fig(fig, out_dir, "sizing_skill_distribution.png")
    print()

    # ── Deposit/Withdraw pattern (sizing into position) ────────────
    _print_box("DEPOSIT/WITHDRAW PATTERNS")
    dep = df.filter(pl.col("action") == "Deposit")
    wit = df.filter(pl.col("action") == "Withdraw")
    print(f"  Total Deposit events:   {len(dep):>10,}")
    print(f"  Total Withdraw events:  {len(wit):>10,}")
    if len(dep) > 0 and len(wit) > 0:
        print(f"  Deposit/Withdraw ratio: {len(dep) / len(wit):>10.2f}")
    if len(dep) > 0:
        avg_deposit = dep["collateralUsd"].mean()
        print(
            f"  Avg deposit size:       ${avg_deposit:>+10,.2f}"
            if avg_deposit
            else "  Avg deposit size:       N/A"
        )
        dep_wallets = dep["ownerAccount"].n_unique()
        wit_wallets = wit["ownerAccount"].n_unique()
        print(f"  Wallets that deposit:   {dep_wallets:>10,}")
        print(f"  Wallets that withdraw:  {wit_wallets:>10,}")
    print()
    print("  NOTE: Deposits after a position opens = adding to a position")
    print("        Persistent depositors may be averaging down (poor sizing).")
    print("        This pattern needs cross-matching with subsequent PnL.")
    pbar.update()
    pbar.close()
    await close_client()


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("06_leverage_sizing_skill")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

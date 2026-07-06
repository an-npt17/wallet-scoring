"""
Closed positions PnL breakdown.

What this answers:
  - PnL distributions overall and by side (Long/Short)
  - Win rates per side — first empirical test of buy/sell asymmetry (RQ1)
  - PnL by asset and platform
  - Loss magnitude vs win magnitude (profit factor)

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/02_closed_positions_pnl.py
"""

import argparse
import asyncio
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db, time_match_stage

_SAMPLE_SIZE = 200_000
_PROJECTION = {
    "_id": 0,
    "ownerAccount": 1,
    "asset": 1,
    "side": 1,
    "realizedPnl": 1,
    "platform": 1,
    "chain": 1,
    "lastClosedAt": 1,
}


def _print_box(title: str) -> None:
    border = "╔" + "═" * 52 + "╗"
    inner = f"║  {title:<50}║"
    close = "╚" + "═" * 52 + "╝"
    print(border)
    print(inner)
    print(close)


def _pnl_stats(series: pl.Series, label: str) -> None:
    s = series.drop_nulls()
    wins = s.filter(s > 0)
    losses = s.filter(s <= 0)
    win_rate = len(wins) / len(s) if len(s) > 0 else 0.0
    profit_factor = (
        wins.sum() / abs(losses.sum())
        if len(losses) > 0 and losses.sum() != 0
        else float("inf")
    )
    print(f"  [{label}]")
    print(f"    N trades:         {len(s):>10,}")
    print(f"    Win rate:         {win_rate:>+9.2%}")
    print(f"    Mean PnL:         ${s.mean():>+10,.2f}")
    print(f"    Median PnL:       ${s.median():>+10,.2f}")
    print(
        f"    Avg win:          ${wins.mean():>+10,.2f}"
        if len(wins) > 0
        else "    Avg win:          N/A"
    )
    print(
        f"    Avg loss:         ${losses.mean():>+10,.2f}"
        if len(losses) > 0
        else "    Avg loss:          N/A"
    )
    print(f"    Profit factor:    {profit_factor:>10.3f}")
    print()


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    db = get_db()
    col = db["closed_positions"]
    time_filter = time_match_stage("lastClosedAt", args.start, args.end)

    with tqdm(total=3, desc="02 closed_positions", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("counting documents")
        total = await col.count_documents(time_filter)
        _print_box("CLOSED POSITIONS OVERVIEW")
        print(f"  Total closed positions:  {total:>12,}")
        pbar.update()

        pbar.set_postfix_str(f"sampling {_SAMPLE_SIZE:,} docs")
        pipeline = ([{"$match": time_filter}] if time_filter else []) + [
            {"$sample": {"size": _SAMPLE_SIZE}},
            {"$project": _PROJECTION},
        ]
        cursor = await col.aggregate(pipeline)
        docs = await cursor.to_list()
        df = pl.from_dicts(docs, infer_schema_length=500)
        print(f"  Sample size:             {len(df):>12,}")
        print()
        pbar.update()

        pbar.set_postfix_str("analysing PnL distributions")
        pbar.update()

    # ── Overall PnL ────────────────────────────────────────────────
    _print_box("PnL OVERALL")
    _pnl_stats(df["realizedPnl"], "ALL POSITIONS")

    pnl_all = df["realizedPnl"].drop_nulls()
    p1, p99 = pnl_all.quantile(0.01) or 0.0, pnl_all.quantile(0.99) or 0.0
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(pnl_all.clip(p1, p99), bins=60)
    ax.set_title("Realized PnL distribution (clipped to P1-P99)")
    ax.set_xlabel("realizedPnl ($)")
    ax.set_ylabel("n positions")
    save_fig(fig, out_dir, "pnl_distribution.png")

    # ── By side (Long vs Short) — RQ1 test ────────────────────────
    _print_box("PnL BY SIDE — KEY METRIC FOR RQ1")
    for side in ["Long", "Short"]:
        subset = df.filter(pl.col("side") == side)["realizedPnl"]
        _pnl_stats(subset, side.upper())

    # ── Side win-rate comparison (core research metric) ────────────
    _print_box("SIDE WIN-RATE COMPARISON (BUY vs SELL SKILL PROXY)")
    long_df = df.filter(pl.col("side") == "Long")
    short_df = df.filter(pl.col("side") == "Short")
    long_wr = (long_df["realizedPnl"] > 0).mean() or 0.0
    short_wr = (short_df["realizedPnl"] > 0).mean() or 0.0
    print(f"  Long win rate:    {long_wr:>8.2%}   (n={len(long_df):,})")
    print(f"  Short win rate:   {short_wr:>8.2%}   (n={len(short_df):,})")
    print(f"  Difference:       {long_wr - short_wr:>+8.2%}")

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["Long", "Short"], [float(long_wr), float(short_wr)])
    ax.set_title("Win rate by side")
    ax.set_ylabel("win rate")
    ax.set_ylim(0, 1)
    save_fig(fig, out_dir, "win_rate_by_side.png")
    print()
    print("  NOTE: Long win rate = buy-side success;")
    print("        Short win rate ≈ sell-side timing skill.")
    print("        If divergent → supports side-aware decomposition hypothesis.")
    print()

    # ── By asset ───────────────────────────────────────────────────
    _print_box("PnL BY ASSET (top 10)")
    by_asset = (
        df.group_by("asset")
        .agg(
            [
                pl.len().alias("n"),
                pl.col("realizedPnl").mean().alias("mean_pnl"),
                (pl.col("realizedPnl") > 0).mean().alias("win_rate"),
                pl.col("realizedPnl").sum().alias("total_pnl"),
            ]
        )
        .sort("n", descending=True)
        .head(10)
    )
    print(f"  {'Asset':<12} {'N':>8} {'Win%':>8} {'Avg PnL':>12} {'Total PnL':>14}")
    print("  " + "-" * 56)
    for row in by_asset.iter_rows():
        asset, n, mean_pnl, win_rate, total_pnl = row
        print(
            f"  {asset:<12} {n:>8,} {win_rate:>7.1%} ${mean_pnl:>+11,.2f} ${total_pnl:>+13,.0f}"
        )
    print()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(by_asset["asset"].cast(pl.String), by_asset["win_rate"])
    ax.set_title("Win rate by asset (top 10 by volume)")
    ax.set_ylabel("win rate")
    ax.tick_params(axis="x", rotation=45)
    save_fig(fig, out_dir, "win_rate_by_asset.png")

    # ── By platform ────────────────────────────────────────────────
    _print_box("PnL BY PLATFORM")
    by_plat = (
        df.group_by("platform")
        .agg(
            [
                pl.len().alias("n"),
                pl.col("realizedPnl").mean().alias("mean_pnl"),
                (pl.col("realizedPnl") > 0).mean().alias("win_rate"),
            ]
        )
        .sort("n", descending=True)
    )
    print(f"  {'Platform':<20} {'N':>8} {'Win%':>8} {'Avg PnL':>12}")
    print("  " + "-" * 50)
    for row in by_plat.iter_rows():
        plat, n, mean_pnl, win_rate = row
        print(f"  {str(plat):<20} {n:>8,} {win_rate:>7.1%} ${mean_pnl:>+11,.2f}")
    print()

    # ── PnL magnitude distribution ─────────────────────────────────
    _print_box("PnL MAGNITUDE BUCKETS")
    pnl = df["realizedPnl"].drop_nulls()
    magnitude_buckets = [
        ("<-$1000", pnl < -1000),
        ("-$1000 to -$100", (pnl >= -1000) & (pnl < -100)),
        ("-$100 to $0", (pnl >= -100) & (pnl < 0)),
        ("$0 to $100", (pnl >= 0) & (pnl < 100)),
        ("$100 to $1000", (pnl >= 100) & (pnl < 1000)),
        (">$1000", pnl >= 1000),
    ]
    total_n = len(pnl)
    for label, mask in magnitude_buckets:
        n = int(mask.sum())
        print(f"  {label:<22s}  {n:>8,}  ({n / total_n * 100:.1f}%)")

    await close_client()

if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("02_closed_positions_pnl")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

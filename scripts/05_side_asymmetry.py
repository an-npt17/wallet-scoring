"""
Long/Short side asymmetry — empirical test of RQ1.

What this answers:
  - Is Long win rate different from Short win rate at the wallet level?
  - Do wallets that are good at Longs also tend to be good at Shorts?
  - What fraction of wallets are side-specialized vs side-agnostic?
  - Does the correlation between Long and Short skill support decomposition?

Hypothesis from Lim et al. (2022): buying skill and selling skill are
orthogonal. In crypto perps, Long positions require entry timing skill
while Short positions require both timing and the ability to hold against
trend — the skills are different and should be scored separately.

Uses `closed_positions` grouped by wallet + side.

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/05_side_asymmetry.py
"""

import argparse
import asyncio
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db, time_match_stage

_MIN_TRADES_PER_SIDE = 5


def _print_box(title: str) -> None:
    border = "╔" + "═" * 58 + "╗"
    inner = f"║  {title:<56}║"
    close = "╚" + "═" * 58 + "╝"
    print(border)
    print(inner)
    print(close)


def _pearson_corr(a: pl.Series, b: pl.Series) -> float:
    df = pl.DataFrame({"a": a, "b": b}).drop_nulls()
    if len(df) < 3:
        return float("nan")
    return pl.corr(df["a"], df["b"], eager=True).item() or 0.0


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    db = get_db()
    col = db["closed_positions"]
    time_filter = time_match_stage("lastClosedAt", args.start, args.end)

    with tqdm(
        total=3, desc="05 side_asymmetry", unit="step", dynamic_ncols=True
    ) as pbar:
        pbar.set_postfix_str("counting documents")
        total = await col.count_documents(time_filter)
        _print_box("SIDE ASYMMETRY — LONG vs SHORT SKILL (RQ1 TEST)")
        print(f"  Total closed positions:  {total:>12,}")
        pbar.update()

        pbar.set_postfix_str("sampling 300,000 docs")
        pipeline = ([{"$match": time_filter}] if time_filter else []) + [
            {"$sample": {"size": 300_000}},
            {
                "$project": {
                    "_id": 0,
                    "ownerAccount": 1,
                    "side": 1,
                    "realizedPnl": 1,
                    "asset": 1,
                }
            },
        ]
        cursor = await col.aggregate(pipeline)
        docs = await cursor.to_list()
        df = pl.from_dicts(docs, infer_schema_length=500)
        print(f"  Sample size:             {len(df):>12,}")
        print()
        pbar.update()

        pbar.set_postfix_str("analysing side asymmetry")
        pbar.update()

    # ── Global side comparison ─────────────────────────────────────
    _print_box("GLOBAL WIN RATE BY SIDE")
    for side in ["Long", "Short"]:
        sub = df.filter(pl.col("side") == side)
        n = len(sub)
        wr = (sub["realizedPnl"] > 0).mean() or 0.0
        avg_pnl = sub["realizedPnl"].mean() or 0.0
        med_pnl = sub["realizedPnl"].median() or 0.0
        print(
            f"  {side:<6}  n={n:>8,}  win%={wr:>6.2%}  avg=${avg_pnl:>+8,.2f}  med=${med_pnl:>+8,.2f}"
        )
    print()

    # ── Wallet-level Long vs Short skill ───────────────────────────
    _print_box(f"WALLET-LEVEL LONG vs SHORT (min {_MIN_TRADES_PER_SIDE} each side)")

    wallet_side = df.group_by(["ownerAccount", "side"]).agg(
        [
            pl.len().alias("n"),
            (pl.col("realizedPnl") > 0).mean().alias("win_rate"),
            pl.col("realizedPnl").mean().alias("avg_pnl"),
        ]
    )

    long_stats = (
        wallet_side.filter(
            (pl.col("side") == "Long") & (pl.col("n") >= _MIN_TRADES_PER_SIDE)
        )
        .select(["ownerAccount", "win_rate", "avg_pnl", "n"])
        .rename({"win_rate": "long_wr", "avg_pnl": "long_avg_pnl", "n": "long_n"})
    )
    short_stats = (
        wallet_side.filter(
            (pl.col("side") == "Short") & (pl.col("n") >= _MIN_TRADES_PER_SIDE)
        )
        .select(["ownerAccount", "win_rate", "avg_pnl", "n"])
        .rename({"win_rate": "short_wr", "avg_pnl": "short_avg_pnl", "n": "short_n"})
    )

    both = long_stats.join(short_stats, on="ownerAccount", how="inner")
    print(f"  Wallets with ≥{_MIN_TRADES_PER_SIDE} each side: {len(both):>8,}")
    print()

    if len(both) > 10:
        # Pearson correlation of Long WR vs Short WR
        r_wr = _pearson_corr(both["long_wr"], both["short_wr"])
        r_pnl = _pearson_corr(both["long_avg_pnl"], both["short_avg_pnl"])
        print(f"  Pearson r (Long WR vs Short WR):      {r_wr:>+8.3f}")
        print(f"  Pearson r (Long avgPnL vs Short PnL): {r_pnl:>+8.3f}")
        print()

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(both["long_wr"], both["short_wr"], s=8, alpha=0.3)
        ax.set_title(f"Long WR vs Short WR per wallet (r={r_wr:+.3f})")
        ax.set_xlabel("Long win rate")
        ax.set_ylabel("Short win rate")
        save_fig(fig, out_dir, "long_vs_short_wr_scatter.png")
        if abs(r_wr) < 0.3:
            print("  ✓ LOW correlation → supports side-aware decomposition (Lim 2022)")
        else:
            print("  ✗ HIGH correlation → sides may not be orthogonal in this data")
        print()

        # ── Specialization quadrants ───────────────────────────────
        _print_box("SKILL QUADRANT ANALYSIS")
        long_med = both["long_wr"].median() or 0.5
        short_med = both["short_wr"].median() or 0.5
        q1 = both.filter(
            (pl.col("long_wr") >= long_med) & (pl.col("short_wr") >= short_med)
        )
        q2 = both.filter(
            (pl.col("long_wr") < long_med) & (pl.col("short_wr") >= short_med)
        )
        q3 = both.filter(
            (pl.col("long_wr") < long_med) & (pl.col("short_wr") < short_med)
        )
        q4 = both.filter(
            (pl.col("long_wr") >= long_med) & (pl.col("short_wr") < short_med)
        )
        n_both = len(both)
        print(
            f"  Quadrant split at median Long WR={long_med:.2%}, Short WR={short_med:.2%}"
        )
        print()
        print(
            f"  Q1 (Good Long + Good Short):  {len(q1):>6,}  ({len(q1) / n_both * 100:.1f}%)"
        )
        print(
            f"  Q2 (Poor Long + Good Short):  {len(q2):>6,}  ({len(q2) / n_both * 100:.1f}%)"
        )
        print(
            f"  Q3 (Poor Long + Poor Short):  {len(q3):>6,}  ({len(q3) / n_both * 100:.1f}%)"
        )
        print(
            f"  Q4 (Good Long + Poor Short):  {len(q4):>6,}  ({len(q4) / n_both * 100:.1f}%)"
        )
        print()
        print("  If Q2 and Q4 are large → asymmetric skill exists.")
        print("  If Q1 and Q3 dominate → skill is side-agnostic.")
        print()

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(
            ["Q1 dual", "Q2 short-only", "Q3 neither", "Q4 long-only"],
            [len(q1), len(q2), len(q3), len(q4)],
        )
        ax.set_title("Side-skill quadrant distribution")
        ax.set_ylabel("n wallets")
        save_fig(fig, out_dir, "skill_quadrants.png")

        # ── Top Long-only specialists ──────────────────────────────
        _print_box("LONG SPECIALISTS (top Long WR, below median Short WR)")
        long_spec = (
            both.filter(
                (pl.col("long_wr") >= both["long_wr"].quantile(0.9))
                & (pl.col("short_wr") < short_med)
            )
            .sort("long_wr", descending=True)
            .head(5)
        )
        print(f"  {'Wallet':<44} {'Long WR':>8} {'Short WR':>10}")
        for row in long_spec.select(
            ["ownerAccount", "long_wr", "short_wr"]
        ).iter_rows():
            wallet, lwr, swr = row
            print(f"  {wallet:<44} {lwr:>8.2%} {swr:>10.2%}")
        print()

        # ── Top Short-only specialists ─────────────────────────────
        _print_box("SHORT SPECIALISTS (top Short WR, below median Long WR)")
        short_spec = (
            both.filter(
                (pl.col("short_wr") >= both["short_wr"].quantile(0.9))
                & (pl.col("long_wr") < long_med)
            )
            .sort("short_wr", descending=True)
            .head(5)
        )
        for row in short_spec.select(
            ["ownerAccount", "long_wr", "short_wr"]
        ).iter_rows():
            wallet, lwr, swr = row
            print(f"  {wallet:<44} {lwr:>8.2%} {swr:>10.2%}")

    await close_client()


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("05_side_asymmetry")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

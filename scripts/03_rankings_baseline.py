"""
Existing composite score analysis from daily_trader_rankings.

What this answers:
  - What is the current scoring formula and its component distributions?
  - Are the four score components correlated or orthogonal?
  - Is the composite score dominated by one factor?
  - How many traders appear consistently (day over day)?

This is the BASELINE the research proposal needs to beat.
Score formula: risk_reward_ratio*0.25 + win_loss_holding_time_ratio*0.25
             + win_loss_roi_ratio*0.25 + winning_percentage*0.25

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/03_rankings_baseline.py
"""

import argparse
import asyncio
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db


def _print_box(title: str) -> None:
    border = "╔" + "═" * 56 + "╗"
    inner = f"║  {title:<54}║"
    close = "╚" + "═" * 56 + "╝"
    print(border)
    print(inner)
    print(close)


def _pearson(a: pl.Series, b: pl.Series) -> float:
    a_clean = a.drop_nulls()
    b_clean = b.drop_nulls()
    combined = pl.DataFrame({"a": a, "b": b}).drop_nulls()
    if len(combined) < 3:
        return float("nan")
    corr = pl.corr(combined["a"], combined["b"], eager=True).item()
    return corr or 0.0


def _date_range_filter(start: str | None, end: str | None) -> dict[str, dict[str, str]]:
    """`date` is stored as an ISO string (YYYY-MM-DD), which sorts lexicographically."""
    cond: dict[str, str] = {}
    if start:
        cond["$gte"] = start
    if end:
        cond["$lt"] = end
    return {"date": cond} if cond else {}


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    db = get_db()
    col = db["daily_trader_rankings"]
    date_filter = _date_range_filter(args.start, args.end)

    with tqdm(total=5, desc="03 rankings", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("counting snapshots")
        total_snapshots = await col.count_documents(date_filter)
        _print_box("DAILY TRADER RANKINGS — BASELINE ANALYSIS")
        print(f"  Total daily snapshots:   {total_snapshots:>10,}")
        pbar.update()

        pbar.set_postfix_str("fetching latest snapshot")
        latest_doc = await col.find_one(date_filter, sort=[("date", -1)])
        pbar.update()

        if latest_doc is None:
            print("  ERROR: no documents found")
            return

        latest_date = latest_doc.get("date", "unknown")
        traders_list: list[dict] = latest_doc.get("traders", [])
        total_analyzed = latest_doc.get("total_traders_analyzed", 0)
        print(f"  Latest snapshot date:    {latest_date}")
        print(f"  Total analyzed:          {total_analyzed:>10,}")
        print(f"  Top traders returned:    {len(traders_list):>10,}")
        print()

        if not traders_list:
            print("  No trader records in latest snapshot.")
            return

        df = pl.from_dicts(traders_list, infer_schema_length=len(traders_list))

        # ── Score distribution ─────────────────────────────────────────
        pbar.set_postfix_str("score distributions")
        _print_box("COMPOSITE SCORE DISTRIBUTION (latest snapshot)")
        score = df["score"].drop_nulls()
        print(
            f"  Formula: risk_reward*0.25 + wl_holding*0.25 + wl_roi*0.25 + win%*0.25"
        )
        print()
        print(f"  Min:    {score.min():.4f}")
        print(f"  P25:    {score.quantile(0.25):.4f}")
        print(f"  Median: {score.quantile(0.5):.4f}")
        print(f"  Mean:   {score.mean():.4f}")
        print(f"  P75:    {score.quantile(0.75):.4f}")
        print(f"  P90:    {score.quantile(0.9):.4f}")
        print(f"  Max:    {score.max():.4f}")
        print()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(score, bins=50)
        ax.set_title("Composite score distribution (latest snapshot)")
        ax.set_xlabel("score")
        ax.set_ylabel("n traders")
        save_fig(fig, out_dir, "score_distribution.png")
        pbar.update()

        # ── Component distributions + correlation matrix ───────────────
        pbar.set_postfix_str("component correlations")
        components = [
            ("risk_reward_ratio", "Risk/Reward"),
            ("win_loss_holding_time_ratio", "WL Holding Time"),
            ("win_loss_roi_ratio", "WL ROI Ratio"),
            ("winning_percentage", "Winning %"),
        ]
        _print_box("SCORE COMPONENT DISTRIBUTIONS")
        print(f"  {'Component':<28} {'Mean':>8} {'Median':>8} {'Min':>8} {'Max':>8}")
        print("  " + "-" * 64)
        for col_name, label in tqdm(
            components, desc="  components", leave=False, dynamic_ncols=True
        ):
            if col_name not in df.columns:
                continue
            s = df[col_name].drop_nulls()
            print(
                f"  {label:<28} {s.mean():>8.4f} {s.quantile(0.5):>8.4f} {s.min():>8.4f} {s.max():>8.4f}"
            )
        print()

        _print_box("COMPONENT CORRELATION MATRIX")
        print("  (Near-zero = orthogonal dimensions; high = redundant scoring)")
        print()
        comp_cols = [c for c, _ in components if c in df.columns]
        comp_labels = {c: l for c, l in components}
        header_labels = [comp_labels[c][:14] for c in comp_cols]
        print(f"  {'':28}", end="")
        for lbl in header_labels:
            print(f"  {lbl:>14}", end="")
        print()
        for ca in tqdm(
            comp_cols, desc="  corr matrix", leave=False, dynamic_ncols=True
        ):
            print(f"  {comp_labels[ca]:<28}", end="")
            for cb in comp_cols:
                r = _pearson(df[ca], df[cb])
                print(f"  {r:>14.3f}", end="")
            print()
        print()

        corr_matrix = np.array(
            [[_pearson(df[ca], df[cb]) for cb in comp_cols] for ca in comp_cols]
        )
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(corr_matrix, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(comp_cols)), header_labels, rotation=45, ha="right")
        ax.set_yticks(range(len(comp_cols)), header_labels)
        for i in range(len(comp_cols)):
            for j in range(len(comp_cols)):
                ax.text(j, i, f"{corr_matrix[i, j]:.2f}", ha="center", va="center")
        ax.set_title("Score component correlation matrix")
        fig.colorbar(im, ax=ax)
        save_fig(fig, out_dir, "component_correlation_matrix.png")
        pbar.update()

        # ── Top 10 + historical coverage ──────────────────────────────
        pbar.set_postfix_str("top traders + history")
        _print_box("TOP 10 TRADERS (latest snapshot)")
        top10 = df.sort("score", descending=True).head(10)
        print(
            f"  {'Rank':<5} {'Score':>8} {'Win%':>8} {'Trades':>8} {'PnL':>14} {'Asset'}"
        )
        print("  " + "-" * 60)
        for row in top10.select(
            [
                "rank",
                "score",
                "winning_percentage",
                "total_closed_trades",
                "total_pnl",
                "most_traded_coin",
            ]
        ).iter_rows():
            rank, score, win_pct, trades, pnl, coin = row
            print(
                f"  {rank:<5} {score:>8.4f} {win_pct:>7.1%} {trades:>8,} ${pnl:>+13,.2f} {coin}"
            )
        print()

        _print_box("HISTORICAL COVERAGE (snapshots per month)")
        cursor = col.find(date_filter, {"date": 1, "_id": 0}).sort("date", 1)
        date_docs = await cursor.to_list()
        if date_docs:
            dates = [d["date"] for d in date_docs if "date" in d]
            print(f"  First snapshot:   {dates[0] if dates else 'N/A'}")
            print(f"  Latest snapshot:  {dates[-1] if dates else 'N/A'}")
            print(f"  Total snapshots:  {len(dates):,}")
        pbar.update()

    await close_client()

if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("03_rankings_baseline")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

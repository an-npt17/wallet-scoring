"""
Bayesian estimation feasibility — trade count analysis.

What this answers:
  - How many wallets have enough trades for reliable skill estimation?
  - At N trades, how much does the Bayesian posterior shrink toward the prior?
  - What is the effective wallet population for the thesis research?

Bayesian context:
  Posterior variance = prior_var * observation_var / (observation_var + prior_var * N)
  At N trades with observation std σ:
    Shrinkage factor = prior_var / (prior_var + σ²/N)
  → More trades = less shrinkage = observation dominates prior

Thresholds from proposal:
  ≥20 trades → posterior begins to escape prior (target minimum)
  ≥50 trades → reliable 95% HPDI
  ≥100 trades → high confidence

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/04_trade_sufficiency.py
"""

import argparse
import asyncio
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db, time_match_stage


def _print_box(title: str) -> None:
    border = "╔" + "═" * 56 + "╗"
    inner = f"║  {title:<54}║"
    close = "╚" + "═" * 56 + "╝"
    print(border)
    print(inner)
    print(close)


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    db = get_db()
    col = db["accounts"]
    time_filter = time_match_stage("lastTradedAt", args.start, args.end)

    with tqdm(total=4, desc="04 trade_sufficiency", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("counting accounts")
        total = await col.count_documents(time_filter)
        _print_box("BAYESIAN FEASIBILITY — TRADE COUNT ANALYSIS")
        print(f"  Total accounts:     {total:>12,}")
        print()
        pbar.update()

        pbar.set_postfix_str(f"fetching all {total:,} accounts (no sample)")
        pipeline = ([{"$match": time_filter}] if time_filter else []) + [
            {"$project": {"_id": 0, "closedPositionCount": 1, "platform": 1, "chain": 1}},
        ]
        cursor = col.aggregate(pipeline)
        docs = await cursor.to_list()
        df = pl.from_dicts(docs, infer_schema_length=1000)
        trade_counts = df["closedPositionCount"].drop_nulls().cast(pl.Int64)
        pbar.update()

        pbar.set_postfix_str("trade count distribution")
        _print_box("TRADE COUNT DISTRIBUTION")
        qs = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
        print(f"  Mean:    {trade_counts.mean():>8.1f}")
        print(f"  Median:  {trade_counts.median():>8.1f}")
        for q in qs:
            val = trade_counts.quantile(q)
            print(f"  P{int(q * 100):<3}:    {val:>8.0f}")
        print(f"  Max:     {trade_counts.max():>8,}")
        print()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(trade_counts.clip(0, trade_counts.quantile(0.99) or 0), bins=60)
        ax.set_title("Closed trade count distribution (clipped to P99)")
        ax.set_xlabel("closedPositionCount")
        ax.set_ylabel("n accounts")
        save_fig(fig, out_dir, "trade_count_distribution.png")

        thresholds = [
            (5, "Minimal  — posterior ~85% prior"),
            (10, "Low      — posterior ~70% prior"),
            (20, "Target   — posterior begins escaping prior"),
            (50, "Good     — reliable 95% HPDI"),
            (100, "Strong   — high-confidence posterior"),
            (200, "Elite    — near-perfect estimation"),
            (500, "Bot risk — likely algorithmic"),
        ]
        n_total = len(trade_counts)
        _print_box("BAYESIAN THRESHOLD ANALYSIS")
        print(f"  {'Threshold':<8} {'N wallets':>10} {'%':>8}  {'Label'}")
        print("  " + "-" * 65)
        threshold_counts: list[int] = []
        for thresh, label in tqdm(thresholds, desc="  thresholds", leave=False, dynamic_ncols=True):
            n = int((trade_counts >= thresh).sum())
            threshold_counts.append(n)
            print(f"  ≥{thresh:<7} {n:>10,} {n / n_total * 100:>7.1f}%  {label}")
        print()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar([f"≥{t}" for t, _ in thresholds], threshold_counts)
        ax.set_title("Bayesian feasibility — wallets by trade-count threshold")
        ax.set_ylabel("n wallets")
        save_fig(fig, out_dir, "threshold_analysis.png")

        _print_box("FEASIBILITY BY PLATFORM (≥20 trades threshold)")
        by_plat = (
            df.filter(pl.col("closedPositionCount").is_not_null())
            .with_columns(pl.col("closedPositionCount").cast(pl.Int64))
            .group_by("platform")
            .agg([
                pl.len().alias("n_total"),
                (pl.col("closedPositionCount") >= 20).sum().alias("n_sufficient"),
                pl.col("closedPositionCount").median().alias("median_trades"),
            ])
            .sort("n_total", descending=True)
        )
        print(f"  {'Platform':<20} {'N total':>10} {'N ≥20':>10} {'% ≥20':>8} {'Median trades':>14}")
        print("  " + "-" * 66)
        for row in by_plat.iter_rows():
            plat, n_total, n_suf, median_t = row
            pct = n_suf / n_total * 100 if n_total > 0 else 0.0
            print(f"  {str(plat):<20} {n_total:>10,} {n_suf:>10,} {pct:>7.1f}% {median_t:>14.0f}")
        print()
        pbar.update()

        pbar.set_postfix_str("shrinkage simulation")
        _print_box("SHRINKAGE SIMULATION (illustrative)")
        print("  Prior SD = 0.10 ROI, Observation SD = 0.20 ROI")
        print()
        prior_var = 0.10**2
        obs_sd = 0.20
        print(f"  {'N trades':>10} {'Shrinkage':>12} {'CI width (95%)':>16}")
        print("  " + "-" * 40)
        for n in tqdm([5, 10, 20, 50, 100, 200, 500], desc="  shrinkage", leave=False, dynamic_ncols=True):
            obs_var = (obs_sd**2) / n
            post_var = (prior_var * obs_var) / (prior_var + obs_var)
            shrinkage = obs_var / (prior_var + obs_var)
            ci_width = 1.96 * 2 * (post_var**0.5)
            print(f"  {n:>10}  {shrinkage:>11.3f}  ±{ci_width:>13.3f}")
        print()
        print("  Shrinkage = fraction of posterior from prior (0=data, 1=prior)")
        pbar.update()

    await close_client()

if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("04_trade_sufficiency")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

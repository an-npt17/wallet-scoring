"""
Closed positions — data quality and pipeline readiness.

What this answers:
  - realizedPnl coverage (nulls, zeros) — critical for pipeline labels
  - Time range and volume of closures
  - Closed positions per wallet: distribution for Bayesian feasibility
  - Cross-check: closed_positions vs accounts.closedPositionCount alignment
  - Platform / chain coverage for the label set
  - Positions with suspiciously large PnL (data quality flags)

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/10_closed_positions_quality.py
"""

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db, time_match_stage

_PROJECTION_CP = {
    "_id": 0,
    "ownerAccount": 1,
    "positionKey": 1,
    "asset": 1,
    "side": 1,
    "realizedPnl": 1,
    "lastClosedAt": 1,
    "platform": 1,
    "chain": 1,
}
_PROJECTION_ACC = {
    "_id": 0,
    "account": 1,
    "closedPositionCount": 1,
    "platform": 1,
}


def _print_box(title: str) -> None:
    border = "╔" + "═" * 62 + "╗"
    inner = f"║  {title:<60}║"
    close = "╚" + "═" * 62 + "╝"
    print(border)
    print(inner)
    print(close)


def _ts_to_date(ts: int | None) -> str:
    if ts is None:
        return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    db = get_db()
    cp_col = db["closed_positions"]
    acc_col = db["accounts"]
    time_filter = time_match_stage("lastClosedAt", args.start, args.end)

    with tqdm(total=5, desc="10 cp_quality", unit="step", dynamic_ncols=True) as pbar:
        # ── Counts ─────────────────────────────────────────────────────
        pbar.set_postfix_str("counting documents")
        total_cp = await cp_col.count_documents(time_filter)
        total_acc = await acc_col.count_documents({})
        _print_box("CLOSED POSITIONS — PIPELINE READINESS")
        print(f"  closed_positions docs:  {total_cp:>12,}")
        print(f"  accounts docs:          {total_acc:>12,}")
        print()
        pbar.update()

        # ── Fetch closed_positions ──────────────────────────────────────
        pbar.set_postfix_str(f"fetching all {total_cp:,} closed positions")
        pipeline = ([{"$match": time_filter}] if time_filter else []) + [
            {"$project": _PROJECTION_CP}
        ]
        cursor = cp_col.aggregate(pipeline)
        cp_docs = await cursor.to_list()
        cp = pl.from_dicts(cp_docs, infer_schema_length=1000)
        pbar.update()

        # ── realizedPnl quality ────────────────────────────────────────
        pbar.set_postfix_str("PnL quality + time range")
        pnl = cp["realizedPnl"]
        n_null = int(pnl.is_null().sum())
        n_zero = int((pnl == 0).sum())
        n_valid = int(pnl.drop_nulls().__len__())

        _print_box("REALIZEDPNL COVERAGE (pipeline label quality)")
        print(f"  Total rows:              {len(cp):>12,}")
        print(f"  realizedPnl not null:    {n_valid:>12,}  ({n_valid / len(cp) * 100:.2f}%)")
        print(f"  realizedPnl null:        {n_null:>12,}  ({n_null / len(cp) * 100:.2f}%)")
        print(f"  realizedPnl == 0:        {n_zero:>12,}  ({n_zero / len(cp) * 100:.2f}%)")
        pnl_clean = pnl.drop_nulls()
        if len(pnl_clean) > 0:
            print(f"  Median realizedPnl:      ${pnl_clean.median():>+12,.2f}")
            print(f"  Mean realizedPnl:        ${pnl_clean.mean():>+12,.2f}")
            n_pos = int((pnl_clean > 0).sum())
            print(f"  Profitable positions:    {n_pos:>12,}  ({n_pos / len(pnl_clean) * 100:.1f}%)")
        print()

        # ── Suspicious PnL values ─────────────────────────────────────
        outlier_thresh = 1_000_000
        n_outlier = int((pnl_clean.abs() > outlier_thresh).sum())
        if n_outlier > 0:
            print(f"  ⚠  PnL > $1M or < -$1M: {n_outlier:>6,} positions (data quality flag)")
        else:
            print(f"  ✓  No extreme PnL outliers (|pnl| > $1M)")
        print()

        # ── Time range ─────────────────────────────────────────────────
        ts_col = cp["lastClosedAt"].drop_nulls()
        _print_box("CLOSURE TIME RANGE")
        print(f"  First closure:  {_ts_to_date(int(ts_col.min()))}")
        print(f"  Latest closure: {_ts_to_date(int(ts_col.max()))}")
        span = (int(ts_col.max()) - int(ts_col.min())) / 86400
        print(f"  Span:           {span:.0f} days")
        print(f"  Unique wallets: {cp['ownerAccount'].n_unique():>8,}")
        print()
        pbar.update()

        # ── Per-wallet distribution ─────────────────────────────────────
        pbar.set_postfix_str("per-wallet distribution + platform")
        wallet_cp = (
            cp.group_by("ownerAccount")
            .agg([
                pl.len().alias("n_closed"),
                pl.col("realizedPnl").sum().alias("total_pnl"),
                (pl.col("realizedPnl") > 0).mean().alias("win_rate"),
            ])
        )
        n_cp = wallet_cp["n_closed"]

        _print_box("CLOSED POSITIONS PER WALLET (label feasibility)")
        thresholds = [1, 5, 10, 20, 50, 100, 200]
        print(f"  {'Threshold':<10} {'N wallets':>12} {'%':>8}  {'Label'}")
        print("  " + "-" * 55)
        for thresh in tqdm(thresholds, desc="  thresholds", leave=False, dynamic_ncols=True):
            n = int((n_cp >= thresh).sum())
            labels = {1: "any data", 5: "min for EDA", 10: "pipeline filter", 20: "Bayesian target", 50: "reliable posterior", 100: "high confidence", 200: "elite"}
            print(f"  ≥{thresh:<9} {n:>12,} {n / len(n_cp) * 100:>7.1f}%  {labels.get(thresh, '')}")
        print()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(n_cp.clip(0, n_cp.quantile(0.99) or 0), bins=60)
        ax.set_title("Closed positions per wallet (clipped to P99)")
        ax.set_xlabel("n_closed")
        ax.set_ylabel("n wallets")
        save_fig(fig, out_dir, "closed_per_wallet_distribution.png")

        # ── Platform / chain coverage ──────────────────────────────────
        _print_box("PLATFORM COVERAGE")
        by_plat = (
            cp.group_by("platform")
            .agg([
                pl.len().alias("n"),
                pl.col("ownerAccount").n_unique().alias("n_wallets"),
                pl.col("realizedPnl").is_null().sum().alias("n_null_pnl"),
            ])
            .sort("n", descending=True)
        )
        print(f"  {'Platform':<24} {'Positions':>10} {'Wallets':>10} {'Null PnL':>10}")
        print("  " + "-" * 58)
        for row in by_plat.iter_rows():
            plat, n, n_w, n_null = row
            print(f"  {str(plat):<24} {n:>10,} {n_w:>10,} {n_null:>10,}")
        print()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(by_plat["platform"].cast(pl.String), by_plat["n"])
        ax.set_title("Closed positions by platform")
        ax.set_ylabel("n positions")
        ax.tick_params(axis="x", rotation=45)
        save_fig(fig, out_dir, "platform_coverage.png")
        pbar.update()

        # ── Cross-check accounts vs closed_positions ───────────────────
        pbar.set_postfix_str("cross-checking accounts vs closed_positions")
        _print_box("CROSS-CHECK: accounts vs closed_positions")

        acc_cursor = acc_col.aggregate([{"$project": _PROJECTION_ACC}])
        acc_docs = await acc_cursor.to_list()
        acc = pl.from_dicts(acc_docs, infer_schema_length=500)

        cp_wallet_counts = wallet_cp.select(["ownerAccount", "n_closed"]).rename({"ownerAccount": "account"})
        merged = acc.join(cp_wallet_counts, on="account", how="left")

        n_acc_no_cp = int(merged["n_closed"].is_null().sum())
        n_acc_with_cp = int(merged["n_closed"].is_not_null().sum())
        merged_valid = merged.filter(pl.col("n_closed").is_not_null() & pl.col("closedPositionCount").is_not_null())
        count_match = merged_valid.with_columns(
            (pl.col("n_closed") == pl.col("closedPositionCount")).alias("match")
        )
        n_match = int(count_match["match"].sum())

        print(f"  Accounts total:                  {len(acc):>10,}")
        print(f"  Accounts WITH closed_positions:  {n_acc_with_cp:>10,}  ({n_acc_with_cp / len(acc) * 100:.1f}%)")
        print(f"  Accounts with NO cp records:     {n_acc_no_cp:>10,}  ({n_acc_no_cp / len(acc) * 100:.1f}%)")
        print(f"  Count exact match (acc vs cp):   {n_match:>10,}  of {len(merged_valid):,} comparable")
        print()

        # ── Summary / next steps ───────────────────────────────────────
        _print_box("PIPELINE READINESS SUMMARY")
        usable_wallets = int((n_cp >= 10).sum())
        pnl_coverage = n_valid / len(cp) * 100
        print(f"  realizedPnl coverage:     {pnl_coverage:.1f}%  {'✓ good' if pnl_coverage > 95 else '⚠ check nulls'}")
        print(f"  Wallets ≥10 closed pos:   {usable_wallets:,}  (pipeline minimum)")
        print(f"  Wallets ≥20 closed pos:   {int((n_cp >= 20).sum()):,}  (Bayesian target)")
        print(f"  Data span:                {span:.0f} days")
        print()
        print("  NEXT STEPS:")
        if n_null > len(cp) * 0.05:
            print("  ⚠  >5% null realizedPnl — investigate source before using as labels")
        if n_acc_no_cp > len(acc) * 0.3:
            print("  ⚠  >30% accounts have no closed_positions — check collection sync")
        print("  1. Run pipeline/01 → 04 to build features + labels parquets")
        print("  2. Run pipeline/05 to check feature-label correlations")
        print("  3. If wallet count <5k at ≥20 trades, lower threshold or expand data range")
        pbar.update()

    await close_client()

if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("10_closed_positions_quality")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

"""
Logs collection deep EDA.

What this answers:
  - Action-type breakdown (Open/Close/Deposit/Withdraw/Liquidate)
  - Data time range and coverage span
  - Unique wallets and positionKeys in the collection
  - Asset / platform / chain distribution
  - Orphan analysis: Opens without matching Close (data gap or still open?)
  - Action balance: Open/Close ratio (healthy data ≈ 1.0)
  - Position lifecycle: distribution of open→close durations
  - Data quality: null fields, zero prices/sizes

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/08_logs_overview.py
"""

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from tqdm import tqdm

from pipeline._report import get_output_dir, save_fig, tee_stdout
from scripts._client import add_time_range_args, close_client, get_db, time_match_stage

_SAMPLE_SIZE = 300_000
_PROJECTION = {
    "_id": 0,
    "ownerAccount": 1,
    "positionKey": 1,
    "action": 1,
    "asset": 1,
    "platform": 1,
    "chain": 1,
    "side": 1,
    "price": 1,
    "sizeUsd": 1,
    "collateralUsd": 1,
    "leverage": 1,
    "timestamp": 1,
}


def _print_box(title: str) -> None:
    border = "╔" + "═" * 60 + "╗"
    inner = f"║  {title:<58}║"
    close = "╚" + "═" * 60 + "╝"
    print(border)
    print(inner)
    print(close)


def _ts_to_date(ts: int | None) -> str:
    if ts is None:
        return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


async def main(args: argparse.Namespace, out_dir: Path) -> None:
    db = get_db()
    col = db["logs"]
    time_filter = time_match_stage("timestamp", args.start, args.end)
    match_stage = [{"$match": time_filter}] if time_filter else []

    with tqdm(
        total=8, desc="08 logs_overview", unit="step", dynamic_ncols=True
    ) as pbar:
        # ── Totals ─────────────────────────────────────────────────────
        pbar.set_postfix_str("counting total + by action")
        total = await col.count_documents(time_filter)
        _print_box("LOGS COLLECTION OVERVIEW")
        print(f"  Total log events:  {total:>14,}")
        print()

        action_counts_cursor = await col.aggregate(
            match_stage
            + [
                {"$group": {"_id": "$action", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}},
            ]
        )
        action_rows = await action_counts_cursor.to_list()
        _print_box("ACTION TYPE BREAKDOWN")
        print(f"  {'Action':<16} {'Count':>12} {'%':>8}")
        print("  " + "-" * 40)
        for row in action_rows:
            action, n = row["_id"], row["n"]
            print(f"  {str(action):<16} {n:>12,} {n / total * 100:>7.1f}%")

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar([str(r["_id"]) for r in action_rows], [r["n"] for r in action_rows])
        ax.set_title("Log event action-type breakdown")
        ax.set_ylabel("n events")
        save_fig(fig, out_dir, "action_type_breakdown.png")

        opens_n = next((r["n"] for r in action_rows if r["_id"] == "Open"), 0)
        closes_n = next((r["n"] for r in action_rows if r["_id"] == "Close"), 0)
        liqs_n = next((r["n"] for r in action_rows if r["_id"] == "Liquidate"), 0)
        ratio = closes_n / opens_n if opens_n > 0 else 0.0
        liq_rate = liqs_n / opens_n * 100 if opens_n > 0 else 0.0
        print()
        print(f"  Open/Close ratio:  {ratio:.3f}  (healthy ≈ 1.0)")
        print(f"  Liquidation rate:  {liq_rate:.2f}%  of opens")
        print()
        pbar.update()

        # ── Events over time ────────────────────────────────────────────
        pbar.set_postfix_str("events over time")
        daily_cursor = await col.aggregate(
            match_stage
            + [
                {
                    "$group": {
                        "_id": {
                            "day": {
                                "$subtract": [
                                    "$timestamp",
                                    {"$mod": ["$timestamp", 86400]},
                                ]
                            },
                            "action": "$action",
                        },
                        "n": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.day": 1}},
            ]
        )
        daily_rows = await daily_cursor.to_list()
        daily_df = pl.from_dicts(
            [
                {"day": r["_id"]["day"], "action": r["_id"]["action"], "n": r["n"]}
                for r in daily_rows
            ]
        )
        pivot_df = (
            daily_df.pivot(
                index="day", columns="action", values="n", aggregate_function="first"
            )
            .fill_null(0)
            .sort("day")
        )

        known_actions = ["Open", "Close", "Deposit", "Withdraw", "Liquidate"]
        for a in known_actions:
            if a not in pivot_df.columns:
                pivot_df = pivot_df.with_columns(pl.lit(0, dtype=pl.Int64).alias(a))

        day_ts = pivot_df["day"].to_numpy()
        day_dates = [datetime.fromtimestamp(int(ts), tz=timezone.utc) for ts in day_ts]
        colors = plt.cm.Set2.colors

        _print_box("EVENTS OVER TIME")
        print(f"  Days with data:          {len(pivot_df):>10,}")
        print(
            f"  Total events in range:   {pivot_df.select(pl.sum_horizontal(known_actions)).sum().item():>10,}"
        )
        print()

        # Daily stacked bar chart
        fig, ax = plt.subplots(figsize=(12, 5))
        bottom = np.zeros(len(pivot_df))
        for i, a in enumerate(known_actions):
            vals = pivot_df[a].to_numpy()
            ax.bar(
                day_dates,
                vals,
                bottom=bottom,
                label=a,
                width=1,
                color=colors[i],
                edgecolor="white",
                linewidth=0.3,
            )
            bottom += vals
        ax.set_title("Daily log events by action type")
        ax.set_ylabel("n events")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate()
        save_fig(fig, out_dir, "events_over_time_daily.png")

        # Weekly line chart
        weekly_df = (
            pivot_df.with_columns(
                ((pl.col("day") // (86400 * 7)) * 86400 * 7).alias("week")
            )
            .group_by("week", maintain_order=True)
            .agg([pl.col(a).sum().alias(a) for a in known_actions])
            .sort("week")
        )
        week_ts = weekly_df["week"].to_numpy()
        week_dates = [datetime.fromtimestamp(int(ts), tz=timezone.utc) for ts in week_ts]
        fig2, ax2 = plt.subplots(figsize=(12, 5))
        for i, a in enumerate(known_actions):
            ax2.plot(
                week_dates,
                weekly_df[a].to_numpy(),
                label=a,
                color=colors[i],
                linewidth=1.5,
            )
        ax2.set_title("Weekly log events by action type")
        ax2.set_ylabel("n events")
        ax2.legend()
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig2.autofmt_xdate()
        save_fig(fig2, out_dir, "events_over_time_weekly.png")

        # Action composition (normalized %)
        fig3, ax3 = plt.subplots(figsize=(12, 5))
        action_matrix = pivot_df.select(known_actions).to_numpy()
        row_totals = action_matrix.sum(axis=1, keepdims=True)
        pct_matrix = np.divide(action_matrix, row_totals, where=row_totals > 0) * 100
        pct_bottom = np.zeros(len(pivot_df))
        for i, a in enumerate(known_actions):
            ax3.fill_between(
                day_dates,
                pct_bottom,
                pct_bottom + pct_matrix[:, i],
                label=a,
                color=colors[i],
                alpha=0.7,
                step="mid",
            )
            pct_bottom += pct_matrix[:, i]
        ax3.set_title("Daily action composition (%)")
        ax3.set_ylabel("% of events")
        ax3.set_ylim(0, 100)
        ax3.legend()
        ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig3.autofmt_xdate()
        save_fig(fig3, out_dir, "action_composition_daily.png")

        # Monthly summary table (30-day buckets)
        monthly_df = daily_df.group_by(
            ((pl.col("day") // (86400 * 30)) * 30 * 86400).alias("month"), "action"
        ).agg(pl.col("n").sum())
        monthly_pivot = (
            monthly_df.pivot(
                index="month", columns="action", values="n", aggregate_function="first"
            )
            .fill_null(0)
            .sort("month")
        )
        for a in known_actions:
            if a not in monthly_pivot.columns:
                monthly_pivot = monthly_pivot.with_columns(
                    pl.lit(0, dtype=pl.Int64).alias(a)
                )

        print(
            f"  {'Month':<12} {'Total':>8} {'Open':>8} {'Close':>8} {'Deposit':>8} {'Withdraw':>8} {'Liquidate':>8}"
        )
        print("  " + "-" * 68)
        for row in monthly_pivot.iter_rows():
            month_ts = row[0]
            month_label = _ts_to_date(month_ts)[:7]
            vals = row[1:]
            total = sum(vals)
            print(
                f"  {month_label:<12} {total:>8,} {vals[0]:>8,} {vals[1]:>8,} {vals[2]:>8,} {vals[3]:>8,} {vals[4]:>8,}"
            )
        print()
        pbar.update()

        # ── Time range ─────────────────────────────────────────────────
        pbar.set_postfix_str("time range")
        ts_cursor = await col.aggregate(
            match_stage
            + [
                {
                    "$group": {
                        "_id": None,
                        "min_ts": {"$min": "$timestamp"},
                        "max_ts": {"$max": "$timestamp"},
                    }
                },
            ]
        )
        ts_rows = await ts_cursor.to_list()
        min_ts = max_ts = span_days = 0
        if ts_rows:
            min_ts, max_ts = ts_rows[0]["min_ts"], ts_rows[0]["max_ts"]
            span_days = (max_ts - min_ts) / 86400 if min_ts and max_ts else 0
            _print_box("TIME RANGE")
            print(f"  First event:       {_ts_to_date(min_ts)}  (ts={min_ts})")
            print(f"  Latest event:      {_ts_to_date(max_ts)}  (ts={max_ts})")
            print(f"  Span:              {span_days:.0f} days")
            print()
        pbar.update()

        # ── Unique counts (separate pipelines to avoid $addToSet memory limit) ──
        pbar.set_postfix_str("unique wallets")
        wallet_cursor = await col.aggregate(
            match_stage
            + [
                {"$group": {"_id": "$ownerAccount"}},
                {"$count": "n"},
            ]
        )
        wallet_rows = await wallet_cursor.to_list()
        n_wallets = wallet_rows[0]["n"] if wallet_rows else 0
        pbar.update()

        pbar.set_postfix_str("unique positionKeys")
        pos_cursor = await col.aggregate(
            match_stage
            + [
                {"$group": {"_id": "$positionKey"}},
                {"$count": "n"},
            ]
        )
        pos_rows = await pos_cursor.to_list()
        n_positions = pos_rows[0]["n"] if pos_rows else 0

        _print_box("UNIQUE COUNTS")
        print(f"  Unique wallets:     {n_wallets:>12,}")
        print(f"  Unique positionKeys: {n_positions:>11,}")
        print(
            f"  Events/wallet avg:  {total / n_wallets:.1f}" if n_wallets else "  N/A"
        )
        print()
        pbar.update()

        # ── Sample for distribution analysis ───────────────────────────
        pbar.set_postfix_str(f"sampling {_SAMPLE_SIZE:,} docs")
        cursor = await col.aggregate(
            match_stage
            + [
                {"$sample": {"size": _SAMPLE_SIZE}},
                {"$project": _PROJECTION},
            ]
        )
        docs = await cursor.to_list()
        df = pl.from_dicts(docs, infer_schema_length=1000)
        print(f"  Sample size for distributions: {len(df):,}")
        print()
        pbar.update()

        # ── Asset / platform / chain breakdown ─────────────────────────
        pbar.set_postfix_str("asset / platform / chain breakdown")
        _print_box("TOP ASSETS (by event count in sample)")
        by_asset = (
            df.group_by("asset")
            .agg(
                [pl.len().alias("n"), (pl.col("action") == "Open").sum().alias("opens")]
            )
            .sort("n", descending=True)
            .head(12)
        )
        print(f"  {'Asset':<14} {'Events':>10} {'Opens':>10} {'%':>8}")
        print("  " + "-" * 46)
        for row in by_asset.iter_rows():
            asset, n, opens = row
            print(
                f"  {str(asset):<14} {n:>10,} {opens:>10,} {n / len(df) * 100:>7.1f}%"
            )
        print()

        _print_box("PLATFORM BREAKDOWN (sample)")
        by_plat = (
            df.group_by("platform").agg(pl.len().alias("n")).sort("n", descending=True)
        )
        for row in by_plat.iter_rows():
            plat, n = row
            print(f"  {str(plat):<24} {n:>10,}  ({n / len(df) * 100:.1f}%)")
        print()

        _print_box("CHAIN BREAKDOWN (sample)")
        by_chain = (
            df.group_by("chain").agg(pl.len().alias("n")).sort("n", descending=True)
        )
        for row in by_chain.iter_rows():
            chain, n = row
            print(f"  {str(chain):<24} {n:>10,}  ({n / len(df) * 100:.1f}%)")
        print()
        pbar.update()

        # ── Orphan / lifecycle analysis ────────────────────────────────
        pbar.set_postfix_str("orphan + data quality analysis")
        opens_sample = df.filter(pl.col("action") == "Open").select("positionKey")
        closes_sample = df.filter(
            pl.col("action").is_in(["Close", "Liquidate"])
        ).select("positionKey")

        open_keys = set(opens_sample["positionKey"].to_list())
        close_keys = set(closes_sample["positionKey"].to_list())
        matched = open_keys & close_keys
        orphan_opens = open_keys - close_keys

        _print_box("ORPHAN ANALYSIS (sample-based estimate)")
        print(f"  Unique open positionKeys in sample:    {len(open_keys):>8,}")
        print(
            f"  Have matching Close/Liquidate:         {len(matched):>8,}  ({len(matched) / len(open_keys) * 100:.1f}%)"
        )
        print(
            f"  Orphan opens (no close in sample):     {len(orphan_opens):>8,}  ({len(orphan_opens) / len(open_keys) * 100:.1f}%)"
        )
        print()
        print("  NOTE: Orphans include still-open positions AND data gaps.")
        print("        Cross-check with opening_positions collection (script 09).")
        print()

        # ── Position lifecycle (Open→Close duration) ───────────────────
        opens_df = (
            df.filter(pl.col("action") == "Open")
            .select(["positionKey", "timestamp"])
            .rename({"timestamp": "open_ts"})
        )
        closes_df = (
            df.filter(pl.col("action").is_in(["Close", "Liquidate"]))
            .select(["positionKey", "timestamp"])
            .rename({"timestamp": "close_ts"})
        )
        lifecycle = (
            opens_df.join(closes_df, on="positionKey", how="inner")
            .with_columns(
                ((pl.col("close_ts") - pl.col("open_ts")) / 3600.0).alias(
                    "duration_hours"
                )
            )
            .filter(pl.col("duration_hours") >= 0)
        )

        if len(lifecycle) > 10:
            dh = lifecycle["duration_hours"]
            _print_box("POSITION LIFECYCLE (open→close duration, sample)")
            print(f"  Matched pairs in sample: {len(lifecycle):>8,}")
            print(
                f"  Mean duration:    {dh.mean():>8.1f} hours  ({dh.mean() / 24:.1f} days)"
            )
            print(f"  Median:           {dh.median():>8.1f} hours")
            print(f"  P10:              {dh.quantile(0.1):>8.1f} hours")
            print(f"  P90:              {dh.quantile(0.9):>8.1f} hours")
            print(f"  P99:              {dh.quantile(0.99):>8.1f} hours")
            buckets = [
                ("<1h", dh < 1),
                ("1-24h", (dh >= 1) & (dh < 24)),
                ("1-7d", (dh >= 24) & (dh < 168)),
                ("7-30d", (dh >= 168) & (dh < 720)),
                (">30d", dh >= 720),
            ]
            print()
            for label, mask in buckets:
                n = int(mask.sum())
                print(f"  {label:<10}  {n:>8,}  ({n / len(dh) * 100:.1f}%)")
            print()

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.hist(dh.clip(0, dh.quantile(0.99) or 0), bins=60)
            ax.set_title("Position lifecycle duration (open→close, clipped to P99)")
            ax.set_xlabel("hours")
            ax.set_ylabel("n positions")
            save_fig(fig, out_dir, "position_lifecycle.png")

        # ── Data quality ───────────────────────────────────────────────
        _print_box("DATA QUALITY (sample)")
        quality_checks = [
            ("price is null", df["price"].is_null().sum()),
            ("price == 0", (df["price"] == 0).sum()),
            ("sizeUsd is null", df["sizeUsd"].is_null().sum()),
            ("sizeUsd == 0", (df["sizeUsd"] == 0).sum()),
            ("collateralUsd null", df["collateralUsd"].is_null().sum()),
            ("leverage is null", df["leverage"].is_null().sum()),
            ("leverage == 0", (df["leverage"] == 0).sum()),
        ]
        any_issue = False
        for label, count in quality_checks:
            if count > 0:
                any_issue = True
                print(f"  ⚠  {label:<26} {count:>8,}  ({count / len(df) * 100:.2f}%)")
        if not any_issue:
            print("  ✓  No null/zero issues found in sample")
        pbar.update()

    await close_client()


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("08_logs_overview")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

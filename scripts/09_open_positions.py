"""
Opening positions EDA — current live exposure.

What this answers:
  - How many positions are currently open?
  - Who is winning / losing unrealized PnL?
  - Leverage and size distribution of live positions
  - Asset / platform / chain concentration
  - Position age: how long have positions been open?
  - Wallet concentration: whales vs retail
  - Largest underwater positions (pipeline risk: liquidation candidates)

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/09_open_positions.py
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

_PROJECTION = {
    "_id": 0,
    "ownerAccount": 1,
    "positionKey": 1,
    "asset": 1,
    "side": 1,
    "sizeUsd": 1,
    "entryPrice": 1,
    "unrealizedPnl": 1,
    "firstOpenedAt": 1,
    "platform": 1,
    "chain": 1,
}
_NOW_TS = int(datetime.now(tz=timezone.utc).timestamp())


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
    col = db["opening_positions"]
    time_filter = time_match_stage("firstOpenedAt", args.start, args.end)

    with tqdm(
        total=4, desc="09 open_positions", unit="step", dynamic_ncols=True
    ) as pbar:
        # ── Total count ────────────────────────────────────────────────
        pbar.set_postfix_str("counting open positions")
        total = await col.count_documents(time_filter)
        _print_box("OPENING POSITIONS — LIVE EXPOSURE")
        print(f"  Total open positions:  {total:>12,}")
        if total == 0:
            print("  Collection is empty.")
            return
        pbar.update()

        # ── Fetch all (no sample — opening_positions is smaller) ───────
        pbar.set_postfix_str(f"fetching all {total:,} open positions")
        pipeline = ([{"$match": time_filter}] if time_filter else []) + [
            {"$project": _PROJECTION}
        ]
        cursor = await col.aggregate(pipeline)
        docs = await cursor.to_list()
        df = pl.from_dicts(docs, infer_schema_length=500)

        n_unique_wallets = df["ownerAccount"].n_unique()
        print(f"  Unique wallets:        {n_unique_wallets:>12,}")
        print(f"  Positions/wallet avg:  {total / n_unique_wallets:>12.1f}")
        print()
        pbar.update()

        # ── Asset / platform / chain ────────────────────────────────────
        pbar.set_postfix_str("asset / platform / side breakdown")
        _print_box("ASSET BREAKDOWN")
        by_asset = (
            df.group_by("asset")
            .agg(
                [
                    pl.len().alias("n"),
                    pl.col("sizeUsd").sum().alias("total_size"),
                    pl.col("unrealizedPnl").sum().alias("total_upnl"),
                ]
            )
            .sort("n", descending=True)
            .head(12)
        )
        print(f"  {'Asset':<14} {'N':>8} {'Total Size $':>14} {'Unrealized PnL $':>18}")
        print("  " + "-" * 58)
        for row in by_asset.iter_rows():
            asset, n, size, upnl = row
            print(f"  {str(asset):<14} {n:>8,} ${size:>13,.0f} ${upnl:>+17,.2f}")
        print()

        _print_box("PLATFORM BREAKDOWN")
        by_plat = (
            df.group_by("platform")
            .agg([pl.len().alias("n"), pl.col("sizeUsd").sum().alias("total_size")])
            .sort("n", descending=True)
        )
        for row in by_plat.iter_rows():
            plat, n, size = row
            print(f"  {str(plat):<24} {n:>8,}  (${size:,.0f} notional)")
        print()

        _print_box("SIDE DISTRIBUTION")
        by_side = df.group_by("side").agg(
            [
                pl.len().alias("n"),
                pl.col("unrealizedPnl").sum().alias("total_upnl"),
                (pl.col("unrealizedPnl") > 0).mean().alias("pct_profitable"),
            ]
        )
        for row in by_side.iter_rows():
            side, n, upnl, pct = row
            print(
                f"  {str(side):<8}  n={n:>8,}  total uPnL=${upnl:>+14,.2f}  profitable={pct:.1%}"
            )
        print()
        pbar.update()

        # ── Unrealized PnL distribution ────────────────────────────────
        pbar.set_postfix_str("PnL / size / age analysis")
        upnl = df["unrealizedPnl"].drop_nulls()
        _print_box("UNREALIZED PnL DISTRIBUTION")
        profitable = int((upnl > 0).sum())
        print(
            f"  Profitable positions:  {profitable:>8,}  ({profitable / len(upnl) * 100:.1f}%)"
        )
        print(
            f"  Underwater positions:  {int((upnl < 0).sum()):>8,}  ({int((upnl < 0).sum()) / len(upnl) * 100:.1f}%)"
        )
        print(f"  Total unrealized PnL:  ${upnl.sum():>+14,.2f}")
        print(f"  Mean uPnL:             ${upnl.mean():>+12,.2f}")
        print(f"  Median uPnL:           ${upnl.median():>+12,.2f}")
        print(f"  P10:                   ${upnl.quantile(0.1):>+12,.2f}")
        print(f"  P90:                   ${upnl.quantile(0.9):>+12,.2f}")
        print()

        upnl_buckets = [
            ("<-$10k", upnl < -10_000),
            ("-$10k to -$1k", (upnl >= -10_000) & (upnl < -1_000)),
            ("-$1k to $0", (upnl >= -1_000) & (upnl < 0)),
            ("$0 to $1k", (upnl >= 0) & (upnl < 1_000)),
            ("$1k to $10k", (upnl >= 1_000) & (upnl < 10_000)),
            (">$10k", upnl >= 10_000),
        ]
        for label, mask in upnl_buckets:
            n = int(mask.sum())
            print(f"  {label:<20}  {n:>8,}  ({n / len(upnl) * 100:.1f}%)")
        print()

        p1, p99 = upnl.quantile(0.01) or 0.0, upnl.quantile(0.99) or 0.0
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(upnl.clip(p1, p99), bins=60)
        ax.set_title("Unrealized PnL distribution (clipped to P1-P99)")
        ax.set_xlabel("unrealizedPnl ($)")
        ax.set_ylabel("n positions")
        save_fig(fig, out_dir, "unrealized_pnl_distribution.png")

        # ── Size distribution ──────────────────────────────────────────
        _print_box("POSITION SIZE (sizeUsd) DISTRIBUTION")
        size = df["sizeUsd"].drop_nulls()
        print(f"  Total notional:   ${size.sum():>14,.0f}")
        print(f"  Mean size:        ${size.mean():>14,.2f}")
        print(f"  Median size:      ${size.median():>14,.2f}")
        print(f"  P90:              ${size.quantile(0.9):>14,.2f}")
        print(f"  P99:              ${size.quantile(0.99):>14,.2f}")
        print(f"  Max:              ${size.max():>14,.2f}")
        print()

        # ── Position age ───────────────────────────────────────────────
        if "firstOpenedAt" in df.columns:
            df = df.with_columns(
                ((pl.lit(_NOW_TS) - pl.col("firstOpenedAt")) / 3600.0).alias("_age_hours")
            )
            age_hours = df["_age_hours"].drop_nulls()
            _print_box("POSITION AGE (hours since firstOpenedAt)")
            print(
                f"  Mean age:    {age_hours.mean():>8.1f} h  ({age_hours.mean() / 24:.1f} days)"
            )
            print(
                f"  Median age:  {age_hours.median():>8.1f} h  ({age_hours.median() / 24:.1f} days)"
            )
            print(
                f"  P90 age:     {age_hours.quantile(0.9):>8.1f} h  ({age_hours.quantile(0.9) / 24:.1f} days)"
            )
            print(
                f"  Max age:     {age_hours.max():>8.1f} h  ({age_hours.max() / 24:.1f} days)"
            )
            age_buckets = [
                ("<1h", age_hours < 1),
                ("1-24h", (age_hours >= 1) & (age_hours < 24)),
                ("1-7d", (age_hours >= 24) & (age_hours < 168)),
                ("7-30d", (age_hours >= 168) & (age_hours < 720)),
                (">30d", age_hours >= 720),
            ]
            print()
            for label, mask in age_buckets:
                n = int(mask.sum())
                print(f"  {label:<10}  {n:>8,}  ({n / len(age_hours) * 100:.1f}%)")
            print()

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.hist(age_hours.clip(0, age_hours.quantile(0.99) or 0), bins=60)
            ax.set_title("Open position age (clipped to P99)")
            ax.set_xlabel("hours")
            ax.set_ylabel("n positions")
            save_fig(fig, out_dir, "position_age.png")

        # ── Wallet concentration ───────────────────────────────────────
        _print_box("WALLET CONCENTRATION")
        wallet_counts = (
            df.group_by("ownerAccount")
            .agg(
                [
                    pl.len().alias("n_positions"),
                    pl.col("sizeUsd").sum().alias("total_size"),
                    pl.col("unrealizedPnl").sum().alias("total_upnl"),
                ]
            )
            .sort("n_positions", descending=True)
        )
        print(
            f"  Wallets with 1 position:   {int((wallet_counts['n_positions'] == 1).sum()):>8,}"
        )
        print(
            f"  Wallets with 2-5 positions:{int(((wallet_counts['n_positions'] >= 2) & (wallet_counts['n_positions'] <= 5)).sum()):>8,}"
        )
        print(
            f"  Wallets with >5 positions: {int((wallet_counts['n_positions'] > 5).sum()):>8,}"
        )
        print()

        _print_box("TOP 10 LARGEST UNDERWATER POSITIONS")
        worst = (
            df.filter(pl.col("unrealizedPnl").is_not_null())
            .sort("unrealizedPnl")
            .head(10)
        )
        print(f"  {'Wallet':<44} {'Asset':<10} {'Side':<6} {'uPnL':>14}")
        print("  " + "-" * 78)
        for row in worst.select(
            ["ownerAccount", "asset", "side", "unrealizedPnl"]
        ).iter_rows():
            wallet, asset, side, upnl = row
            print(
                f"  {str(wallet)[:42]:<44} {str(asset):<10} {str(side):<6} ${upnl:>+13,.2f}"
            )
        print()
        pbar.update()

    await close_client()


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__)
    add_time_range_args(_parser)
    _args = _parser.parse_args()
    _out_dir = get_output_dir("09_open_positions")
    with tee_stdout(_out_dir):
        asyncio.run(main(_args, _out_dir))

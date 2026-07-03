"""
Cross-asset skill transfer analysis — NEW research angle.

What this answers:
  - Is a wallet's skill in SOL perps predictive of its skill in ETH perps?
  - Do wallets specialize in assets or generalize across them?
  - What fraction of wallets show cross-asset vs single-asset skill?

Research significance:
  No published paper tests whether on-chain skill generalizes across assets.
  If skill is asset-specific (high SOL WR does NOT predict high ETH WR),
  then asset-conditional scoring is a novel contribution.
  If skill generalizes (high SOL WR predicts high ETH WR),
  then cross-asset portfolios of wallets are feasible.

Uses closed_positions collection.

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/07_asset_skill_transfer.py
"""

import asyncio

import polars as pl

from scripts._client import get_db


_MIN_TRADES = 5
_SAMPLE_SIZE = 300_000


def _print_box(title: str) -> None:
    border = "╔" + "═" * 60 + "╗"
    inner = f"║  {title:<58}║"
    close = "╚" + "═" * 60 + "╝"
    print(border)
    print(inner)
    print(close)


def _pearson(a: pl.Series, b: pl.Series) -> float:
    combined = pl.DataFrame({"a": a, "b": b}).drop_nulls()
    if len(combined) < 5:
        return float("nan")
    return combined["a"].pearson_corr(combined["b"]) or 0.0


async def main() -> None:
    db = get_db()
    col = db["closed_positions"]

    total = await col.count_documents({})
    _print_box("CROSS-ASSET SKILL TRANSFER ANALYSIS")
    print(f"  Total closed positions:  {total:>12,}")

    cursor = col.aggregate(
        [
            {"$sample": {"size": _SAMPLE_SIZE}},
            {
                "$project": {
                    "_id": 0,
                    "ownerAccount": 1,
                    "asset": 1,
                    "side": 1,
                    "realizedPnl": 1,
                }
            },
        ]
    )
    docs = await cursor.to_list()
    df = pl.from_dicts(docs, infer_schema_length=500)
    print(f"  Sample size:             {len(df):>12,}")
    print()

    # ── Asset coverage per wallet ──────────────────────────────────
    _print_box("WALLET ASSET COVERAGE")
    asset_counts = df.group_by("ownerAccount").agg(
        pl.col("asset").n_unique().alias("n_assets")
    )
    for n in [1, 2, 3, 4, 5]:
        count = int((asset_counts["n_assets"] == n).sum())
        pct = count / len(asset_counts) * 100
        print(f"  {n} asset(s):   {count:>8,}  ({pct:.1f}%)")
    multi = int((asset_counts["n_assets"] > 5).sum())
    print(f"  >5 assets:   {multi:>8,}  ({multi / len(asset_counts) * 100:.1f}%)")
    print()

    # ── Per-asset win rates ────────────────────────────────────────
    _print_box("WIN RATE BY ASSET (top 10)")
    by_asset = (
        df.group_by("asset")
        .agg(
            [
                pl.len().alias("n"),
                (pl.col("realizedPnl") > 0).mean().alias("win_rate"),
                pl.col("realizedPnl").mean().alias("avg_pnl"),
            ]
        )
        .filter(pl.col("n") >= 50)
        .sort("n", descending=True)
        .head(10)
    )
    print(f"  {'Asset':<12} {'N':>8} {'Win%':>8} {'Avg PnL':>12}")
    print("  " + "-" * 44)
    for row in by_asset.iter_rows():
        asset, n, wr, avg_pnl = row
        print(f"  {str(asset):<12} {n:>8,} {wr:>7.1%} ${avg_pnl:>+11,.2f}")
    print()

    # ── Cross-asset correlation (wallet win rate per asset) ────────
    _print_box("CROSS-ASSET SKILL CORRELATION")
    print(f"  (wallets with ≥{_MIN_TRADES} trades in BOTH assets)")
    print()

    wallet_asset_wr = (
        df.group_by(["ownerAccount", "asset"])
        .agg(
            [
                pl.len().alias("n"),
                (pl.col("realizedPnl") > 0).mean().alias("win_rate"),
            ]
        )
        .filter(pl.col("n") >= _MIN_TRADES)
    )

    # Get top 5 assets by total positions
    top_assets = (
        df.group_by("asset")
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") >= 200)
        .sort("n", descending=True)
        .head(5)["asset"]
        .to_list()
    )

    if len(top_assets) < 2:
        print("  Not enough assets in sample for cross-asset analysis.")
        return

    print(f"  Top assets analyzed: {top_assets}")
    print()
    print(
        f"  {'Asset A':<12} {'Asset B':<12} {'N wallets':>10} {'Pearson r':>12}  {'Interpretation'}"
    )
    print("  " + "-" * 70)

    for i, asset_a in enumerate(top_assets):
        for asset_b in top_assets[i + 1 :]:
            wrs_a = (
                wallet_asset_wr.filter(pl.col("asset") == asset_a)
                .select(["ownerAccount", "win_rate"])
                .rename({"win_rate": "wr_a"})
            )
            wrs_b = (
                wallet_asset_wr.filter(pl.col("asset") == asset_b)
                .select(["ownerAccount", "win_rate"])
                .rename({"win_rate": "wr_b"})
            )
            combined = wrs_a.join(wrs_b, on="ownerAccount", how="inner")
            n_w = len(combined)
            if n_w < 5:
                continue
            r = _pearson(combined["wr_a"], combined["wr_b"])
            if abs(r) < 0.2:
                interp = "Asset-specific skill"
            elif abs(r) < 0.5:
                interp = "Weak transfer"
            else:
                interp = "Strong transfer"
            print(f"  {asset_a:<12} {asset_b:<12} {n_w:>10,} {r:>+12.3f}  {interp}")
    print()
    print("  RESEARCH HYPOTHESIS:")
    print("  r < 0.3 → skills are asset-specific → asset-conditional scoring needed")
    print("  r > 0.5 → skills generalize → single cross-asset score sufficient")


if __name__ == "__main__":
    asyncio.run(main())

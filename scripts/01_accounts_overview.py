"""
Accounts collection overview.

What this answers:
  - How many unique trader accounts exist?
  - PnL / ROI / win-rate distributions across the population
  - Trade-count distribution (inputs Bayesian feasibility in script 04)
  - Platform + chain coverage

Run:
    export MONGO_SOURCE_URL="mongodb://..."
    uv run python scripts/01_accounts_overview.py
"""

import asyncio

import polars as pl

from scripts._client import get_db


_SAMPLE_SIZE = 100_000
_PROJECTION = {
    "_id": 1,
    "platform": 1,
    "chain": 1,
    "PNL": 1,
    "ROI": 1,
    "profitableRatio": 1,
    "closedPositionCount": 1,
    "openingPositionCount": 1,
    "realizedPnl": 1,
    "tradedAssets": 1,
    "lastTradedAt": 1,
}


def _print_box(title: str) -> None:
    border = "╔" + "═" * 46 + "╗"
    inner = f"║  {title:<44}║"
    close = "╚" + "═" * 46 + "╝"
    print(border)
    print(inner)
    print(close)


def _percentiles(series: pl.Series, qs: list[float]) -> list[float]:
    return [series.quantile(q) or 0.0 for q in qs]


async def main() -> None:
    db = get_db()
    col = db["accounts"]

    # ── Total count ────────────────────────────────────────────────
    total = await col.count_documents({})
    _print_box("ACCOUNTS OVERVIEW")
    print(f"  Total accounts:    {total:>12,}")

    # ── Sample for distribution analysis ──────────────────────────
    cursor = col.aggregate(
        [
            {"$sample": {"size": _SAMPLE_SIZE}},
            {"$project": _PROJECTION},
        ]
    )
    docs = await cursor.to_list()
    df = pl.from_dicts(docs, infer_schema_length=500)

    # ── Platform / chain breakdown ─────────────────────────────────
    print()
    _print_box("PLATFORM BREAKDOWN (sample)")
    plat = df.group_by("platform").agg(pl.len().alias("n")).sort("n", descending=True)
    for row in plat.iter_rows():
        print(f"  {row[0]:<20s}  {row[1]:>8,}  ({row[1] / len(df) * 100:.1f}%)")

    print()
    _print_box("CHAIN BREAKDOWN (sample)")
    chain = df.group_by("chain").agg(pl.len().alias("n")).sort("n", descending=True)
    for row in chain.iter_rows():
        print(f"  {row[0]:<20s}  {row[1]:>8,}  ({row[1] / len(df) * 100:.1f}%)")

    # ── PnL statistics ─────────────────────────────────────────────
    print()
    _print_box("PnL STATISTICS (sample)")
    pnl = df["PNL"].drop_nulls()
    qs = _percentiles(pnl, [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    print(f"  N accounts with PnL:  {len(pnl):>8,}")
    print(f"  Mean PnL:             ${pnl.mean():>+12,.2f}")
    print(f"  P10:                  ${qs[0]:>+12,.2f}")
    print(f"  P25:                  ${qs[1]:>+12,.2f}")
    print(f"  Median:               ${qs[2]:>+12,.2f}")
    print(f"  P75:                  ${qs[3]:>+12,.2f}")
    print(f"  P90:                  ${qs[4]:>+12,.2f}")
    print(f"  P95:                  ${qs[5]:>+12,.2f}")
    print(f"  P99:                  ${qs[6]:>+12,.2f}")
    positive = (pnl > 0).sum()
    print(f"  Profitable accounts:  {positive:>8,}  ({positive / len(pnl) * 100:.1f}%)")

    # ── ROI statistics ─────────────────────────────────────────────
    print()
    _print_box("ROI STATISTICS (sample)")
    roi = df["ROI"].drop_nulls()
    rqs = _percentiles(roi, [0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
    print(f"  Mean ROI:             {roi.mean():>+8.2%}")
    print(f"  Median ROI:           {rqs[2]:>+8.2%}")
    print(f"  P10:                  {rqs[0]:>+8.2%}")
    print(f"  P90:                  {rqs[4]:>+8.2%}")
    print(f"  P99:                  {rqs[5]:>+8.2%}")

    # ── Win-rate distribution ──────────────────────────────────────
    print()
    _print_box("WIN-RATE (profitableRatio) DISTRIBUTION")
    wr = df["profitableRatio"].drop_nulls()
    wrqs = _percentiles(wr, [0.1, 0.25, 0.5, 0.75, 0.9])
    print(f"  Mean win rate:        {wr.mean():>+8.2%}")
    print(f"  Median:               {wrqs[2]:>+8.2%}")
    print(f"  P10:                  {wrqs[0]:>+8.2%}")
    print(f"  P90:                  {wrqs[4]:>+8.2%}")
    buckets = [
        ("<20%", wr < 0.2),
        ("20-40%", (wr >= 0.2) & (wr < 0.4)),
        ("40-60%", (wr >= 0.4) & (wr < 0.6)),
        ("60-80%", (wr >= 0.6) & (wr < 0.8)),
        (">80%", wr >= 0.8),
    ]
    for label, mask in buckets:
        n = int(mask.sum())
        print(f"  {label:<10s}  {n:>7,}  ({n / len(wr) * 100:.1f}%)")

    # ── Closed trade count distribution ───────────────────────────
    print()
    _print_box("CLOSED TRADE COUNT DISTRIBUTION")
    tc = df["closedPositionCount"].drop_nulls().cast(pl.Int64)
    thresholds = [1, 5, 10, 20, 50, 100, 200, 500]
    for thresh in thresholds:
        n = int((tc >= thresh).sum())
        print(f"  ≥{thresh:<4d} trades:     {n:>8,}  ({n / len(tc) * 100:.1f}%)")

    # ── Asset diversification ──────────────────────────────────────
    print()
    _print_box("ASSET DIVERSIFICATION (sample)")
    if "tradedAssets" in df.columns:
        n_assets = df["tradedAssets"].list.len()
        print(f"  Mean assets per wallet:  {n_assets.mean():.2f}")
        print(f"  Median:                  {n_assets.median():.1f}")
        for n in [1, 2, 3, 5]:
            count = int((n_assets == n).sum())
            print(
                f"  {n} asset(s):             {count:>7,}  ({count / len(df) * 100:.1f}%)"
            )
        multi = int((n_assets > 3).sum())
        print(f"  >3 assets:               {multi:>7,}  ({multi / len(df) * 100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())

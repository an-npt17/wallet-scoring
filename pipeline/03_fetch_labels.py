"""
Stage 3: Fetch ground-truth PnL labels from MongoDB closed_positions via beanie.

Uses realizedPnl (authoritative closed PnL, no reconstruction).
Outputs two files:
  - labels_raw.parquet  — one row per closed position
  - labels.parquet      — one row per wallet (aggregated)

Output: data/processed/labels.parquet, data/processed/labels_raw.parquet

Run:
    uv run python pipeline/03_fetch_labels.py
"""
import asyncio
import logging

import polars as pl

from database.mongo.schema import ClosedPosition
from pipeline._paths import LABELS_PATH, PROCESSED_DIR
from src.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def _fetch_closed_positions() -> pl.DataFrame:
    total = await ClosedPosition.count()
    logger.info("closed_positions: %s documents", f"{total:,}")

    docs = await ClosedPosition.aggregate([
        {
            "$project": {
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
        }
    ]).to_list()

    logger.info("Fetched %s documents", f"{len(docs):,}")
    return pl.from_dicts(docs, infer_schema_length=1000)


def _aggregate_wallet_labels(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.group_by("ownerAccount")
        .agg([
            pl.len().alias("n_closed"),
            pl.col("realizedPnl").sum().alias("total_realized_pnl"),
            pl.col("realizedPnl").mean().alias("avg_realized_pnl"),
            (pl.col("realizedPnl") > 0).mean().alias("realized_win_rate"),
            pl.col("lastClosedAt").max().alias("last_closed_at"),
            pl.col("asset").n_unique().alias("n_assets_traded"),
        ])
        .rename({"ownerAccount": "wallet"})
    )


async def _run() -> None:
    await init_db()

    raw = await _fetch_closed_positions()
    logger.info("Raw labels shape: %s", raw.shape)

    raw_path = PROCESSED_DIR / "labels_raw.parquet"
    raw.write_parquet(raw_path)
    logger.info("Saved raw → %s", raw_path)

    wallet_labels = _aggregate_wallet_labels(raw)
    logger.info("Wallet-level labels: %s wallets", f"{len(wallet_labels):,}")

    wallet_labels.write_parquet(LABELS_PATH)
    logger.info("Saved → %s", LABELS_PATH)

    wr = wallet_labels["realized_win_rate"].drop_nulls()
    print(f"\nLabel distribution (realized_win_rate):")
    print(f"  mean={wr.mean():.3f}  median={wr.median():.3f}  std={wr.std():.3f}")
    print(f"  wallets WR > 0.5: {(wr > 0.5).sum():,}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

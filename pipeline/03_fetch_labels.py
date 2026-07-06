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
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from database.mongo.schema import ClosedPosition
from pipeline._paths import LABELS_PATH, PROCESSED_DIR
from pipeline._report import get_output_dir, save_fig, tee_stdout
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


async def _run(out_dir: Path) -> None:
    raw_path = PROCESSED_DIR / "labels_raw.parquet"
    with tqdm(total=4, desc="Stage 3", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("init db")
        await init_db()
        pbar.update()

        pbar.set_postfix_str("fetching closed_positions")
        raw = await _fetch_closed_positions()
        logger.info("Raw labels shape: %s", raw.shape)
        pbar.update()

        pbar.set_postfix_str("aggregating wallet labels")
        wallet_labels = _aggregate_wallet_labels(raw)
        logger.info("Wallet-level labels: %s wallets", f"{len(wallet_labels):,}")
        pbar.update()

        pbar.set_postfix_str("saving parquet files")
        raw.write_parquet(raw_path)
        logger.info("Saved raw → %s", raw_path)
        wallet_labels.write_parquet(LABELS_PATH)
        logger.info("Saved → %s", LABELS_PATH)
        pbar.update()

    wr = wallet_labels["realized_win_rate"].drop_nulls()
    print(f"\nLabel distribution (realized_win_rate):")
    print(f"  mean={wr.mean():.3f}  median={wr.median():.3f}  std={wr.std():.3f}")
    print(f"  wallets WR > 0.5: {(wr > 0.5).sum():,}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(wr, bins=50)
    ax.set_title("Ground-truth label distribution (realized_win_rate)")
    ax.set_xlabel("realized_win_rate")
    ax.set_ylabel("n wallets")
    save_fig(fig, out_dir, "realized_win_rate_distribution.png")


def main() -> None:
    out_dir = get_output_dir("03_fetch_labels")
    with tee_stdout(out_dir):
        asyncio.run(_run(out_dir))


if __name__ == "__main__":
    main()

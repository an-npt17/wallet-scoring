"""
Stage 4: Compute B1-B5 baseline scores from MongoDB via beanie.

Baselines (research-proposal.md Section 5.3):
  B1 — Existing composite from daily_trader_rankings
  B2 — Raw PnL (accounts.PNL)
  B3 — Raw ROI (accounts.ROI)
  B4 — Win-rate (accounts.profitableRatio)
  B5 — Sharpe ratio computed from accounts.logs daily PnL series

Output: data/processed/baselines.parquet

Run:
    uv run python pipeline/04_compute_baselines.py
"""

import asyncio
import logging
import math
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from database.mongo.schema import Account, DailyTraderRanking
from pipeline._paths import BASELINES_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.db import init_db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)


async def _fetch_accounts() -> pl.DataFrame:
    total = await Account.count()
    logger.info("accounts: %s documents", f"{total:,}")

    docs = await Account.aggregate(
        [
            {
                "$addFields": {
                    "logsArray": {"$objectToArray": {"$ifNull": ["$logs", {}]}}
                }
            },
            {
                "$addFields": {
                    "logsCount": {"$size": "$logsArray"},
                    "logsSum": {"$sum": "$logsArray.v"},
                    "logsSumSq": {
                        "$sum": {
                            "$map": {
                                "input": "$logsArray",
                                "as": "l",
                                "in": {"$multiply": ["$$l.v", "$$l.v"]},
                            }
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "account": 1,
                    "PNL": 1,
                    "ROI": 1,
                    "profitableRatio": 1,
                    "closedPositionCount": 1,
                    "logsCount": 1,
                    "logsSum": 1,
                    "logsSumSq": 1,
                }
            },
        ]
    ).to_list()

    logger.info("Fetched %s account docs", f"{len(docs):,}")
    return pl.from_dicts(docs, infer_schema_length=500)


async def _fetch_latest_rankings() -> list[dict]:
    doc = await DailyTraderRanking.find_one(sort=[("date", -1)])
    if doc is None:
        return []
    traders = doc.traders
    logger.info("Latest ranking snapshot: %s traders", len(traders))
    return [t.model_dump() for t in traders]


def _add_sharpe_column(df: pl.DataFrame) -> pl.DataFrame:
    mean = pl.col("logsSum") / pl.col("logsCount")
    variance = (pl.col("logsSumSq") - pl.col("logsCount") * mean**2) / (
        pl.col("logsCount") - 1
    )
    std = variance.sqrt()
    return (
        df.with_columns(mean.alias("_mean"), std.alias("_std"))
        .with_columns(
            pl.when((pl.col("logsCount") >= 5) & (pl.col("_std") > 1e-12))
            .then(pl.col("_mean") / pl.col("_std") * math.sqrt(365))
            .otherwise(None)
            .alias("b5_sharpe")
        )
        .drop(["logsCount", "logsSum", "logsSumSq", "_mean", "_std"])
    )


async def _run(out_dir: Path) -> None:
    with tqdm(total=4, desc="Stage 4", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("init db")
        await init_db()
        pbar.update()

        pbar.set_postfix_str("fetching accounts + rankings")
        accounts_df, ranking_rows = await asyncio.gather(
            _fetch_accounts(),
            _fetch_latest_rankings(),
        )
        pbar.update()

        pbar.set_postfix_str("computing B5 Sharpe (vectorized)")
        baselines = _add_sharpe_column(
            accounts_df.rename(
                {
                    "account": "wallet",
                    "PNL": "b2_pnl",
                    "ROI": "b3_roi",
                    "profitableRatio": "b4_win_rate",
                }
            )
        )
        if ranking_rows:
            b1 = (
                pl.from_dicts(ranking_rows, infer_schema_length=200)
                .rename({"trader_address": "wallet", "score": "b1_composite"})
                .select(["wallet", "b1_composite"])
            )
            baselines = baselines.join(b1, on="wallet", how="left")
        else:
            baselines = baselines.with_columns(
                pl.lit(None).cast(pl.Float64).alias("b1_composite")
            )
        pbar.update()

        pbar.set_postfix_str(f"saving → {BASELINES_PATH}")
        baselines.write_parquet(BASELINES_PATH)
        logger.info("Saved → %s  (%s wallets)", BASELINES_PATH, f"{len(baselines):,}")
        pbar.update()

    print("\nBaseline non-null coverage:")
    coverage_cols: list[str] = []
    coverage_counts: list[int] = []
    for col_name in ["b1_composite", "b2_pnl", "b3_roi", "b4_win_rate", "b5_sharpe"]:
        if col_name in baselines.columns:
            n = baselines[col_name].drop_nulls().len()
            coverage_cols.append(col_name)
            coverage_counts.append(n)
            print(f"  {col_name:<18}: {n:>10,}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(coverage_cols, coverage_counts)
    ax.set_title("Baseline non-null coverage")
    ax.set_ylabel("n wallets")
    save_fig(fig, out_dir, "baseline_coverage.png")


def main() -> None:
    out_dir = get_output_dir("04_compute_baselines")
    with tee_stdout(out_dir):
        asyncio.run(_run(out_dir))


if __name__ == "__main__":
    main()

"""
Stage 2: Compute per-wallet skill features from reconstructed positions.

Input:  data/processed/positions.parquet
Output: data/processed/wallet_features.parquet

Run:
    uv run python pipeline/02_compute_features.py
"""

import logging
import time

import polars as pl

from pipeline._paths import FEATURES_PATH, MIN_TRADES_FILTER, POSITIONS_PATH
from src.features.skill_computer import SkillComputerService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Stage 2: Compute wallet features from %s", POSITIONS_PATH)
    t0 = time.perf_counter()

    positions = pl.read_parquet(POSITIONS_PATH)
    logger.info(
        "Loaded %s positions across %s wallets",
        f"{len(positions):,}",
        f"{positions['wallet'].n_unique():,}",
    )

    computer = SkillComputerService()
    features = computer.compute(positions)

    n_before = len(features)
    features = features.filter(pl.col("n_trades") >= MIN_TRADES_FILTER)
    elapsed = time.perf_counter() - t0

    logger.info(
        "Wallets: %s total → %s with ≥%d trades  (%.1fs)",
        f"{n_before:,}",
        f"{len(features):,}",
        MIN_TRADES_FILTER,
        elapsed,
    )
    logger.info("Feature columns: %s", features.columns)

    features.write_parquet(FEATURES_PATH)
    logger.info("Saved → %s", FEATURES_PATH)


if __name__ == "__main__":
    main()

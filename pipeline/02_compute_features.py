"""
Stage 2: Compute per-wallet skill features from reconstructed positions.

Input:  data/processed/positions.parquet
Output: data/processed/wallet_features.parquet

Run:
    uv run python pipeline/02_compute_features.py
"""

import logging
import time
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._paths import FEATURES_PATH, MIN_TRADES_FILTER, POSITIONS_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.features.skill_computer import SkillComputerService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)


def _run(out_dir: Path) -> None:
    t0 = time.perf_counter()
    with tqdm(total=4, desc="Stage 2", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {POSITIONS_PATH}")
        positions = pl.read_parquet(POSITIONS_PATH)
        logger.info(
            "Loaded %s positions across %s wallets",
            f"{len(positions):,}",
            f"{positions['wallet'].n_unique():,}",
        )
        pbar.update()

        pbar.set_postfix_str("computing skill features")
        features = SkillComputerService().compute(positions)
        pbar.update()

        pbar.set_postfix_str(f"filtering ≥{MIN_TRADES_FILTER} trades")
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
        pbar.update()

        pbar.set_postfix_str(f"saving → {FEATURES_PATH}")
        features.write_parquet(FEATURES_PATH)
        logger.info("Saved → %s", FEATURES_PATH)
        pbar.update()

    for col_name, label in [
        ("overall_win_rate", "Overall win rate"),
        ("n_trades", "Trade count"),
    ]:
        if col_name not in features.columns:
            continue
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(features[col_name].drop_nulls(), bins=50)
        ax.set_title(f"{label} distribution (post-filter wallets)")
        ax.set_xlabel(col_name)
        ax.set_ylabel("n wallets")
        save_fig(fig, out_dir, f"{col_name}_distribution.png")


def main() -> None:
    out_dir = get_output_dir("02_compute_features")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

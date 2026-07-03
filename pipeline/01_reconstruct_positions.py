"""
Stage 1: Reconstruct completed positions from raw log events.

Input:  logs.json (local file, ~40M rows)
Output: data/processed/positions.parquet

Each output row is one matched Open→Close/Liquidate pair.
Positions without a Close event (still open) are excluded.

Run:
    uv run python pipeline/01_reconstruct_positions.py
"""

import logging
import time

from pipeline.config import DATA_PATH, POSITIONS_PATH
from src.features.position_builder import PositionBuilderService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Stage 1: Reconstruct positions from %s", DATA_PATH)
    t0 = time.perf_counter()

    builder = PositionBuilderService(DATA_PATH)
    positions = builder.build()

    elapsed = time.perf_counter() - t0
    logger.info("Reconstructed %s positions in %.1fs", f"{len(positions):,}", elapsed)

    n_long = int((positions["side"] == "Long").sum())
    n_short = int((positions["side"] == "Short").sum())
    win_rate = float(positions["win"].mean() or 0.0)
    logger.info(
        "Long: %s  Short: %s  Win rate: %.3f", f"{n_long:,}", f"{n_short:,}", win_rate
    )

    positions.write_parquet(POSITIONS_PATH)
    logger.info("Saved → %s  (%s rows)", POSITIONS_PATH, f"{len(positions):,}")


if __name__ == "__main__":
    main()

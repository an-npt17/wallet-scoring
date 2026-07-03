"""
Stage 1: Reconstruct completed positions from MongoDB logs collection.

Three parallel server-side $group aggregations via beanie (no raw event transfer):
  - First Open per positionKey → entry fields
  - Last Close/Liquidate per positionKey → exit fields
  - Liquidate count per wallet → liquidation count

Output: data/processed/positions.parquet

Run:
    uv run python pipeline/01_reconstruct_positions.py
"""
import asyncio
import logging
import time

from pipeline._paths import POSITIONS_PATH
from src.db import init_db
from src.features.position_builder import PositionBuilderService

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def _run() -> None:
    await init_db()
    t0 = time.perf_counter()
    logger.info("Stage 1: Reconstruct positions from MongoDB logs collection")

    positions = await PositionBuilderService().build()

    elapsed = time.perf_counter() - t0
    logger.info("Reconstructed %s positions in %.1fs", f"{len(positions):,}", elapsed)

    n_long = int((positions["side"] == "Long").sum())
    n_short = int((positions["side"] == "Short").sum())
    win_rate = float(positions["win"].mean() or 0.0)
    logger.info("Long: %s  Short: %s  Win rate: %.3f", f"{n_long:,}", f"{n_short:,}", win_rate)

    positions.write_parquet(POSITIONS_PATH)
    logger.info("Saved → %s  (%s rows)", POSITIONS_PATH, f"{len(positions):,}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

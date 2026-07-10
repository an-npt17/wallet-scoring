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
from pathlib import Path

import matplotlib.pyplot as plt
from tqdm import tqdm

from pipeline._paths import POSITIONS_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.db import init_db
from src.features.position_builder import PositionBuilderService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)


async def _run(out_dir: Path) -> None:
    t0 = time.perf_counter()
    with tqdm(total=3, desc="Stage 1", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("init db")
        await init_db()
        pbar.update()

        pbar.set_postfix_str("reconstructing positions from logs")
        positions = await PositionBuilderService().build()
        elapsed = time.perf_counter() - t0
        n_long = int((positions["side"] == "Long").sum())
        n_short = int((positions["side"] == "Short").sum())
        win_rate = float(positions["win"].mean() or 0.0)
        logger.info(
            "Reconstructed %s positions in %.1fs — Long %s  Short %s  WR %.3f",
            f"{len(positions):,}",
            elapsed,
            f"{n_long:,}",
            f"{n_short:,}",
            win_rate,
        )
        pbar.update()

        fig, ax = plt.subplots(figsize=(5, 4))
        ax.bar(["Long", "Short"], [n_long, n_short])
        ax.set_title("Reconstructed positions by side")
        ax.set_ylabel("n positions")
        save_fig(fig, out_dir, "positions_by_side.png")

        pbar.set_postfix_str(f"saving → {POSITIONS_PATH}")
        positions.write_parquet(POSITIONS_PATH)
        logger.info("Saved → %s  (%s rows)", POSITIONS_PATH, f"{len(positions):,}")
        pbar.update()


def main() -> None:
    out_dir = get_output_dir("01_reconstruct_positions")
    with tee_stdout(out_dir):
        asyncio.run(_run(out_dir))


if __name__ == "__main__":
    main()

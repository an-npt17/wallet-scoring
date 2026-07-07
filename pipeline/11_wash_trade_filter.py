"""
Stage 11: B8 — Wash-trade / bot detection pre-filter (Ashfaq 2023, arXiv:2305.01543).

The original NFT wash-trading heuristic detects colluding buyer-seller pairs
via cycle detection on a two-party trade graph (reference implementation:
github.com/Dreamerryao/nft-wash-trading). Our perp position data has NO
counterparty field — positions are wallet-vs-pool/protocol, not wallet-vs-
wallet — so the colluding-pair cycle detection does not transfer directly.

ADAPTATION (documented, not a literal reproduction): we detect the same
underlying behavioral signature the original heuristic targets — rapid,
repetitive round-tripping designed to farm volume rather than express a
genuine directional view — using same-wallet round-trip frequency and
holding time instead of a two-party graph. A wallet is flagged if its
median position duration is very short AND it trades often enough that the
pattern looks systematic rather than incidental.

This is used as a PRE-FILTER (exclude flagged wallets before ranking), not a
ranking baseline to beat, per research-proposal.md sec 5.3.

Input:  data/processed/positions.parquet
Output: data/processed/wash_trade_flags.parquet
        pipeline/outputs/11_wash_trade_filter/

Run:
    uv run python -m pipeline.11_wash_trade_filter
"""

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._paths import MIN_TRADES_FILTER, POSITIONS_PATH, PROCESSED_DIR
from pipeline._report import get_output_dir, save_fig, tee_stdout

WASH_TRADE_FLAGS_PATH = PROCESSED_DIR / "wash_trade_flags.parquet"

_MAX_MEDIAN_DURATION_HOURS = 1.0
_MIN_TRADES_FOR_PATTERN = 20


def _print_box(title: str) -> None:
    width = 60
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _run(out_dir: Path) -> None:
    with tqdm(total=2, desc="Stage 11", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {POSITIONS_PATH}")
        positions = pl.read_parquet(POSITIONS_PATH)
        pbar.update()

        pbar.set_postfix_str("computing round-trip pattern per wallet")
        wallet_stats = positions.group_by("wallet").agg(
            [
                pl.len().alias("n_trades"),
                pl.col("duration_hours").median().alias("median_duration_hours"),
                (pl.col("duration_hours") < 1.0).mean().alias("frac_under_1h"),
            ]
        ).filter(pl.col("n_trades") >= MIN_TRADES_FILTER)
        pbar.update()

    wallet_stats = wallet_stats.with_columns(
        (
            (pl.col("median_duration_hours") < _MAX_MEDIAN_DURATION_HOURS)
            & (pl.col("n_trades") >= _MIN_TRADES_FOR_PATTERN)
        ).alias("b8_wash_flag")
    )
    wallet_stats.write_parquet(WASH_TRADE_FLAGS_PATH)

    n_flagged = int(wallet_stats["b8_wash_flag"].sum())
    pct_flagged = n_flagged / len(wallet_stats) * 100

    _print_box("B8 — WASH-TRADE / BOT PRE-FILTER")
    print(f"  Wallets evaluated:  {len(wallet_stats):,}")
    print(f"  Flag rule: median duration < {_MAX_MEDIAN_DURATION_HOURS}h AND "
          f"n_trades >= {_MIN_TRADES_FOR_PATTERN}")
    print(f"  Flagged as likely wash/bot: {n_flagged:,} ({pct_flagged:.2f}%)")
    print("  Reference: Ashfaq (2023) flags 0.11% of wallets in NFT markets")
    print("  (different market structure — see docstring adaptation note).")
    print()
    print(f"  Saved -> {WASH_TRADE_FLAGS_PATH}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(wallet_stats["median_duration_hours"].clip(0, 48), bins=50)
    ax.axvline(_MAX_MEDIAN_DURATION_HOURS, color="red", linestyle="--", label="flag threshold")
    ax.set_title("Median position duration per wallet (clipped at 48h)")
    ax.set_xlabel("hours")
    ax.set_ylabel("n wallets")
    ax.legend()
    save_fig(fig, out_dir, "duration_distribution.png")


def main() -> None:
    out_dir = get_output_dir("11_wash_trade_filter")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

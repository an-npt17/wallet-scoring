"""
Stage 12: B6 — zScore reimplementation on perp data (Anon/Kandaswamy et al. 2025).

The original (arXiv:2507.20494) trains a deep residual neural network on
Uniswap v3 LP + swap behavior, producing a Liquidity-Provision Score and a
Swap-Behavior Score from rule-based "blueprint" features: volume, frequency,
holding time, and withdrawal discipline.

SCOPE ADAPTATION: perp positions have no LP-side data, and our position
schema (Position, src/features/schemas.py) does not carry Deposit/Withdraw
events, so "withdrawal discipline" is approximated by liquidation avoidance
(the closest analog: a liquidation is a forced, undisciplined exit). The
residual neural network is NOT reproduced here — the blueprint features are
combined with a simple equal-weighted z-score average instead of a learned
network, since (a) the original's supervised targets don't transfer to this
domain and (b) a rule-based composite is what the network is stated to
approximate for edge cases (see docstring in references.bib entry
kandaswamy_deep_2025). This is documented as a simplification, not a full
reproduction — the network component is future work if a labeled target for
perp "swap-behavior" quality is defined.

Input:  data/processed/positions.parquet
Output: data/processed/zscore_baseline.parquet
        pipeline/outputs/12_zscore_baseline/

Run:
    uv run python -m pipeline.12_zscore_baseline --holdout-days 45
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._numeric import as_int
from pipeline._paths import MIN_TRADES_FILTER, POSITIONS_PATH, PROCESSED_DIR
from pipeline._report import get_output_dir, save_fig, tee_stdout

ZSCORE_BASELINE_PATH = PROCESSED_DIR / "zscore_baseline.parquet"

_BLUEPRINT_COLS = ["volume_z", "frequency_z", "holding_time_z", "discipline_z"]


def _print_box(title: str) -> None:
    width = 60
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _split_train_test(
    positions: pl.DataFrame, holdout_days: int
) -> tuple[pl.DataFrame, pl.DataFrame]:
    max_ts = as_int(positions["close_ts"].max())
    cutoff_ts = max_ts - holdout_days * 86400
    train = positions.filter(pl.col("close_ts") < cutoff_ts)
    test = positions.filter(pl.col("close_ts") >= cutoff_ts)
    return train, test


def _future_labels(test: pl.DataFrame) -> pl.DataFrame:
    return (
        test.group_by("wallet")
        .agg(
            [
                pl.len().alias("n_future_trades"),
                pl.col("win").mean().alias("future_win_rate"),
                pl.col("pnl").sum().alias("future_pnl"),
            ]
        )
        .filter(pl.col("n_future_trades") >= 5)
    )


def _z(col: str) -> pl.Expr:
    mean_ = pl.col(col).mean()
    std_ = pl.col(col).std()
    return pl.when(std_ > 0).then((pl.col(col) - mean_) / std_).otherwise(0.0)


def _run(out_dir: Path, holdout_days: int) -> None:
    with tqdm(total=3, desc="Stage 12", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {POSITIONS_PATH}")
        positions = pl.read_parquet(POSITIONS_PATH)
        pbar.update()

        pbar.set_postfix_str("splitting train/test (same as stages 6-10)")
        train, test = _split_train_test(positions, holdout_days)
        pbar.update()

        pbar.set_postfix_str("computing blueprint features (train window)")
        blueprint = (
            train.group_by("wallet")
            .agg(
                [
                    pl.len().alias("n_trades"),
                    pl.col("entry_size_usd").sum().alias("volume"),
                    pl.col("duration_hours").median().alias("holding_time"),
                    pl.col("n_liquidations").max().fill_null(0).alias("n_liquidations"),
                    pl.col("open_ts").min().alias("first_ts"),
                    pl.col("open_ts").max().alias("last_ts"),
                ]
            )
            .filter(pl.col("n_trades") >= MIN_TRADES_FILTER)
            .with_columns(
                [
                    (
                        (pl.col("last_ts") - pl.col("first_ts")).cast(pl.Float64) / 86400.0
                    ).clip(lower_bound=1.0).alias("active_span_days"),
                    (
                        pl.col("n_liquidations").cast(pl.Float64)
                        / pl.col("n_trades").cast(pl.Float64)
                    ).alias("liquidation_rate"),
                ]
            )
            .with_columns(
                (pl.col("n_trades").cast(pl.Float64) / pl.col("active_span_days")).alias(
                    "frequency"
                )
            )
        )
        pbar.update()

    blueprint = blueprint.with_columns(
        [
            _z("volume").alias("volume_z"),
            _z("frequency").alias("frequency_z"),
            (-_z("holding_time")).alias("holding_time_z"),
            (-_z("liquidation_rate")).alias("discipline_z"),
        ]
    ).with_columns(pl.mean_horizontal(_BLUEPRINT_COLS).alias("b6_zscore"))

    future = _future_labels(test)
    result = blueprint.join(future, on="wallet", how="inner")
    result.write_parquet(ZSCORE_BASELINE_PATH)

    _print_box("B6 — zScore REIMPLEMENTATION (rule-based, no NN — see docstring)")
    print(f"  Wallets scored:            {len(blueprint):,}")
    print(f"  Wallets with future labels: {len(result):,}")
    print()
    print("  Blueprint component means:")
    for col in ["volume", "frequency", "holding_time", "liquidation_rate"]:
        print(f"    {col:<18} mean={blueprint[col].mean():.4f}")
    print()
    print(f"  Saved -> {ZSCORE_BASELINE_PATH}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(blueprint["b6_zscore"].drop_nulls(), bins=50)
    ax.set_title("B6 zScore (rule-based reimplementation) distribution")
    ax.set_xlabel("b6_zscore")
    ax.set_ylabel("n wallets")
    save_fig(fig, out_dir, "zscore_distribution.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout-days", type=int, default=45)
    args = parser.parse_args()
    out_dir = get_output_dir("12_zscore_baseline")
    with tee_stdout(out_dir):
        _run(out_dir, args.holdout_days)


if __name__ == "__main__":
    main()

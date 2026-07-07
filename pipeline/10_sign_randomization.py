"""
Stage 10: B7 — Sign-randomization skill classifier (Gomez-Cram et al. 2026).

Reproduces the "skilled winner" classifier from arXiv:2605.02287 (synthesized
in Nechepurenko 2026). Original code/labels are not released (confirmed via
search, see literature-review.md sec 7b), so this is implemented from the
paper's method description: an exact binomial test of each wallet's
directional-accuracy persistence against the population base rate, using the
same train/test split as stages 6-9 so it can be compared against B1-B5 and
bayes_score out-of-sample (stage 13).

The original paper classifies 3.14% of Polymarket accounts as "skilled
winners" at their significance threshold — this stage reports the analogous
figure for our perp wallet population as a direct reproduction check.

Input:  data/processed/positions.parquet
Output: data/processed/sign_randomization_scores.parquet
        pipeline/outputs/10_sign_randomization/

Run:
    uv run python -m pipeline.10_sign_randomization --holdout-days 45
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from scipy import stats
from tqdm import tqdm

from pipeline._numeric import as_float, as_int
from pipeline._paths import MIN_TRADES_FILTER, POSITIONS_PATH, PROCESSED_DIR
from pipeline._report import get_output_dir, save_fig, tee_stdout

_ALPHA = 0.05
SIGN_RANDOMIZATION_PATH = PROCESSED_DIR / "sign_randomization_scores.parquet"


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


def _run(out_dir: Path, holdout_days: int) -> None:
    with tqdm(total=4, desc="Stage 10", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {POSITIONS_PATH}")
        positions = pl.read_parquet(POSITIONS_PATH)
        pbar.update()

        pbar.set_postfix_str("splitting train/test (same as stages 6-9)")
        train, test = _split_train_test(positions, holdout_days)
        pbar.update()

        pbar.set_postfix_str("computing train-window win rate per wallet")
        wallet_stats = (
            train.group_by("wallet")
            .agg([pl.len().alias("n_trades"), pl.col("win").mean().alias("win_rate")])
            .filter(pl.col("n_trades") >= MIN_TRADES_FILTER)
        )
        total_wins = as_float((wallet_stats["win_rate"] * wallet_stats["n_trades"]).sum())
        total_n = as_float(wallet_stats["n_trades"].sum())
        p_pop = total_wins / total_n if total_n else 0.5
        pbar.update()

        pbar.set_postfix_str("exact binomial sign-randomization test")
        n = wallet_stats["n_trades"].to_numpy()
        k = np.round(wallet_stats["win_rate"].to_numpy() * n).astype(int)
        p_values = np.array(
            [
                stats.binomtest(int(ki), int(ni), p_pop, alternative="greater").pvalue
                for ki, ni in zip(k, n, strict=True)
            ]
        )
        wallet_stats = wallet_stats.with_columns(
            [
                pl.Series("b7_p_value", p_values),
                pl.Series("b7_skilled_winner", p_values < _ALPHA),
                pl.Series("b7_score", -np.log10(np.clip(p_values, 1e-300, 1.0))),
            ]
        )
        pbar.update()

    future = _future_labels(test)
    result = wallet_stats.join(future, on="wallet", how="inner")
    result.write_parquet(SIGN_RANDOMIZATION_PATH)

    _print_box("B7 — SIGN-RANDOMIZATION SKILL CLASSIFIER")
    print(f"  Wallets tested:            {len(wallet_stats):,}")
    print(f"  Population base win rate:  {p_pop:.4f}")
    n_flagged = int(wallet_stats["b7_skilled_winner"].sum())
    pct_flagged = n_flagged / len(wallet_stats) * 100
    print(f"  Flagged 'skilled winners' (p<{_ALPHA}): {n_flagged:,} ({pct_flagged:.2f}%)")
    print("  Reference: Gomez-Cram et al. (2026) flag 3.14% on Polymarket.")
    print()
    print(f"  Wallets with future labels: {len(result):,}")
    print(f"  Saved -> {SIGN_RANDOMIZATION_PATH}")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(wallet_stats["b7_p_value"], bins=50)
    ax.axvline(_ALPHA, color="red", linestyle="--", label=f"alpha={_ALPHA}")
    ax.set_title("B7 sign-randomization p-value distribution")
    ax.set_xlabel("p-value")
    ax.set_ylabel("n wallets")
    ax.legend()
    save_fig(fig, out_dir, "sign_randomization_pvalues.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout-days", type=int, default=45)
    args = parser.parse_args()
    out_dir = get_output_dir("10_sign_randomization")
    with tee_stdout(out_dir):
        _run(out_dir, args.holdout_days)


if __name__ == "__main__":
    main()

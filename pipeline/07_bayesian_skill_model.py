"""
Stage 7: Fit the proposed Bayesian hierarchical skill model (research-proposal.md §3.2).

This is the first pipeline stage that implements the actual proposed method,
as opposed to stages 2/5/6 which explore point-estimate features. For each
skill dimension (buy = long_win_rate, sell = short_win_rate, timing =
overall_win_rate), an empirical-Bayes Normal-Normal hierarchical model
(src/skill_model/empirical_bayes.py) shrinks each wallet's raw estimate
toward the population mean in proportion to its sampling uncertainty
(1 / n_trades). This directly targets the problem documented in
pipeline/outputs/04_trade_sufficiency: most wallets have too few trades for
raw estimates to be trustworthy.

Uses the identical train/test split as pipeline/06_walkforward_validation.py
so the resulting posterior scores are evaluated on the same held-out future
window as the baselines in pipeline/08_baseline_comparison.py.

The three per-dimension posterior means are combined into a single
`bayes_score` by averaging their population z-scores (equal weighting is a
simplification — learning the combination weights is future work per
research-proposal.md §3.2's EV_copy formulation).

Input:  data/processed/positions.parquet
Output: data/processed/bayesian_scores.parquet
        pipeline/outputs/07_bayesian_skill_model/

Run:
    uv run python -m pipeline.07_bayesian_skill_model --holdout-days 45
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._numeric import as_int
from pipeline._paths import BAYES_SCORES_PATH, MIN_TRADES_FILTER, POSITIONS_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.features.skill_computer import SkillComputerService
from src.skill_model import EmpiricalBayesSkillService, SkillDimension

_MIN_TEST_TRADES = 5

_DIMENSIONS: list[tuple[SkillDimension, str, str]] = [
    (SkillDimension.BUY, "long_win_rate", "n_long_trades"),
    (SkillDimension.SELL, "short_win_rate", "n_short_trades"),
    (SkillDimension.TIMING, "overall_win_rate", "n_trades"),
]


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
        .filter(pl.col("n_future_trades") >= _MIN_TEST_TRADES)
    )


def _run(out_dir: Path, holdout_days: int) -> None:
    with tqdm(total=4, desc="Stage 7", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {POSITIONS_PATH}")
        positions = pl.read_parquet(POSITIONS_PATH)
        pbar.update()

        pbar.set_postfix_str("splitting train/test by close_ts (same as stage 6)")
        train, test = _split_train_test(positions, holdout_days)
        _print_box("BAYESIAN MODEL — TRAIN/TEST SPLIT")
        print(f"  Holdout window:     last {holdout_days} days")
        print(f"  Train positions:    {len(train):>12,}")
        print(f"  Test positions:     {len(test):>12,}")
        print()
        pbar.update()

        pbar.set_postfix_str("computing train-window raw skill estimates")
        features = SkillComputerService().compute(train).filter(
            pl.col("n_trades") >= MIN_TRADES_FILTER
        )
        pbar.update()

        pbar.set_postfix_str("fitting empirical-Bayes hierarchical model per dimension")
        service = EmpiricalBayesSkillService()
        posteriors: dict[str, pl.DataFrame] = {}
        for dimension, rate_col, n_col in _DIMENSIONS:
            posterior, hyper = service.fit_rate_dimension(
                features,
                dimension=dimension,
                wallet_col="wallet",
                rate_col=rate_col,
                n_col=n_col,
                min_trades=MIN_TRADES_FILTER,
            )
            posteriors[dimension.value] = posterior
            _print_box(f"DIMENSION: {dimension.value.upper()} ({rate_col})")
            print(f"  N wallets:        {hyper.n_wallets:>10,}")
            print(f"  mu (population):  {hyper.mu:>10.4f}")
            print(f"  tau2 (between-wallet variance): {hyper.tau2:>10.6f}")
            print(f"  Mean shrinkage toward prior:    {hyper.mean_shrinkage:>10.4f}")
            print()
        pbar.update()

    # ── Combine per-dimension posteriors into one score ──────────────────────
    # raw_estimate/n_trades per dimension are kept (not just posterior_mean) so
    # downstream null-hypothesis tests (stage 09/10) can reuse them without
    # recomputing SkillComputerService on the same train window.
    combined = None
    for dim, _, _ in _DIMENSIONS:
        p = posteriors[dim.value].select(
            [
                "wallet",
                pl.col("posterior_mean").alias(f"posterior_{dim.value}"),
                pl.col("raw_estimate").alias(f"raw_{dim.value}"),
                pl.col("n_trades").alias(f"n_trades_{dim.value}"),
            ]
        )
        combined = (
            p if combined is None else combined.join(p, on="wallet", how="full", coalesce=True)
        )
    assert combined is not None

    z_exprs = []
    for dim, _, _ in _DIMENSIONS:
        col = f"posterior_{dim.value}"
        mean_v = combined[col].mean()
        std_v = combined[col].std()
        if mean_v is None or std_v is None or std_v == 0:
            continue
        z_exprs.append(((pl.col(col) - mean_v) / std_v).alias(f"z_{dim.value}"))
    combined = combined.with_columns(z_exprs)
    z_cols = [f"z_{dim.value}" for dim, _, _ in _DIMENSIONS if f"z_{dim.value}" in combined.columns]
    combined = combined.with_columns(pl.mean_horizontal(z_cols).alias("bayes_score"))

    future = _future_labels(test)
    combined = combined.join(future, on="wallet", how="inner")
    combined.write_parquet(BAYES_SCORES_PATH)

    _print_box("COMBINED bayes_score (equal-weighted z-scores)")
    print(f"  Wallets with combined score + future labels: {len(combined):,}")
    print(f"  Saved -> {BAYES_SCORES_PATH}")
    print()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(combined["bayes_score"].drop_nulls(), bins=50)
    ax.set_title("Combined Bayesian skill score distribution")
    ax.set_xlabel("bayes_score (mean z-score across buy/sell/timing)")
    ax.set_ylabel("n wallets")
    save_fig(fig, out_dir, "bayes_score_distribution.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--holdout-days",
        type=int,
        default=45,
        help="n most recent days of closed positions held out as the future-performance test window",
    )
    args = parser.parse_args()
    out_dir = get_output_dir("07_bayesian_skill_model")
    with tee_stdout(out_dir):
        _run(out_dir, args.holdout_days)


if __name__ == "__main__":
    main()

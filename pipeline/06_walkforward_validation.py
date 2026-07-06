"""
Stage 6: Walk-forward validation — does the score predict FUTURE skill?

Problem with stage 5 (05_feature_analysis.py): it correlates features and
labels computed from the *same* historical window, so a wallet's past PnL
trivially correlates with itself. That is not evidence of skill, just of
recording the same thing twice.

This stage holds out the last `--holdout-days` of closed positions as an
out-of-sample test window:
  - TRAIN window (before cutoff): compute wallet features via
    SkillComputerService — same proposed features as stage 5, plus three
    "naive" baselines (total_pnl, avg_roi, overall_win_rate) computed on the
    identical train window so the comparison is apples-to-apples.
  - TEST window (after cutoff): realized win rate / PnL per wallet — the
    ground truth the features must predict, never seen during training.

Only wallets with >= MIN_TRADES_FILTER trades in both windows are scored.

Input:  data/processed/positions.parquet
Output: pipeline/outputs/06_walkforward_validation/

Run:
    uv run python -m pipeline.06_walkforward_validation --holdout-days 45
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._paths import MIN_TRADES_FILTER, POSITIONS_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.features.skill_computer import SkillComputerService

_MIN_TEST_TRADES = 5

_PROPOSED_FEATURES = [
    "long_win_rate",
    "short_win_rate",
    "side_asymmetry",
    "overall_win_rate",
    "avg_roi",
    "total_pnl",
    "leverage_adj_roi",
    "mean_leverage",
    "sizing_skill",
    "liquidation_rate",
    "n_trades",
    "trade_frequency_per_day",
]

_NAIVE_BASELINES = ["total_pnl", "avg_roi", "overall_win_rate"]


def _pearson(df: pl.DataFrame, col_a: str, col_b: str) -> float:
    sub = df.select([col_a, col_b]).drop_nulls()
    if len(sub) < 5:
        return float("nan")
    return pl.corr(sub[col_a], sub[col_b], eager=True).item() or 0.0


def _print_box(title: str) -> None:
    width = 60
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _run(out_dir: Path, holdout_days: int) -> None:
    with tqdm(total=4, desc="Stage 6", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {POSITIONS_PATH}")
        positions = pl.read_parquet(POSITIONS_PATH)
        pbar.update()

        pbar.set_postfix_str("splitting train/test by close_ts")
        max_ts = positions["close_ts"].max()
        cutoff_ts = max_ts - holdout_days * 86400
        train = positions.filter(pl.col("close_ts") < cutoff_ts)
        test = positions.filter(pl.col("close_ts") >= cutoff_ts)
        _print_box("WALK-FORWARD SPLIT")
        print(f"  Holdout window:     last {holdout_days} days")
        print(f"  Train positions:    {len(train):>12,}")
        print(f"  Test positions:     {len(test):>12,}")
        print()
        pbar.update()

        pbar.set_postfix_str("computing train-window features")
        features = SkillComputerService().compute(train).filter(
            pl.col("n_trades") >= MIN_TRADES_FILTER
        )
        pbar.update()

        pbar.set_postfix_str("computing test-window (future) labels")
        future_labels = (
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
        pbar.update()

    df = features.join(future_labels, on="wallet", how="inner")
    print(f"Wallets scored (>= {MIN_TRADES_FILTER} train trades, "
          f">= {_MIN_TEST_TRADES} future trades): {len(df):,}")
    print()

    # ── Out-of-sample correlations ──────────────────────────────────────────
    _print_box("PROPOSED FEATURES × FUTURE PERFORMANCE (out-of-sample)")
    print(f"  {'Feature':<26} {'vs future_WR':>14} {'vs future_PnL':>14}")
    print("  " + "-" * 56)
    feat_names: list[str] = []
    r_wrs: list[float] = []
    r_pnls: list[float] = []
    for feat in tqdm(_PROPOSED_FEATURES, desc="proposed features", leave=False, dynamic_ncols=True):
        if feat not in df.columns:
            continue
        r_wr = _pearson(df, feat, "future_win_rate")
        r_pnl = _pearson(df, feat, "future_pnl")
        feat_names.append(feat)
        r_wrs.append(r_wr)
        r_pnls.append(r_pnl)
        tag = " (naive baseline)" if feat in _NAIVE_BASELINES else ""
        print(f"  {feat:<26} {r_wr:>+14.3f} {r_pnl:>+14.3f}{tag}")
    print()

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["tab:orange" if f in _NAIVE_BASELINES else "tab:blue" for f in feat_names]
    ax.barh(feat_names, r_wrs, color=colors)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Out-of-sample: train-window feature × future win rate")
    ax.set_xlabel("Pearson r  (orange = naive baseline)")
    save_fig(fig, out_dir, "walkforward_correlations.png")

    # ── Scatter for the single best proposed (non-baseline) feature ────────
    non_baseline = [
        (f, r) for f, r in zip(feat_names, r_wrs) if f not in _NAIVE_BASELINES
    ]
    if non_baseline:
        best_feat, best_r = max(non_baseline, key=lambda t: abs(t[1]))
        sub = df.select([best_feat, "future_win_rate"]).drop_nulls()
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(sub[best_feat], sub["future_win_rate"], s=8, alpha=0.3)
        ax.set_title(f"{best_feat} vs future win rate (r={best_r:+.3f})")
        ax.set_xlabel(best_feat)
        ax.set_ylabel("future_win_rate")
        save_fig(fig, out_dir, "best_feature_scatter.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--holdout-days", type=int, default=45,
        help="n most recent days of closed positions held out as the future-performance test window",
    )
    args = parser.parse_args()
    out_dir = get_output_dir("06_walkforward_validation")
    with tee_stdout(out_dir):
        _run(out_dir, args.holdout_days)


if __name__ == "__main__":
    main()

"""
Stage 15: Rolling walk-forward validation with per-fold error bars.

Stages 6-14 all rest on a SINGLE 45-day holdout, so every out-of-sample number
is one draw from one market regime. This stage replaces that single split with a
rolling walk-forward: an expanding train window and K consecutive, non-overlapping
45-day test windows. Each fold independently recomputes the empirical-Bayes
posteriors on its own train window (no leakage across the cutoff) and evaluates
every score against that fold's future labels. Reporting mean +/- std across folds
turns the single-fold point estimates of Stage 14 into interval estimates and
tests regime sensitivity (research-proposal NS6).

For each fold and each score we report Spearman rank correlation vs future win
rate, restricted to wallets with >= MIN_FUTURE_TRADES trades in that fold's test
window (so the label is not pure sampling noise; see Stage 14 reliability). The
learned LambdaMART ranker is re-fit and cross-validated within each fold.

Input:  data/processed/positions.parquet
        data/processed/baselines.parquet  (b3_roi, full-history reference)
Output: data/processed/rolling_walkforward.parquet
        pipeline/outputs/15_rolling_walkforward/

Run:
    uv run python pipeline/15_rolling_walkforward.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel

from pipeline._numeric import as_int
from pipeline._paths import (
    BASELINES_PATH,
    MIN_TRADES_FILTER,
    POSITIONS_PATH,
    PROCESSED_DIR,
)
from pipeline._ranking import (
    cv_learned_ranker,
    grade_labels,
    label_reliability,
    spearman,
)
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.features.skill_computer import SkillComputerService
from src.skill_model import EmpiricalBayesSkillService, SkillDimension

ROLLING_PATH = PROCESSED_DIR / "rolling_walkforward.parquet"

_HOLDOUT_DAYS = 45
_N_FOLDS = 5
_MIN_FUTURE_TRADES = 10
_TOP_K_FRAC = 0.10

# Scores evaluated per fold. Each is a train-window posterior except b3_roi
# (full-history reference baseline) and learned_ranker (re-fit per fold).
_SCORES = [
    "learned_ranker",
    "posterior_liquidation",
    "posterior_timing",
    "posterior_sell",
    "bayes_score",
    "b3_roi",
]

_RANKER_FEATURES = [
    "posterior_buy",
    "posterior_sell",
    "posterior_timing",
    "posterior_sizing",
    "posterior_liquidation",
    "raw_sizing",
    "n_trades",
]

_RATE_DIMS: list[tuple[SkillDimension, str, str]] = [
    (SkillDimension.BUY, "long_win_rate", "n_long_trades"),
    (SkillDimension.SELL, "short_win_rate", "n_short_trades"),
    (SkillDimension.TIMING, "overall_win_rate", "n_trades"),
    (SkillDimension.LIQUIDATION, "survival_rate", "n_trades"),
]


class FoldResult(BaseModel):
    """One walk-forward fold: population, label reliability, per-score Spearman."""

    fold: int
    test_start_ts: int
    n_wallets: int
    reliability: float
    scores: dict[str, float]


def _print_box(title: str) -> None:
    width = 66
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _score_train_window(train: pl.DataFrame) -> pl.DataFrame:
    """Recompute empirical-Bayes posteriors + bayes_score on one train window."""
    features = (
        SkillComputerService()
        .compute(train)
        .filter(pl.col("n_trades") >= MIN_TRADES_FILTER)
        .with_columns((1.0 - pl.col("liquidation_rate")).alias("survival_rate"))
    )
    service = EmpiricalBayesSkillService()
    combined: pl.DataFrame | None = None
    for dimension, rate_col, n_col in _RATE_DIMS:
        posterior, _ = service.fit_rate_dimension(
            features,
            dimension=dimension,
            wallet_col="wallet",
            rate_col=rate_col,
            n_col=n_col,
            min_trades=MIN_TRADES_FILTER,
        )
        p = posterior.select(
            ["wallet", pl.col("posterior_mean").alias(f"posterior_{dimension.value}")]
        )
        combined = p if combined is None else combined.join(p, on="wallet", how="full", coalesce=True)

    sizing, _ = service.fit_continuous_dimension(
        features,
        dimension=SkillDimension.SIZING,
        wallet_col="wallet",
        estimate_col="log_wl_ratio",
        sigma2_col="sigma2_log_wl",
        n_col="n_trades",
        min_trades=MIN_TRADES_FILTER,
    )
    s = sizing.select(
        [
            "wallet",
            pl.col("posterior_mean").alias("posterior_sizing"),
            pl.col("raw_estimate").alias("raw_sizing"),
        ]
    )
    assert combined is not None
    combined = combined.join(s, on="wallet", how="full", coalesce=True)
    combined = combined.join(
        features.select(["wallet", "n_trades"]), on="wallet", how="left"
    )

    # bayes_score = equal-weighted z-average of buy/sell/timing/sizing posteriors.
    z_cols: list[str] = []
    for key in ("buy", "sell", "timing", "sizing"):
        col = f"posterior_{key}"
        mean_v, std_v = combined[col].mean(), combined[col].std()
        if mean_v is None or std_v is None or std_v == 0:
            continue
        combined = combined.with_columns(((pl.col(col) - mean_v) / std_v).alias(f"z_{key}"))
        z_cols.append(f"z_{key}")
    combined = combined.with_columns(pl.mean_horizontal(z_cols).alias("bayes_score"))
    return combined


def _future_labels(test: pl.DataFrame) -> pl.DataFrame:
    return (
        test.group_by("wallet")
        .agg(
            [
                pl.len().alias("n_future_trades"),
                pl.col("win").mean().alias("future_win_rate"),
            ]
        )
        .filter(pl.col("n_future_trades") >= _MIN_FUTURE_TRADES)
    )


def _eval_fold(
    fold: int,
    train: pl.DataFrame,
    test: pl.DataFrame,
    baselines: pl.DataFrame,
    test_start_ts: int,
) -> FoldResult | None:
    scored = _score_train_window(train)
    future = _future_labels(test)
    df = (
        scored.join(future, on="wallet", how="inner")
        .join(baselines, on="wallet", how="left")
        .drop_nulls(subset=_RANKER_FEATURES + ["future_win_rate"])
    )
    if df.height < 50:
        print(f"  Fold {fold}: n={df.height} (too few after filtering, skipped)\n")
        return None

    future_wr = df["future_win_rate"].to_numpy()
    n_future = df["n_future_trades"].to_numpy().astype(np.float64)
    rho = label_reliability(future_wr, n_future)

    relevance = grade_labels(future_wr)
    features = df.select(_RANKER_FEATURES).to_numpy()
    k = max(int(df.height * _TOP_K_FRAC), 1)
    oos_pred, _, _ = cv_learned_ranker(features, future_wr, relevance, k)

    scores: dict[str, float] = {}
    scores["learned_ranker"] = spearman(oos_pred, future_wr)
    for name in _SCORES:
        if name == "learned_ranker":
            continue
        if name not in df.columns:
            scores[name] = 0.0
            continue
        scores[name] = spearman(df[name].to_numpy(), future_wr, omit=True)
    return FoldResult(
        fold=fold,
        test_start_ts=test_start_ts,
        n_wallets=df.height,
        reliability=round(rho, 4),
        scores={key: round(val, 4) for key, val in scores.items()},
    )


def _run(out_dir: Path) -> None:
    positions = pl.read_parquet(POSITIONS_PATH)
    baselines = (
        pl.read_parquet(BASELINES_PATH)
        .select(["wallet", "b3_roi"])
        .unique(subset=["wallet"], keep="first")
    )
    max_ts = as_int(positions["close_ts"].max())
    window = _HOLDOUT_DAYS * 86400

    _print_box("ROLLING WALK-FORWARD VALIDATION")
    print(f"  {_N_FOLDS} folds, expanding train, non-overlapping {_HOLDOUT_DAYS}-day test windows")
    print(f"  Eval population: wallets with >= {_MIN_FUTURE_TRADES} future trades per fold")
    print()

    results: list[FoldResult] = []
    # Fold f (f=0 most recent) tests [max_ts - (f+1)*window, max_ts - f*window).
    for fold in range(_N_FOLDS):
        test_end = max_ts - fold * window
        test_start = test_end - window
        train = positions.filter(pl.col("close_ts") < test_start)
        test = positions.filter(
            (pl.col("close_ts") >= test_start) & (pl.col("close_ts") < test_end)
        )
        res = _eval_fold(fold, train, test, baselines, test_start)
        if res is None:
            continue
        results.append(res)
        line = "  ".join(f"{name}={res.scores.get(name, 0.0):+.3f}" for name in _SCORES)
        print(f"  Fold {fold} (n={res.n_wallets:>4}, rho={res.reliability:.3f}): {line}")
    print()

    _report_aggregate(results, out_dir)


def _report_aggregate(results: list[FoldResult], out_dir: Path) -> None:
    if not results:
        print("  No valid folds.")
        return
    _print_box(f"AGGREGATE ACROSS {len(results)} FOLDS  (Spearman vs future WR, mean +/- std)")
    agg: dict[str, tuple[float, float]] = {}
    for name in _SCORES:
        vals = np.array([r.scores.get(name, 0.0) for r in results], dtype=np.float64)
        agg[name] = (float(vals.mean()), float(vals.std()))
        print(f"  {name:<24} {vals.mean():+.3f} ± {vals.std():.3f}")
    print()
    mean_rho = float(np.mean([r.reliability for r in results]))
    print(f"  Mean label reliability across folds: rho={mean_rho:.3f}")
    print()

    rows = [
        {"fold": r.fold, "test_start_ts": r.test_start_ts, "n_wallets": r.n_wallets,
         "reliability": r.reliability, **r.scores}
        for r in results
    ]
    pl.DataFrame(rows).write_parquet(ROLLING_PATH)
    print(f"  Saved per-fold results -> {ROLLING_PATH}")

    _plot(results, agg, out_dir)


def _plot(
    results: list[FoldResult],
    agg: dict[str, tuple[float, float]],
    out_dir: Path,
) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))
    folds = [r.fold for r in results]
    for name in _SCORES:
        ax1.plot(folds, [r.scores.get(name, 0.0) for r in results], "o-", label=name)
    ax1.set_xlabel("fold (0 = most recent test window)")
    ax1.set_ylabel("Spearman vs future WR")
    ax1.set_title(f"Per-fold stability (>= {_MIN_FUTURE_TRADES} future trades)")
    ax1.axhline(0.0, color="black", lw=0.8)
    ax1.set_xticks(folds)
    ax1.legend(fontsize=8)

    names = list(_SCORES)
    means = [agg[n][0] for n in names]
    stds = [agg[n][1] for n in names]
    y = np.arange(len(names))
    ax2.barh(y, means, xerr=stds, capsize=4, color="steelblue")
    ax2.set_yticks(y, names)
    ax2.invert_yaxis()
    ax2.set_xlabel("mean Spearman ± std across folds")
    ax2.set_title("Walk-forward aggregate")
    ax2.axvline(0.0, color="black", lw=0.8)
    save_fig(fig, out_dir, "rolling_walkforward.png")


def main() -> None:
    out_dir = get_output_dir("15_rolling_walkforward")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

"""
Stage 14: Learned composite ranker (LambdaMART) with reliability-aware evaluation.

Motivation (see docs/eda-report.tex Discussion): the equal-weighted `bayes_score`
and the multiplicative `van_loon_score` both *underperform* their best single
dimension, because a naive combination folds in the sign-flipped `posterior_sizing`
(out-of-sample r_s < 0). This stage replaces the hand-specified combination with a
LightGBM LambdaMART ranker that *learns* how to weight the five train-window
posteriors to rank wallets by future performance.

Two things this stage does that the earlier stages did not:

  1. LEARNED COMBINATION (research-proposal NS3). LGBMRanker optimises NDCG
     directly over the wallet list, so it can down-weight or drop the noisy
     sizing dimension automatically rather than averaging it in.

  2. RELIABILITY-AWARE EVALUATION. The future_win_rate label is dominated by
     binomial sampling noise on wallets with few future trades. We report the
     label *reliability* rho = 1 - E[p(1-p)/n_future] / Var(future_win_rate)
     at each min-future-trade threshold, so a Spearman/NDCG number is never read
     without the ceiling that label noise imposes on it. On this data rho jumps
     from ~0.01 (>=5 future trades) to ~0.66 (>=20), so the ranker is evaluated
     across thresholds, not on the noise-dominated >=5 population alone.

Input:  data/processed/bayesian_scores.parquet  (train-window posteriors + labels)
        data/processed/baselines.parquet         (b3_roi, full-history baseline)
Output: data/processed/learned_ranker_scores.parquet
        pipeline/outputs/14_learned_ranker/

Run:
    uv run python pipeline/14_learned_ranker.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel

from pipeline._paths import BASELINES_PATH, BAYES_SCORES_PATH, PROCESSED_DIR
from pipeline._ranking import (
    cv_learned_ranker,
    grade_labels,
    label_reliability,
    spearman,
)
from pipeline._report import get_output_dir, save_fig, tee_stdout

RANKER_SCORES_PATH = PROCESSED_DIR / "learned_ranker_scores.parquet"


class RankerRegimeResult(BaseModel):
    """Learned-ranker vs baseline results at one min-future-trade threshold."""

    min_future_trades: int
    n_wallets: int
    reliability: float
    learned_ranker_rs: float
    learned_ranker_ndcg: float
    b3_roi_rs: float
    posterior_liquidation_rs: float
    bayes_score_rs: float

# Train-window posteriors used as ranker features (all leakage-free: computed on
# the pre-holdout window only). n_trades_timing is the breadth term.
_FEATURE_COLS = [
    "posterior_buy",
    "posterior_sell",
    "posterior_timing",
    "posterior_sizing",
    "posterior_liquidation",
    "raw_sizing",
    "n_trades_timing",
]

_FUTURE_TRADE_THRESHOLDS = [5, 10, 20]
_TOP_K_FRAC = 0.10


def _print_box(title: str) -> None:
    width = 66
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _run(out_dir: Path) -> None:
    bayes = pl.read_parquet(BAYES_SCORES_PATH)
    # baselines.parquet has ~4k duplicate wallet keys; dedupe before joining or the
    # left join inflates the population (1,230 -> 1,347). unique(keep=first) is a
    # read-only local guard — the upstream duplication should also be fixed in
    # stage 04, and stages 08/13 inherit the same inflation.
    baselines = (
        pl.read_parquet(BASELINES_PATH)
        .select(["wallet", "b3_roi"])
        .unique(subset=["wallet"], keep="first")
    )
    df = bayes.join(baselines, on="wallet", how="left")

    _print_box("LEARNED RANKER (LambdaMART) — RELIABILITY-AWARE EVALUATION")
    print(f"  Wallets with posteriors + future labels: {df.height:,}")
    print(f"  Features: {', '.join(_FEATURE_COLS)}")
    print(f"  5-fold CV, NDCG@{int(_TOP_K_FRAC * 100)}%, seed=42")
    print()

    summary_rows: list[RankerRegimeResult] = []
    best_oos: NDArray[np.float64] | None = None
    best_wallets: pl.Series | None = None

    for thr in _FUTURE_TRADE_THRESHOLDS:
        sub = df.filter(
            pl.col("n_future_trades") >= thr
        ).drop_nulls(subset=_FEATURE_COLS + ["future_win_rate"])
        if sub.height < 50:
            print(f"  >= {thr} future trades: n={sub.height} (too few, skipped)\n")
            continue

        future_wr = sub["future_win_rate"].to_numpy()
        n_future = sub["n_future_trades"].to_numpy().astype(np.float64)
        rho = label_reliability(future_wr, n_future)
        relevance = grade_labels(future_wr)
        features = sub.select(_FEATURE_COLS).to_numpy()
        k = max(int(sub.height * _TOP_K_FRAC), 1)

        oos_pred, fold_ndcg, fold_spearman = cv_learned_ranker(
            features, future_wr, relevance, k
        )

        # Baselines evaluated on the same population (whole-population rank).
        base_rs: dict[str, float] = {}
        for name in ("b3_roi", "posterior_liquidation", "bayes_score"):
            base_rs[name] = spearman(sub[name].to_numpy(), future_wr, omit=True)

        learned_rs = spearman(oos_pred, future_wr)
        ndcg_mean, ndcg_std = float(np.mean(fold_ndcg)), float(np.std(fold_ndcg))
        rs_mean, rs_std = float(np.mean(fold_spearman)), float(np.std(fold_spearman))

        _print_box(f"MIN {thr} FUTURE TRADES  (n={sub.height:,}, label reliability rho={rho:.3f})")
        learned_line = (
            f"  learned_ranker   Spearman(OOS)={learned_rs:+.3f}   "
            f"CV Spearman={rs_mean:+.3f}±{rs_std:.3f}   NDCG@{k}={ndcg_mean:.3f}±{ndcg_std:.3f}"
        )
        print(learned_line)
        print(f"  b3_roi                 Spearman={base_rs['b3_roi']:+.3f}   (full-history baseline)")
        print(f"  posterior_liquidation  Spearman={base_rs['posterior_liquidation']:+.3f}")
        print(f"  bayes_score            Spearman={base_rs['bayes_score']:+.3f}   (equal-weight composite)")
        if rho < 0.05:
            print("  NOTE: rho<0.05 — label is ~pure luck here; no score can rank this population.")
        print()

        summary_rows.append(RankerRegimeResult(
            min_future_trades=thr,
            n_wallets=sub.height,
            reliability=round(rho, 4),
            learned_ranker_rs=round(learned_rs, 4),
            learned_ranker_ndcg=round(ndcg_mean, 4),
            b3_roi_rs=round(base_rs["b3_roi"], 4),
            posterior_liquidation_rs=round(base_rs["posterior_liquidation"], 4),
            bayes_score_rs=round(base_rs["bayes_score"], 4),
        ))

        if thr == _FUTURE_TRADE_THRESHOLDS[0]:
            best_oos = oos_pred
            best_wallets = sub["wallet"]

    if best_oos is not None and best_wallets is not None:
        pl.DataFrame({"wallet": best_wallets, "learned_ranker_score": best_oos}).write_parquet(
            RANKER_SCORES_PATH
        )
        print(f"  Saved OOS ranker scores (>= {_FUTURE_TRADE_THRESHOLDS[0]} pop) -> {RANKER_SCORES_PATH}\n")

    _plot_summary(summary_rows, out_dir)


def _plot_summary(rows: list[RankerRegimeResult], out_dir: Path) -> None:
    if not rows:
        return
    thr = [r.min_future_trades for r in rows]
    rho = [r.reliability for r in rows]
    learned = [r.learned_ranker_rs for r in rows]
    roi = [r.b3_roi_rs for r in rows]
    liq = [r.posterior_liquidation_rs for r in rows]
    bayes = [r.bayes_score_rs for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    x = np.arange(len(thr))
    ax1.plot(x, rho, "o-", color="black")
    ax1.set_xticks(x, [str(t) for t in thr])
    ax1.set_xlabel("min future trades")
    ax1.set_ylabel("label reliability  ρ")
    ax1.set_title("Future-win-rate label reliability")
    ax1.axhline(0.05, ls="--", color="red", lw=1, label="ρ=0.05 (≈pure luck)")
    ax1.legend()

    w = 0.2
    ax2.bar(x - 1.5 * w, learned, w, label="learned_ranker")
    ax2.bar(x - 0.5 * w, roi, w, label="b3_roi")
    ax2.bar(x + 0.5 * w, liq, w, label="posterior_liquidation")
    ax2.bar(x + 1.5 * w, bayes, w, label="bayes_score")
    ax2.set_xticks(x, [str(t) for t in thr])
    ax2.set_xlabel("min future trades")
    ax2.set_ylabel("Spearman vs future WR")
    ax2.set_title("Ranker vs baselines by reliability regime")
    ax2.axhline(0.0, color="black", lw=0.8)
    ax2.legend()
    save_fig(fig, out_dir, "learned_ranker_by_reliability.png")


def main() -> None:
    out_dir = get_output_dir("14_learned_ranker")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

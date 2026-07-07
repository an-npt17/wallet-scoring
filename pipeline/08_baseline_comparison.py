"""
Stage 8: Compare the proposed Bayesian score against baselines B1-B5 (RQ4).

This is the first stage that answers "does the proposed method beat the
baselines" (research-proposal.md §5.2/§5.3, RQ4) rather than just exploring
raw feature correlations (stage 5/6). Two metrics, both out-of-sample
(train-window score vs. held-out future-window ground truth, identical split
to stage 6/7):

  - Spearman rank correlation vs. future_win_rate / future_pnl.
  - Top-decile hit rate: of wallets ranked in the top decile by a given
    score, what fraction land above the population MEDIAN future_win_rate?
    (A proxy for "top-decile wallets by proposed score outperform the
    market", proposal §5.2.)

Baselines compared:
  B1 (existing composite)  — daily_trader_rankings score. KNOWN BROKEN:
                              only the top-20 wallets/snapshot have non-null
                              coverage (see docs/eda-report.tex, "Data-Quality
                              Note"), so this comparison is not a fair
                              full-population baseline and results should be
                              read with that caveat, not as a real B1 defeat.
  B2 (raw PnL), B3 (raw ROI), B4 (win rate), B5 (Sharpe) — computed on the
                              FULL account history (not train-window-only),
                              so they have a slight information advantage
                              over train-window-only scores; noted in output.
  B6 (zScore, arXiv:2507.20494) — NOT implemented; not included below.

Input:  data/processed/bayesian_scores.parquet (stage 7)
        data/processed/baselines.parquet (stage 4)
Output: pipeline/outputs/08_baseline_comparison/

Run:
    uv run python -m pipeline.08_baseline_comparison
"""

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._paths import BASELINES_PATH, BAYES_SCORES_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout

_SCORE_COLS = [
    "bayes_score",
    "posterior_buy",
    "posterior_sell",
    "posterior_timing",
    "b1_composite",
    "b2_pnl",
    "b3_roi",
    "b4_win_rate",
    "b5_sharpe",
]

_KNOWN_LIMITED = {"b1_composite": "only top-20 wallets/snapshot have coverage"}


def _print_box(title: str) -> None:
    width = 64
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _spearman(df: pl.DataFrame, col_a: str, col_b: str) -> float:
    sub = df.select([col_a, col_b]).drop_nulls()
    if len(sub) < 5:
        return float("nan")
    ranked = sub.select(
        [pl.col(col_a).rank().alias("ra"), pl.col(col_b).rank().alias("rb")]
    )
    return pl.corr(ranked["ra"], ranked["rb"], eager=True).item() or 0.0


def _top_decile_hit_rate(df: pl.DataFrame, score_col: str, label_col: str) -> tuple[float, int]:
    sub = df.select([score_col, label_col]).drop_nulls()
    n = len(sub)
    if n < 10:
        return float("nan"), n
    threshold = sub[score_col].quantile(0.9)
    median_label = sub[label_col].median()
    top_decile = sub.filter(pl.col(score_col) >= threshold)
    if len(top_decile) == 0:
        return float("nan"), n
    hit_rate = (top_decile[label_col] > median_label).mean()
    return float(hit_rate or 0.0), n


def _run(out_dir: Path) -> None:
    with tqdm(total=2, desc="Stage 8", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {BAYES_SCORES_PATH}")
        scores = pl.read_parquet(BAYES_SCORES_PATH)
        pbar.update()

        pbar.set_postfix_str(f"loading {BASELINES_PATH}")
        baselines = pl.read_parquet(BASELINES_PATH)
        df = scores.join(baselines, on="wallet", how="left")
        pbar.update()

    _print_box("B1-B5 BASELINE COMPARISON (out-of-sample, RQ4)")
    print(f"  Wallets with future labels: {len(df):,}")
    print()

    _print_box("SPEARMAN RANK CORRELATION vs FUTURE PERFORMANCE")
    print(f"  {'Score':<20} {'vs future_WR':>14} {'vs future_PnL':>14}  Note")
    print("  " + "-" * 70)
    names: list[str] = []
    rho_wrs: list[float] = []
    for col in tqdm(_SCORE_COLS, desc="scores", leave=False, dynamic_ncols=True):
        if col not in df.columns:
            continue
        rho_wr = _spearman(df, col, "future_win_rate")
        rho_pnl = _spearman(df, col, "future_pnl")
        names.append(col)
        rho_wrs.append(rho_wr)
        note = _KNOWN_LIMITED.get(col, "")
        print(f"  {col:<20} {rho_wr:>+14.3f} {rho_pnl:>+14.3f}  {note}")
    print()

    _print_box("TOP-DECILE HIT RATE (% above population median future_WR)")
    print(f"  {'Score':<20} {'Hit rate':>10} {'N wallets':>12}")
    print("  " + "-" * 46)
    hit_names: list[str] = []
    hit_rates: list[float] = []
    for col in _SCORE_COLS:
        if col not in df.columns:
            continue
        hit_rate, n = _top_decile_hit_rate(df, col, "future_win_rate")
        hit_names.append(col)
        hit_rates.append(hit_rate)
        print(f"  {col:<20} {hit_rate:>9.1%} {n:>12,}")
    print()

    print("  B6 (zScore, arXiv:2507.20494) — NOT implemented, excluded from this comparison.")
    print("  B2-B5 use full account history; bayes_score/posterior_* use train-window only")
    print("  (a slight information disadvantage for the proposed method in this comparison).")
    print()

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(names, rho_wrs)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Spearman rho vs future_win_rate: proposed score vs baselines")
    ax.set_xlabel("Spearman rho")
    save_fig(fig, out_dir, "score_comparison_spearman.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(hit_names, hit_rates)
    ax.axvline(0.5, color="black", linewidth=1, linestyle="--")
    ax.set_title("Top-decile hit rate: proposed score vs baselines")
    ax.set_xlabel("fraction of top-decile wallets above median future_WR")
    save_fig(fig, out_dir, "score_comparison_hit_rate.png")


def main() -> None:
    out_dir = get_output_dir("08_baseline_comparison")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

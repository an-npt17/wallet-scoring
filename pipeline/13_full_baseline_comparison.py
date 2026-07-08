"""
Stage 13: Full baseline comparison — bayes_score vs B1-B8, with B8 as a robustness filter.

Consolidates every score built across stages 4, 7, 10, 12 into one
out-of-sample comparison table (research-proposal.md sec 5.2/5.3, RQ4):

  bayes_score        — stage 7, the proposed Bayesian hierarchical score
  B1 composite       — stage 4 (KNOWN limited: only 20-wallet coverage)
  B2 raw PnL         — stage 4 (full account history)
  B3 raw ROI         — stage 4 (full account history)
  B4 win rate        — stage 4 (full account history)
  B5 Sharpe          — stage 4 (full account history)
  B6 zScore reimpl.  — stage 12 (train-window only, rule-based)
  B7 sign-randomiz.  — stage 10 (train-window only)

B8 (stage 11) is not a ranking score — it is applied as a filter: the
comparison is run twice, with and without wash-trade-flagged wallets
excluded, to check whether any baseline's apparent performance depends on
wallets that look like bots rather than genuine traders.

Input:  data/processed/bayesian_scores.parquet, baselines.parquet,
        zscore_baseline.parquet, sign_randomization_scores.parquet,
        wash_trade_flags.parquet
Output: pipeline/outputs/13_full_baseline_comparison/

Run:
    uv run python -m pipeline.13_full_baseline_comparison
"""

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._numeric import as_float
from pipeline._paths import BASELINES_PATH, BAYES_SCORES_PATH, PROCESSED_DIR
from pipeline._report import get_output_dir, save_fig, tee_stdout

ZSCORE_BASELINE_PATH = PROCESSED_DIR / "zscore_baseline.parquet"
SIGN_RANDOMIZATION_PATH = PROCESSED_DIR / "sign_randomization_scores.parquet"
WASH_TRADE_FLAGS_PATH = PROCESSED_DIR / "wash_trade_flags.parquet"

_SCORE_COLS = [
    "van_loon_score",
    "bayes_score",
    "b1_composite",
    "b2_pnl",
    "b3_roi",
    "b4_win_rate",
    "b5_sharpe",
    "b6_zscore",
    "b7_score",
]

_KNOWN_LIMITED = {"b1_composite": "only top-20 wallets/snapshot have coverage"}


def _print_box(title: str) -> None:
    width = 66
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
    return as_float(hit_rate), n


def _print_comparison(df: pl.DataFrame, title: str) -> list[float]:
    _print_box(title)
    print(f"  Wallets in this comparison: {len(df):,}")
    print()
    print(f"  {'Score':<16} {'Spearman WR':>12} {'Spearman PnL':>13} {'Hit rate':>10}  Note")
    print("  " + "-" * 74)
    rho_wrs: list[float] = []
    for col in _SCORE_COLS:
        if col not in df.columns:
            continue
        rho_wr = _spearman(df, col, "future_win_rate")
        rho_pnl = _spearman(df, col, "future_pnl")
        hit_rate, _ = _top_decile_hit_rate(df, col, "future_win_rate")
        note = _KNOWN_LIMITED.get(col, "")
        print(f"  {col:<16} {rho_wr:>+12.3f} {rho_pnl:>+13.3f} {hit_rate:>9.1%}  {note}")
        rho_wrs.append(rho_wr)
    print()
    return rho_wrs


def _run(out_dir: Path) -> None:
    with tqdm(total=5, desc="Stage 13", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str("loading all score parquets")
        bayes = pl.read_parquet(BAYES_SCORES_PATH).select(
            ["wallet", "bayes_score", "van_loon_score", "future_win_rate", "future_pnl"]
        )
        pbar.update()
        baselines = pl.read_parquet(BASELINES_PATH).select(
            ["wallet", "b1_composite", "b2_pnl", "b3_roi", "b4_win_rate", "b5_sharpe"]
        )
        pbar.update()
        zscore = pl.read_parquet(ZSCORE_BASELINE_PATH).select(["wallet", "b6_zscore"])
        pbar.update()
        sign_rand = pl.read_parquet(SIGN_RANDOMIZATION_PATH).select(["wallet", "b7_score"])
        pbar.update()
        wash_flags = pl.read_parquet(WASH_TRADE_FLAGS_PATH).select(["wallet", "b8_wash_flag"])
        pbar.update()

    df = (
        bayes.join(baselines, on="wallet", how="left")
        .join(zscore, on="wallet", how="left")
        .join(sign_rand, on="wallet", how="left")
        .join(wash_flags, on="wallet", how="left")
    )

    all_rhos = _print_comparison(df, "FULL COMPARISON (all wallets, RQ4)")

    clean = df.filter(~pl.col("b8_wash_flag").fill_null(False))
    n_excluded = len(df) - len(clean)
    print(f"  B8 excludes {n_excluded:,} wallets flagged as likely wash/bot traders.")
    print()
    clean_rhos = _print_comparison(clean, "ROBUSTNESS CHECK (B8 wash-trade-flagged wallets excluded)")

    print("  B6/B7 are computed on the train window only (like bayes_score); B2-B5 use full")
    print("  account history (a slight information advantage). B1 coverage is 20 wallets —")
    print("  read with that caveat, not as a fair full-population baseline.")

    fig, ax = plt.subplots(figsize=(9, 6))
    x = range(len(_SCORE_COLS))
    width = 0.35
    ax.bar([i - width / 2 for i in x], all_rhos, width, label="all wallets")
    ax.bar([i + width / 2 for i in x], clean_rhos, width, label="B8-filtered")
    ax.set_xticks(list(x), _SCORE_COLS, rotation=30, ha="right")
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Spearman rho vs future_win_rate: all scores, with/without B8 filter")
    ax.set_ylabel("Spearman rho")
    ax.legend()
    save_fig(fig, out_dir, "full_comparison.png")


def main() -> None:
    out_dir = get_output_dir("13_full_baseline_comparison")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

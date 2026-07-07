"""
Stage 9: Luck-vs-skill validity check (Kosowski et al. 2006 / Papaioannou et al. 2024).

Neither pipeline 07 (Bayesian model) nor 08 (baseline comparison) actually asks
"is the top-decile bayes_score wallet distinguishable from a chance trader?"
They only rank wallets against each other and against B1-B5. This stage adds
the missing luck-vs-skill test from the literature review (docs section 7b):

  1. Exact binomial test per wallet (Kosowski et al. 2006 methodological
     template): H0 = wallet's train-window timing hit rate is drawn from
     Binomial(n_trades, p_population). Flags wallets whose train-window
     record is significant at p < 0.05 (one-sided).
  2. Monte-Carlo random-allocation benchmark (Papaioannou et al. 2024 /
     Choi et al. 2025): simulate B chance traders per wallet (same n_trades,
     population base rate), and ask whether the REAL bayes_score top-decile's
     realized FUTURE (out-of-sample) win rate exceeds what a population of
     pure-chance traders would produce at the same decile cutoff. This is the
     test the M6 Investment Challenge paper applies to Sharpe ratios.

Input:  data/processed/bayesian_scores.parquet (stage 7)
Output: pipeline/outputs/09_luck_vs_skill_null/

Run:
    uv run python -m pipeline.09_luck_vs_skill_null
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from scipy import stats
from tqdm import tqdm

from pipeline._numeric import as_float
from pipeline._paths import BAYES_SCORES_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout

_N_BOOTSTRAP = 2000
_ALPHA = 0.05
_RNG_SEED = 42


def _print_box(title: str) -> None:
    width = 64
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _binomial_test_flags(df: pl.DataFrame, p_pop: float) -> pl.DataFrame:
    n = df["n_trades_timing"].to_numpy()
    k = np.round(df["raw_timing"].to_numpy() * n).astype(int)
    p_values = np.array(
        [
            stats.binomtest(int(ki), int(ni), p_pop, alternative="greater").pvalue
            for ki, ni in zip(k, n, strict=True)
        ]
    )
    return df.with_columns(
        [
            pl.Series("binom_p_value", p_values),
            pl.Series("binom_significant", p_values < _ALPHA),
        ]
    )


def _monte_carlo_top_decile_null(
    n_trades: np.ndarray, p_pop: float, decile_size: int, rng: np.random.Generator
) -> np.ndarray:
    """B simulations of a chance-trader population's top-decile mean win rate."""
    null_means = np.empty(_N_BOOTSTRAP)
    for b in range(_N_BOOTSTRAP):
        sim_wins = rng.binomial(n_trades, p_pop)
        sim_win_rate = sim_wins / n_trades
        top_idx = np.argpartition(sim_win_rate, -decile_size)[-decile_size:]
        null_means[b] = sim_win_rate[top_idx].mean()
    return null_means


def _run(out_dir: Path) -> None:
    with tqdm(total=3, desc="Stage 9", unit="step", dynamic_ncols=True) as pbar:
        pbar.set_postfix_str(f"loading {BAYES_SCORES_PATH}")
        df = pl.read_parquet(BAYES_SCORES_PATH).filter(
            pl.col("raw_timing").is_not_null() & pl.col("n_trades_timing").is_not_null()
        )
        pbar.update()

        pbar.set_postfix_str("computing population base rate")
        total_wins = as_float((df["raw_timing"] * df["n_trades_timing"]).sum())
        total_n = as_float(df["n_trades_timing"].sum())
        p_pop = total_wins / total_n if total_n else 0.5
        pbar.update()

        pbar.set_postfix_str("exact binomial test per wallet (Kosowski et al. 2006)")
        df = _binomial_test_flags(df, p_pop)
        pbar.update()

    _print_box("LUCK-VS-SKILL VALIDITY CHECK")
    print(f"  Wallets tested:              {len(df):,}")
    print(f"  Population base hit rate:    {p_pop:.4f}")
    print()

    _print_box("TEST 1: EXACT BINOMIAL (Kosowski et al. 2006)")
    n_sig = int(df["binom_significant"].sum())
    pct_sig = n_sig / len(df) * 100
    print(f"  Wallets with train-window record significant at p<{_ALPHA}: "
          f"{n_sig:,} ({pct_sig:.2f}%)")
    print("  Reference: Gomez-Cram et al. (2026) flag 3.14% of Polymarket accounts")
    print("  as 'skilled winners' via an analogous persistence test.")
    print()

    top_decile_n = max(1, len(df) // 10)
    top_decile = df.sort("bayes_score", descending=True).head(top_decile_n)
    overlap = int(top_decile["binom_significant"].sum())
    print(f"  Of the {top_decile_n:,} bayes_score top-decile wallets, {overlap:,} "
          f"({overlap / top_decile_n * 100:.1f}%) are also binomial-significant.")
    print()

    _print_box("TEST 2: MONTE-CARLO RANDOM-ALLOCATION NULL (Papaioannou et al. 2024)")
    n_trades_arr = df["n_trades_timing"].to_numpy().astype(np.int64)
    rng = np.random.default_rng(_RNG_SEED)
    null_dist = _monte_carlo_top_decile_null(n_trades_arr, p_pop, top_decile_n, rng)

    real_future_wr = as_float(top_decile["future_win_rate"].mean())
    null_mean = float(null_dist.mean())
    null_std = float(null_dist.std())
    percentile = float((null_dist < real_future_wr).mean() * 100)

    print(f"  Real top-decile mean FUTURE win rate (out-of-sample): {real_future_wr:.4f}")
    print(f"  Null (chance-trader) top-decile mean TRAIN win rate:")
    print(f"    mean={null_mean:.4f}  std={null_std:.4f}")
    print(f"  Real out-of-sample value falls at the {percentile:.1f}th percentile of the null.")
    if percentile > 95:
        print("  -> Top-decile performance EXCEEDS the chance benchmark (p<0.05, one-sided).")
    else:
        print("  -> Cannot reject the null that top-decile performance is explainable by chance.")
    print()
    print("  NOTE: the null uses train-window base rate + trade counts to simulate chance")
    print("  traders, then compares against real OUT-OF-SAMPLE future win rate — a stricter")
    print("  test than comparing null to the (trivially correlated) train-window value.")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(null_dist, bins=50, alpha=0.7, label="chance-trader null (train-window sim)")
    ax.axvline(real_future_wr, color="red", linewidth=2, label="real top-decile (future, OOS)")
    ax.set_title("Top-decile win rate: real (out-of-sample) vs chance-trader null")
    ax.set_xlabel("win rate")
    ax.set_ylabel("count (simulations)")
    ax.legend()
    save_fig(fig, out_dir, "luck_vs_skill_null.png")


def main() -> None:
    out_dir = get_output_dir("09_luck_vs_skill_null")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

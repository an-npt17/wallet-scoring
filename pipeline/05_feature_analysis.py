"""
Stage 5: Feature–label correlation analysis and distribution inspection.

Answers:
  - Which features correlate most with realized_win_rate and total_realized_pnl?
  - Are long/short skills empirically orthogonal? (RQ1)
  - What is the side-asymmetry quadrant distribution?
  - How do proposed features compare to B1-B5 baselines?

Inputs:
  data/processed/wallet_features.parquet
  data/processed/labels.parquet
  data/processed/baselines.parquet  (optional)

Run:
    uv run python pipeline/05_feature_analysis.py
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl
from tqdm import tqdm

from pipeline._paths import BASELINES_PATH, FEATURES_PATH, LABELS_PATH
from pipeline._report import get_output_dir, save_fig, tee_stdout

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s"
)
logger = logging.getLogger(__name__)

_PROPOSED_FEATURES = [
    "long_win_rate",
    "short_win_rate",
    "side_asymmetry",
    "overall_win_rate",
    "avg_roi",
    "total_pnl",
    "leverage_adj_roi",
    "mean_leverage",
    "max_leverage",
    "sizing_skill",
    "liquidation_rate",
    "n_trades",
    "avg_duration_hours",
    "trade_frequency_per_day",
    "n_assets",
    "active_span_days",
]

_BASELINE_FEATURES = [
    "b1_composite",
    "b2_pnl",
    "b3_roi",
    "b4_win_rate",
    "b5_sharpe",
]

_LABEL_COLS = ["realized_win_rate", "total_realized_pnl"]


def _pearson(df: pl.DataFrame, col_a: str, col_b: str) -> float:
    sub = df.select([col_a, col_b]).drop_nulls()
    if len(sub) < 5:
        return float("nan")
    return pl.corr(sub[col_a], sub[col_b], eager=True).item()


def _print_box(title: str) -> None:
    width = 60
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _print_correlations(
    df: pl.DataFrame, feature_cols: list[str], desc: str = "correlations"
) -> None:
    print(f"  {'Feature':<26} {'vs win_rate':>14} {'vs total_pnl':>14}")
    print("  " + "-" * 56)
    for feat in tqdm(
        feature_cols, desc=desc, unit="feat", leave=False, dynamic_ncols=True
    ):
        if feat not in df.columns:
            continue
        r_wr = (
            _pearson(df, feat, "realized_win_rate")
            if "realized_win_rate" in df.columns
            else float("nan")
        )
        r_pnl = (
            _pearson(df, feat, "total_realized_pnl")
            if "total_realized_pnl" in df.columns
            else float("nan")
        )
        print(f"  {feat:<26} {r_wr:>+14.3f} {r_pnl:>+14.3f}")


def _run(out_dir: Path) -> None:
    features = pl.read_parquet(FEATURES_PATH)
    labels = pl.read_parquet(LABELS_PATH)
    df = features.join(labels, on="wallet", how="inner")
    logger.info("Joined: %s wallets", f"{len(df):,}")

    # ── Side orthogonality (RQ1) ────────────────────────────────────────────
    _print_box("SIDE ORTHOGONALITY — RQ1")
    r_sides = _pearson(df, "long_win_rate", "short_win_rate")
    print(f"  Pearson r(long_WR, short_WR) = {r_sides:+.3f}")
    if abs(r_sides) < 0.3:
        print("  → LOW correlation — side decomposition is justified")
    elif abs(r_sides) < 0.5:
        print("  → MODERATE — partial skill overlap")
    else:
        print("  → HIGH — single score may suffice")
    print()

    # ── Proposed feature correlations ────────────────────────────────────────
    _print_box("PROPOSED FEATURES × LABELS")
    _print_correlations(df, _PROPOSED_FEATURES, desc="proposed features")
    print()

    present_feats = [f for f in _PROPOSED_FEATURES if f in df.columns]
    r_wrs = [_pearson(df, f, "realized_win_rate") for f in present_feats]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(present_feats, r_wrs)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_title("Proposed features × realized_win_rate (Pearson r)")
    ax.set_xlabel("r")
    save_fig(fig, out_dir, "feature_correlations.png")

    # ── Side asymmetry quadrant ─────────────────────────────────────────────
    _print_box("SIDE ASYMMETRY QUADRANT COUNTS")
    quad = df.with_columns(
        [
            (pl.col("long_win_rate") > 0.5).alias("long_skilled"),
            (pl.col("short_win_rate") > 0.5).alias("short_skilled"),
        ]
    ).drop_nulls(subset=["long_skilled", "short_skilled"])
    total_q = len(quad)
    for ls, ss, label in [
        (True, True, "Q1  Long✓ Short✓ (dual skilled)"),
        (True, False, "Q2  Long✓ Short✗ (long specialist)"),
        (False, True, "Q3  Long✗ Short✓ (short specialist)"),
        (False, False, "Q4  Long✗ Short✗ (unskilled)"),
    ]:
        n = int(
            quad.filter(
                (pl.col("long_skilled") == ls) & (pl.col("short_skilled") == ss)
            ).height
        )
        pct = n / total_q * 100 if total_q > 0 else 0.0
        print(f"  {label}: {n:>8,}  ({pct:.1f}%)")
    print()

    quad_counts = [
        int(
            quad.filter(
                (pl.col("long_skilled") == ls) & (pl.col("short_skilled") == ss)
            ).height
        )
        for ls, ss in [(True, True), (True, False), (False, True), (False, False)]
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["Q1 dual", "Q2 long-only", "Q3 short-only", "Q4 unskilled"], quad_counts)
    ax.set_title("Side-asymmetry quadrant distribution")
    ax.set_ylabel("n wallets")
    save_fig(fig, out_dir, "quadrant_distribution.png")

    # ── Baseline comparison ──────────────────────────────────────────────────
    if BASELINES_PATH.exists():
        _print_box("BASELINE FEATURES × LABELS")
        baselines = pl.read_parquet(BASELINES_PATH)
        merged = df.join(baselines, on="wallet", how="inner")
        logger.info("Merged with baselines: %s wallets", f"{len(merged):,}")
        _print_correlations(merged, _BASELINE_FEATURES, desc="baseline features")
        print()

    # ── Distribution summary ─────────────────────────────────────────────────
    _print_box("FEATURE DISTRIBUTION SUMMARY")
    numeric_feats = [c for c in _PROPOSED_FEATURES if c in features.columns]
    summary = features.select(numeric_feats).describe()
    print(summary)


def main() -> None:
    out_dir = get_output_dir("05_feature_analysis")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

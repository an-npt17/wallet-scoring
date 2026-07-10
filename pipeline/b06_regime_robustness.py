"""Stage B06: Regime robustness -- does the crowding lift survive a rolling
walk-forward split, and does it hold across market conditions?

b01-b05 all evaluate on ONE later-in-time 70/30 holdout: every out-of-sample
number is a single draw from a single market regime. This stage:

  1. Rolling walk-forward -- expanding train window, K consecutive
     non-overlapping test folds. Re-fits BASELINE and FULL LightGBM per fold
     and reports ROC-AUC / PR-AUC mean +/- std across folds, turning b01's
     single point estimate into an interval estimate.
  2. Regime breakdown -- labels every test row by (a) exogenous BTC/ETH macro
     vol/trend regime (src.burst.regime -- proxies overall crypto market
     condition, not the trading venue) and (b) endogenous market-wide
     liquidation-intensity tertile (own panel, no external dependency, catches
     idiosyncratic crowding the macro regime misses). Reports lift per bucket.
  3. Event stress test -- the biggest simultaneous liquidation-burst clusters
     in the data get evaluated as targeted mini-holdouts: precision@k /
     recall in the window around each cluster, since averaged fold metrics
     can hide a miss on the one crash that mattered.

Input:  data/processed/burst_panel.parquet (built by b01)
Output: pipeline/outputs/b06_regime_robustness/

Run:
    uv run python pipeline/b06_regime_robustness.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from pydantic import BaseModel

from pipeline._numeric import as_float
from pipeline._paths import PROCESSED_DIR
from pipeline._report import get_output_dir, save_fig, tee_stdout
from pipeline.b01_burst_baseline import (
    PANEL_PATH,
    _fit_eval,
    _pr_auc,
    _print_box,
    _roc_auc,
)
from src.burst import MarketRegimeService, PanelConfig

_INITIAL_TRAIN_FRAC = 0.40
_N_FOLDS = 5
_EVENT_TOP_N = 5
_EVENT_WINDOW_BINS = 72  # +/- 6h at 5-min bins
_TOP_K_FRAC = 0.05
OOF_PATH = PROCESSED_DIR / "b06_oof.parquet"


class FoldResult(BaseModel):
    fold: int
    train_rows: int
    test_rows: int
    test_start: int
    test_end: int
    base_roc: float
    base_pr: float
    full_roc: float
    full_pr: float


def _fold_cuts(bin_ts: pl.Series) -> list[float]:
    qs = [
        _INITIAL_TRAIN_FRAC + i * (1 - _INITIAL_TRAIN_FRAC) / _N_FOLDS
        for i in range(_N_FOLDS + 1)
    ]
    return [as_float(bin_ts.quantile(q)) for q in qs]


def _endogenous_crowd_regime(panel: pl.DataFrame) -> pl.DataFrame:
    """Tertile-buckets market-wide liquidation intensity per bin (own panel,
    no external dependency) -- catches idiosyncratic crowding events that a
    BTC/ETH macro regime label would miss."""
    mkt = (
        panel.group_by("bin_ts")
        .agg(pl.col("market_liq_short").first().alias("mkt_liq"))
        .sort("bin_ts")
    )
    q1 = as_float(mkt["mkt_liq"].quantile(1 / 3))
    q2 = as_float(mkt["mkt_liq"].quantile(2 / 3))
    return mkt.with_columns(
        pl.when(pl.col("mkt_liq") < q1)
        .then(pl.lit("low_crowd"))
        .when(pl.col("mkt_liq") < q2)
        .then(pl.lit("med_crowd"))
        .otherwise(pl.lit("high_crowd"))
        .alias("crowd_regime")
    ).select("bin_ts", "crowd_regime")


def _walk_forward(
    panel: pl.DataFrame, baseline_feats: list[str], full_feats: list[str]
) -> tuple[list[FoldResult], pl.DataFrame]:
    cuts = _fold_cuts(panel["bin_ts"])
    fold_results: list[FoldResult] = []
    oof_frames: list[pl.DataFrame] = []
    for i in range(_N_FOLDS):
        train = panel.filter(pl.col("bin_ts") < cuts[i])
        test = panel.filter(
            (pl.col("bin_ts") >= cuts[i]) & (pl.col("bin_ts") < cuts[i + 1])
        )
        if train.height == 0 or test.height == 0:
            continue
        base_res, p_base, _ = _fit_eval(f"fold{i} baseline", baseline_feats, train, test)
        full_res, p_full, _ = _fit_eval(f"fold{i} full", full_feats, train, test)
        fold_results.append(
            FoldResult(
                fold=i,
                train_rows=train.height,
                test_rows=test.height,
                test_start=int(cuts[i]),
                test_end=int(cuts[i + 1]),
                base_roc=base_res.roc_auc,
                base_pr=base_res.pr_auc,
                full_roc=full_res.roc_auc,
                full_pr=full_res.pr_auc,
            )
        )
        oof_frames.append(
            test.select("asset", "bin_ts", "label").with_columns(
                pl.Series("pred_base", p_base),
                pl.Series("pred_full", p_full),
                pl.lit(i).alias("fold"),
            )
        )
        print(
            f"  fold {i}: train {train.height:>8,} test {test.height:>7,} "
            f"| base ROC {base_res.roc_auc:.4f} PR {base_res.pr_auc:.4f} "
            f"| full ROC {full_res.roc_auc:.4f} PR {full_res.pr_auc:.4f}"
        )
    return fold_results, pl.concat(oof_frames)


def _print_summary(folds: list[FoldResult]) -> None:
    _print_box("WALK-FORWARD SUMMARY (mean +/- std across folds)")
    base_roc = np.array([f.base_roc for f in folds])
    base_pr = np.array([f.base_pr for f in folds])
    full_roc = np.array([f.full_roc for f in folds])
    full_pr = np.array([f.full_pr for f in folds])
    print(
        f"  baseline  ROC-AUC {base_roc.mean():.4f} +/- {base_roc.std():.4f}"
        f"   PR-AUC {base_pr.mean():.4f} +/- {base_pr.std():.4f}"
    )
    print(
        f"  full      ROC-AUC {full_roc.mean():.4f} +/- {full_roc.std():.4f}"
        f"   PR-AUC {full_pr.mean():.4f} +/- {full_pr.std():.4f}"
    )
    lift_roc = full_roc - base_roc
    lift_pr = full_pr - base_pr
    print(
        f"  LIFT      ROC-AUC {lift_roc.mean():+.4f} +/- {lift_roc.std():.4f}"
        f"   PR-AUC {lift_pr.mean():+.4f} +/- {lift_pr.std():.4f}"
    )
    print()


def _print_regime_breakdown(oof: pl.DataFrame, regime_col: str) -> None:
    _print_box(f"BREAKDOWN BY {regime_col.upper()}")
    buckets = oof[regime_col].drop_nulls().unique().sort().to_list()
    for bucket in buckets:
        sub = oof.filter(pl.col(regime_col) == bucket)
        y = sub["label"].to_numpy().astype(np.int8)
        p_base = sub["pred_base"].to_numpy()
        p_full = sub["pred_full"].to_numpy()
        base_pr = _pr_auc(y, p_base)
        full_pr = _pr_auc(y, p_full)
        print(
            f"  {bucket:<12} n={sub.height:>8,} pos_rate={y.mean():.4f} "
            f"| base ROC {_roc_auc(y, p_base):.4f} PR {base_pr:.4f} "
            f"| full ROC {_roc_auc(y, p_full):.4f} PR {full_pr:.4f} "
            f"| lift(PR) {full_pr - base_pr:+.4f}"
        )
    print()


def _event_stress_test(oof: pl.DataFrame) -> None:
    _print_box(f"EVENT STRESS TEST (top {_EVENT_TOP_N} liquidation-burst clusters)")
    cluster = (
        oof.group_by("bin_ts")
        .agg(pl.col("label").sum().alias("n_assets_bursting"))
        .sort("n_assets_bursting", descending=True)
    )
    candidates = cluster["bin_ts"].to_list()
    used: list[int] = []
    for center in candidates:
        if len(used) >= _EVENT_TOP_N:
            break
        if any(abs(center - u) < _EVENT_WINDOW_BINS * 300 for u in used):
            continue
        used.append(center)
        lo, hi = center - _EVENT_WINDOW_BINS * 300, center + _EVENT_WINDOW_BINS * 300
        window = oof.filter((pl.col("bin_ts") >= lo) & (pl.col("bin_ts") <= hi))
        y = window["label"].to_numpy().astype(np.int8)
        p_full = window["pred_full"].to_numpy()
        k = max(1, int(len(p_full) * _TOP_K_FRAC))
        order = np.argsort(-p_full)
        top_idx = order[:k]
        precision_at_k = float(y[top_idx].mean())
        recall_at_k = float(y[top_idx].sum() / max(y.sum(), 1))
        print(
            f"  event @ bin_ts={center}  window_rows={window.height:,}  "
            f"pos_rate={y.mean():.4f}  precision@{_TOP_K_FRAC:.0%}={precision_at_k:.4f}  "
            f"recall@{_TOP_K_FRAC:.0%}={recall_at_k:.4f}  ROC {_roc_auc(y, p_full):.4f}"
        )
    print()


def _plot(folds: list[FoldResult], oof: pl.DataFrame, out_dir: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))
    x = [f.fold for f in folds]
    ax1.plot(x, [f.base_pr for f in folds], "o-", label="baseline PR-AUC")
    ax1.plot(x, [f.full_pr for f in folds], "o-", label="full PR-AUC")
    ax1.set_xlabel("fold (time-ordered)")
    ax1.set_ylabel("PR-AUC")
    ax1.set_title("Walk-forward PR-AUC per fold")
    ax1.legend()

    buckets = oof["crowd_regime"].drop_nulls().unique().sort().to_list()
    lifts: list[float] = []
    for b in buckets:
        sub = oof.filter(pl.col("crowd_regime") == b)
        y = sub["label"].to_numpy().astype(np.int8)
        lifts.append(
            _pr_auc(y, sub["pred_full"].to_numpy()) - _pr_auc(y, sub["pred_base"].to_numpy())
        )
    ax2.bar(buckets, lifts, color="steelblue")
    ax2.axhline(0.0, color="black", linewidth=0.8)
    ax2.set_ylabel("PR-AUC lift (full - baseline)")
    ax2.set_title("Crowding lift by endogenous crowd regime")
    save_fig(fig, out_dir, "regime_robustness.png")


def _run(out_dir: Path) -> None:
    cfg = PanelConfig()
    panel = pl.read_parquet(PANEL_PATH).sort("bin_ts")
    baseline_feats = cfg.baseline_features
    full_feats = (
        cfg.baseline_features
        + cfg.crowding_features
        + cfg.volume_features
        + cfg.cross_asset_features
    )

    _print_box("BUILDING REGIME LABELS")
    macro = MarketRegimeService().label_bins(panel["bin_ts"].unique())
    crowd = _endogenous_crowd_regime(panel)
    regime = macro.join(crowd, on="bin_ts", how="left")
    print(f"  macro (BTC/ETH) regime days: {macro.height:,}")
    print(f"  endogenous crowd regime bins: {crowd.height:,}")
    print()

    _print_box(
        f"ROLLING WALK-FORWARD (initial train {_INITIAL_TRAIN_FRAC:.0%}, {_N_FOLDS} folds)"
    )
    fold_results, oof = _walk_forward(panel, baseline_feats, full_feats)
    oof = oof.join(regime, on="bin_ts", how="left")
    oof = oof.join(
        panel.select("asset", "bin_ts", "future_notional"), on=["asset", "bin_ts"], how="left"
    )
    oof.write_parquet(OOF_PATH)
    print(f"  OOF predictions written: {OOF_PATH} ({oof.height:,} rows)")
    print()

    _print_summary(fold_results)
    _print_regime_breakdown(oof, "vol_regime")
    _print_regime_breakdown(oof, "trend_regime")
    _print_regime_breakdown(oof, "crowd_regime")
    _event_stress_test(oof)
    _plot(fold_results, oof, out_dir)


def main() -> None:
    out_dir = get_output_dir("b06_regime_robustness")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

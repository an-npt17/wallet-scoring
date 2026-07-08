"""
Stage B01: Liquidation-burst prediction — does crowding beat the self-exciting baseline?

M1 of the liquidation-burst thesis. Builds the leakage-safe per-asset 5-min panel
(src/burst), splits it time-ordered (train = earlier bins, test = later bins), and
compares two LightGBM classifiers on the held-out future window:

  * BASELINE  — past-intensity features only (past_liq_short/long). This is the
    self-exciting / univariate-Hawkes proxy that M0 showed already reaches
    AUC ~0.83-0.87. It is the bar to beat.
  * FULL      — baseline + tier-crowding / imbalance / concentration / leverage /
    velocity features. The research question: does crowding add out-of-sample lift?

Reports ROC-AUC and PR-AUC (PR-AUC primary, class is imbalanced ~4% positive),
plus feature importances, on a strictly later test period than training.

Input:  data/processed/positions.parquet
Output: data/processed/burst_panel.parquet
        pipeline/outputs/b01_burst_baseline/

Run:
    uv run python pipeline/b01_burst_baseline.py
"""

from pathlib import Path

import lightgbm as lgb
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel
from scipy.stats import rankdata

from pipeline._numeric import as_float
from pipeline._report import get_output_dir, save_fig, tee_stdout
from src.burst import (
    BurstPanelBuilderService,
    BurstTunerService,
    PanelConfig,
    TunerConfig,
)

POSITIONS_PATH = Path("data/processed/positions.parquet")
PANEL_PATH = Path("data/processed/burst_panel.parquet")
_TRAIN_FRAC = 0.70
_SEED = 42
_REBUILD_PANEL = False  # set True to force panel rebuild from positions
_N_TRIALS = 40


class ScoreResult(BaseModel):
    name: str
    n_features: int
    roc_auc: float
    pr_auc: float


def _print_box(title: str) -> None:
    width = 66
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _roc_auc(y: NDArray[np.int8], p: NDArray[np.float64]) -> float:
    pos = p[y == 1]
    neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # Mann-Whitney U -> AUC, tie-aware via rankdata.

    order = rankdata(p)
    r_pos = order[y == 1].sum()
    auc = (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    return float(auc)


def _pr_auc(y: NDArray[np.int8], p: NDArray[np.float64]) -> float:
    order = np.argsort(-p)
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    total_pos = y.sum()
    if total_pos == 0:
        return float("nan")
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / total_pos
    # average precision = sum precision * delta-recall
    dr = np.diff(np.concatenate([[0.0], recall]))
    return float(np.sum(precision * dr))


def _fit_eval(
    name: str,
    features: list[str],
    train: pl.DataFrame,
    test: pl.DataFrame,
) -> tuple[ScoreResult, NDArray[np.float64], lgb.LGBMClassifier]:
    x_tr = train.select(features).to_numpy()
    y_tr = train["label"].to_numpy().astype(np.int8)
    x_te = test.select(features).to_numpy()
    y_te = test["label"].to_numpy().astype(np.int8)
    model = lgb.LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=_SEED,
        verbose=-1,
    )
    model.fit(x_tr, y_tr)
    proba = np.asarray(model.predict_proba(x_te), dtype=np.float64)
    p_te = proba[:, 1]
    result = ScoreResult(
        name=name,
        n_features=len(features),
        roc_auc=round(_roc_auc(y_te, p_te), 4),
        pr_auc=round(_pr_auc(y_te, p_te), 4),
    )
    return result, p_te, model


def _run(out_dir: Path) -> None:
    cfg = PanelConfig()

    _print_box("BUILDING LEAKAGE-SAFE BURST PANEL")
    if PANEL_PATH.exists() and not _REBUILD_PANEL:
        panel = pl.read_parquet(PANEL_PATH)
        print(f"  Loaded cached panel: {PANEL_PATH}")
    else:
        positions = pl.read_parquet(POSITIONS_PATH)
        panel = BurstPanelBuilderService(cfg).build(positions)
        panel = panel.drop_nulls().sort("bin_ts")
        PANEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        panel.write_parquet(PANEL_PATH)
    print(f"  Panel rows (asset x active bin): {panel.height:,}")
    print(f"  Assets: {panel['asset'].n_unique()}")
    print(f"  Positive rate (burst): {panel['label'].mean():.4f}")
    print(
        f"  Label: h={cfg.horizon_bins * cfg.bin_seconds // 60}min, threshold>={cfg.threshold}"
    )
    print()

    # Time-ordered split: earlier bins train, later bins test (no leakage).
    cutoff = as_float(panel["bin_ts"].quantile(_TRAIN_FRAC))
    train = panel.filter(pl.col("bin_ts") < cutoff)
    test = panel.filter(pl.col("bin_ts") >= cutoff)
    print(f"  Train rows: {train.height:,} (pos {train['label'].mean():.4f})")
    print(f"  Test  rows: {test.height:,} (pos {test['label'].mean():.4f})")
    print()

    baseline_feats = cfg.baseline_features
    full_feats = (
        cfg.baseline_features
        + cfg.crowding_features
        + cfg.volume_features
        + cfg.cross_asset_features
    )

    base_res, _, _ = _fit_eval("baseline (past-intensity)", baseline_feats, train, test)
    full_res, _, full_model = _fit_eval("full (default LGBM)", full_feats, train, test)

    # Optuna-tuned full model, optimized for average-precision on an inner,
    # time-ordered validation slice of train (test untouched during tuning).
    _print_box(f"TUNING FULL MODEL (Optuna x{_N_TRIALS}, objective=average_precision)")
    tuner = BurstTunerService(TunerConfig(n_trials=_N_TRIALS, seed=_SEED))
    best = tuner.tune(train, full_feats)
    print(f"  Best params: {best.model_dump()}")
    tuned_model = tuner.build_model(best)
    tuned_model.fit(
        train.select(full_feats).to_numpy(), train["label"].to_numpy().astype(np.int8)
    )
    p_tuned = tuner.eval_scores(tuned_model, test, full_feats)
    y_te = test["label"].to_numpy().astype(np.int8)
    tuned_res = ScoreResult(
        name="full (tuned, AP)",
        n_features=len(full_feats),
        roc_auc=round(_roc_auc(y_te, p_tuned), 4),
        pr_auc=round(_pr_auc(y_te, p_tuned), 4),
    )

    _print_box("OUT-OF-SAMPLE RESULTS (later test period)")
    print(f"  {'model':<28} {'n_feat':>6} {'ROC-AUC':>9} {'PR-AUC':>9}")
    for r in (base_res, full_res, tuned_res):
        print(f"  {r.name:<28} {r.n_features:>6} {r.roc_auc:>9.4f} {r.pr_auc:>9.4f}")
    print()
    print(
        f"  LIFT full(default) over baseline:  ROC-AUC {full_res.roc_auc - base_res.roc_auc:+.4f}"
        f"   PR-AUC {full_res.pr_auc - base_res.pr_auc:+.4f}"
    )
    print(
        f"  LIFT full(tuned)   over baseline:  ROC-AUC {tuned_res.roc_auc - base_res.roc_auc:+.4f}"
        f"   PR-AUC {tuned_res.pr_auc - base_res.pr_auc:+.4f}"
    )
    print(
        f"  GAIN from tuning (tuned - default): PR-AUC {tuned_res.pr_auc - full_res.pr_auc:+.4f}"
    )
    base_rate = as_float(test["label"].mean())
    print(f"  (PR-AUC baseline = positive rate = {base_rate:.4f})")
    print()

    _plot(base_res, tuned_res, full_feats, tuned_model, out_dir)


def _plot(
    base_res: ScoreResult,
    full_res: ScoreResult,
    full_feats: list[str],
    full_model: lgb.LGBMClassifier,
    out_dir: Path,
) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))
    x = np.arange(2)
    ax1.bar(x - 0.2, [base_res.roc_auc, full_res.roc_auc], 0.4, label="ROC-AUC")
    ax1.bar(x + 0.2, [base_res.pr_auc, full_res.pr_auc], 0.4, label="PR-AUC")
    ax1.set_xticks(x, ["baseline\n(past-intensity)", "full\n(+crowding)"])
    ax1.set_ylabel("out-of-sample score")
    ax1.set_title("Burst prediction: crowding lift over self-exciting baseline")
    ax1.legend()

    imp = np.asarray(full_model.feature_importances_, dtype=np.float64)
    order = np.argsort(imp)
    ax2.barh(np.arange(len(full_feats)), imp[order], color="steelblue")
    ax2.set_yticks(np.arange(len(full_feats)), [full_feats[i] for i in order])
    ax2.set_xlabel("LightGBM feature importance (gain splits)")
    ax2.set_title("Full-model feature importance")
    save_fig(fig, out_dir, "burst_baseline_lift.png")


def main() -> None:
    out_dir = get_output_dir("b01_burst_baseline")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

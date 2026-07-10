"""Stage B08: Rolling walk-forward for CovTPP and ST-GNN.

b06 gives the LightGBM baseline/full comparison walk-forward confidence
intervals; @tab:m2's three-way ordering among CovTPP, ST-GNN, and the tuned
LightGBM (all within ~0.005 PR-AUC on a single split) is still untested across
folds -- flagged as the remaining piece of NS1. This stage closes that gap for
the two neural models: same expanding-window walk-forward and regime labels as
b06, applied to CovTPPBaselineService and STGNNBaselineService.

Each fold calls `fit_score(panel_upto_fold_end, cutoff_ts=fold_start)`: the
service itself trains only on rows before cutoff_ts and scores every row from
cutoff_ts onward, so truncating the panel to the fold's end makes "everything
from cutoff onward" exactly the fold's test window -- no separate test-set
argument needed.

Input:  data/processed/burst_panel.parquet (from b01)
Output: pipeline/outputs/b08_covtpp_stgnn_walkforward/

Run:
    uv run python -m pipeline.b08_covtpp_stgnn_walkforward
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from pydantic import BaseModel

from pipeline._numeric import as_float
from pipeline._report import get_output_dir, save_fig, tee_stdout
from pipeline.b01_burst_baseline import PANEL_PATH, _pr_auc, _print_box, _roc_auc
from pipeline.b06_regime_robustness import _endogenous_crowd_regime, _fold_cuts
from src.burst import (
    CovTPPBaselineService,
    CovTPPConfig,
    MarketRegimeService,
    STGNNBaselineService,
    STGNNConfig,
)

_MODELS = ("CovTPP", "ST-GNN")


class FoldResult(BaseModel):
    model: str
    fold: int
    train_rows: int
    test_rows: int
    roc_auc: float
    pr_auc: float


def _fit_one(
    model_name: str, panel: pl.DataFrame, cutoff: int, fold: int
) -> tuple[FoldResult, pl.DataFrame]:
    if model_name == "CovTPP":
        svc = CovTPPBaselineService(CovTPPConfig())
    else:
        svc = STGNNBaselineService(STGNNConfig())
    p, y, ts = svc.fit_score(panel, cutoff)
    train_rows = int(panel.filter(pl.col("bin_ts") < cutoff).height)
    roc = _roc_auc(y, p)
    pr = _pr_auc(y, p)
    result = FoldResult(
        model=model_name,
        fold=fold,
        train_rows=train_rows,
        test_rows=len(y),
        roc_auc=round(roc, 4),
        pr_auc=round(pr, 4),
    )
    oof = pl.DataFrame(
        {"bin_ts": ts, "label": y, "score": p.astype(np.float64)}
    ).with_columns(pl.lit(model_name).alias("model"), pl.lit(fold).alias("fold"))
    return result, oof


def _print_summary(results: list[FoldResult]) -> None:
    _print_box("WALK-FORWARD SUMMARY (mean +/- std across folds)")
    for model_name in _MODELS:
        rows = [r for r in results if r.model == model_name]
        roc = np.array([r.roc_auc for r in rows])
        pr = np.array([r.pr_auc for r in rows])
        print(
            f"  {model_name:<8} ROC-AUC {roc.mean():.4f} +/- {roc.std():.4f}"
            f"   PR-AUC {pr.mean():.4f} +/- {pr.std():.4f}"
        )
    print()


def _print_regime_breakdown(oof: pl.DataFrame, regime_col: str) -> None:
    _print_box(f"BREAKDOWN BY {regime_col.upper()}")
    buckets = oof[regime_col].drop_nulls().unique().sort().to_list()
    for model_name in _MODELS:
        for bucket in buckets:
            sub = oof.filter((pl.col("model") == model_name) & (pl.col(regime_col) == bucket))
            if sub.height == 0:
                continue
            y = sub["label"].to_numpy().astype(np.int8)
            p = sub["score"].to_numpy()
            print(
                f"  {model_name:<8} {bucket:<12} n={sub.height:>7,} pos_rate={y.mean():.4f} "
                f"| ROC {_roc_auc(y, p):.4f}  PR {_pr_auc(y, p):.4f}"
            )
    print()


def _plot(results: list[FoldResult], out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for model_name in _MODELS:
        rows = sorted((r for r in results if r.model == model_name), key=lambda r: r.fold)
        ax.plot([r.fold for r in rows], [r.pr_auc for r in rows], "o-", label=model_name)
    ax.set_xlabel("fold (time-ordered)")
    ax.set_ylabel("PR-AUC")
    ax.set_title("Walk-forward PR-AUC per fold: CovTPP vs. ST-GNN")
    ax.legend()
    save_fig(fig, out_dir, "covtpp_stgnn_walkforward.png")


def _run(out_dir: Path) -> None:
    panel = pl.read_parquet(PANEL_PATH).sort("bin_ts")
    cuts = _fold_cuts(panel["bin_ts"])
    n_folds = len(cuts) - 1

    macro = MarketRegimeService().label_bins(panel["bin_ts"].unique())
    crowd = _endogenous_crowd_regime(panel)
    regime = macro.join(crowd, on="bin_ts", how="left")

    results: list[FoldResult] = []
    oof_frames: list[pl.DataFrame] = []
    for i in range(n_folds):
        panel_i = panel.filter(pl.col("bin_ts") < cuts[i + 1])
        cutoff = int(cuts[i])
        for model_name in _MODELS:
            res, oof = _fit_one(model_name, panel_i, cutoff, i)
            results.append(res)
            oof_frames.append(oof)
            print(
                f"  fold {i} {model_name:<8}: train {res.train_rows:>8,} test {res.test_rows:>7,} "
                f"| ROC {res.roc_auc:.4f}  PR {res.pr_auc:.4f}"
            )

    oof = pl.concat(oof_frames).join(regime, on="bin_ts", how="left")
    print()
    _print_summary(results)
    _print_regime_breakdown(oof, "vol_regime")
    _print_regime_breakdown(oof, "trend_regime")
    _print_regime_breakdown(oof, "crowd_regime")
    _plot(results, out_dir)


def main() -> None:
    out_dir = get_output_dir("b08_covtpp_stgnn_walkforward")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

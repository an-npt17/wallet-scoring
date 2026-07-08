"""
Stage B03: Transformer Hawkes Process (THP) neural baseline.

Trains a compact self-attention temporal-point-process model on each asset's
liquidation event stream (train period only) and scores the conditional
intensity at every test bin — the SAME test bins and burst label as b01/b02 —
so PR-AUC / ROC-AUC are directly comparable to the LightGBM and classical
Hawkes models.

Run:
    uv run python pipeline/b03_thp_baseline.py
"""

from pathlib import Path

import numpy as np
import polars as pl
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, roc_auc_score

from pipeline._numeric import as_float
from pipeline._report import get_output_dir, tee_stdout
from src.burst import THPBaselineService, THPConfig

POSITIONS_PATH = Path("data/processed/positions.parquet")
PANEL_PATH = Path("data/processed/burst_panel.parquet")
_TRAIN_FRAC = 0.70

# Reference numbers from b01 (LightGBM) and b02 (classical Hawkes), identical split.
_REFERENCE: list[tuple[str, float, float]] = [
    ("Hawkes (univariate, MLE)", 0.9746, 0.1570),
    ("Hawkes (+market, MLE)", 0.9740, 0.1568),
    ("LGBM baseline (past-intensity)", 0.9078, 0.2281),
    ("LGBM full (tuned, AP)", 0.9801, 0.2502),
]


def _print_box(title: str) -> None:
    width = 66
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _run(out_dir: Path) -> None:
    panel = pl.read_parquet(PANEL_PATH).sort("bin_ts")
    positions = pl.read_parquet(POSITIONS_PATH)
    cutoff = int(as_float(panel["bin_ts"].quantile(_TRAIN_FRAC)))
    test = panel.filter(pl.col("bin_ts") >= cutoff)
    print(f"  Panel rows: {panel.height:,}  test bins: {test.height:,}")
    print(f"  Cutoff ts: {cutoff}  test positive rate: {test['label'].mean():.4f}")
    print()

    _print_box("TRAINING TRANSFORMER HAWKES PROCESS (THP, TPP-MLE)")
    svc = THPBaselineService(THPConfig())
    p, y = svc.fit_score(positions, panel, cutoff)
    roc = float(roc_auc_score(y, p))
    pr = float(average_precision_score(y, p))

    _print_box("OUT-OF-SAMPLE COMPARISON (same test bins, all stages)")
    print(f"  {'model':<34} {'ROC-AUC':>9} {'PR-AUC':>9}")
    print(f"  {'THP (neural TPP)':<34} {roc:>9.4f} {pr:>9.4f}")
    for name, r, pa in _REFERENCE:
        print(f"  {name:<34} {r:>9.4f} {pa:>9.4f}")
    print()
    print(f"  (random PR-AUC = positive rate = {as_float(test['label'].mean()):.4f})")


def main() -> None:
    out_dir = get_output_dir("b03_thp_baseline")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

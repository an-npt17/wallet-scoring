"""Stage B02: Classical Hawkes baselines for liquidation-burst prediction.

Fits published-method self-exciting baselines by maximum likelihood and scores
them on the SAME test bins and burst label as b01, so PR-AUC / ROC-AUC are
directly comparable to the LightGBM models:

  * Hawkes (univariate)      — per-asset self-exciting exp-kernel Hawkes.
  * Hawkes (+market)         — self + all-asset market excitation (shared decay),
                               a tractable multivariate-Hawkes stand-in.

These give the thesis a *named, citable* baseline to beat instead of the
hand-rolled past-intensity proxy. Compare against b01's LightGBM numbers.

Run:
    uv run python pipeline/b02_hawkes_baseline.py
"""

from pathlib import Path

import numpy as np
import polars as pl
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, roc_auc_score

from pipeline._numeric import as_float
from pipeline._report import get_output_dir, tee_stdout
from src.burst import HawkesBaselineService

POSITIONS_PATH = Path("data/processed/positions.parquet")
PANEL_PATH = Path("data/processed/burst_panel.parquet")
_TRAIN_FRAC = 0.70

# b01 reference (tuned LightGBM run, identical split/label) for the joint table.
_B01_REFERENCE: list[tuple[str, float, float]] = [
    ("LGBM baseline (past-intensity)", 0.9078, 0.2281),
    ("LGBM full (tuned, AP)", 0.9801, 0.2502),
]


def _print_box(title: str) -> None:
    width = 66
    print("╔" + "═" * width + "╗")
    print(f"║  {title:<{width - 2}}║")
    print("╚" + "═" * width + "╝")


def _metrics(y: NDArray[np.int8], p: NDArray[np.float64]) -> tuple[float, float]:
    return float(roc_auc_score(y, p)), float(average_precision_score(y, p))


def _run(out_dir: Path) -> None:
    panel = pl.read_parquet(PANEL_PATH).sort("bin_ts")
    positions = pl.read_parquet(POSITIONS_PATH)
    cutoff = int(as_float(panel["bin_ts"].quantile(_TRAIN_FRAC)))

    test = panel.filter(pl.col("bin_ts") >= cutoff)
    print(f"  Panel rows: {panel.height:,}  test bins: {test.height:,}")
    print(f"  Cutoff ts: {cutoff}  test positive rate: {test['label'].mean():.4f}")
    print()

    svc = HawkesBaselineService()

    _print_box("FITTING HAWKES (univariate self-exciting, MLE)")
    y_uni_p, y_uni = svc.score(positions, panel, cutoff, use_market=False)
    roc_uni, pr_uni = _metrics(y_uni, y_uni_p)

    _print_box("FITTING HAWKES (+market cross-excitation, MLE)")
    y_mkt_p, y_mkt = svc.score(positions, panel, cutoff, use_market=True)
    roc_mkt, pr_mkt = _metrics(y_mkt, y_mkt_p)

    _print_box("OUT-OF-SAMPLE COMPARISON (same test bins as b01)")
    print(f"  {'model':<34} {'ROC-AUC':>9} {'PR-AUC':>9}")
    print(f"  {'Hawkes (univariate)':<34} {roc_uni:>9.4f} {pr_uni:>9.4f}")
    print(f"  {'Hawkes (+market)':<34} {roc_mkt:>9.4f} {pr_mkt:>9.4f}")
    for name, roc, pr in _B01_REFERENCE:
        print(f"  {name:<34} {roc:>9.4f} {pr:>9.4f}")
    print()
    base_rate = as_float(test["label"].mean())
    print(f"  (random PR-AUC = positive rate = {base_rate:.4f})")


def main() -> None:
    out_dir = get_output_dir("b02_hawkes_baseline")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

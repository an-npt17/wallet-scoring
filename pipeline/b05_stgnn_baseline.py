"""Stage B05: Spatio-temporal GNN for liquidation-burst prediction.

Treats the 40 assets as nodes on the shared global 5-minute grid; a graph layer
mixes each active asset's 17 features with a cross-asset market message per step,
and a per-node GRU carries temporal state. The burst hazard is scored on the SAME
test bins and label as b01-b04 for a directly comparable PR-AUC.

Run:
    uv run python pipeline/b05_stgnn_baseline.py
"""

from pathlib import Path

import polars as pl
from sklearn.metrics import average_precision_score, roc_auc_score

from pipeline._numeric import as_float
from pipeline._report import get_output_dir, tee_stdout
from src.burst import STGNNBaselineService, STGNNConfig

PANEL_PATH = Path("data/processed/burst_panel.parquet")
_TRAIN_FRAC = 0.70

_REFERENCE: list[tuple[str, float, float]] = [
    ("THP (neural TPP)", 0.9700, 0.1294),
    ("Hawkes (univariate, MLE)", 0.9746, 0.1570),
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
    cutoff = int(as_float(panel["bin_ts"].quantile(_TRAIN_FRAC)))
    test = panel.filter(pl.col("bin_ts") >= cutoff)
    print(f"  Panel rows: {panel.height:,}  test bins: {test.height:,}")
    print(f"  Cutoff ts: {cutoff}  test positive rate: {test['label'].mean():.4f}")
    print()

    _print_box("TRAINING SPATIO-TEMPORAL GNN (cross-asset graph + GRU)")
    svc = STGNNBaselineService(STGNNConfig())
    p, y = svc.fit_score(panel, cutoff)
    roc = float(roc_auc_score(y, p))
    pr = float(average_precision_score(y, p))

    _print_box("OUT-OF-SAMPLE COMPARISON (same test bins, all stages)")
    print(f"  {'model':<34} {'ROC-AUC':>9} {'PR-AUC':>9}")
    print(f"  {'ST-GNN (cross-asset graph)':<34} {roc:>9.4f} {pr:>9.4f}")
    for name, r, pa in _REFERENCE:
        print(f"  {name:<34} {r:>9.4f} {pa:>9.4f}")
    print()
    print(f"  (random PR-AUC = positive rate = {as_float(test['label'].mean()):.4f})")


def main() -> None:
    out_dir = get_output_dir("b05_stgnn_baseline")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

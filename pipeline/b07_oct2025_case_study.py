"""Stage B07: Named case study -- the Oct 10-11 2025 liquidation event.

@sec:robustness (b06) shows the crowding lift survives a rolling walk-forward
and holds across regime buckets, but every fold there is anonymous ("fold 3",
"high-vol bucket"). This stage ties the model to a real, externally verifiable
event: the Oct 10-11 2025 crash (Trump tariff-shock selloff), one of the
largest simultaneous crypto liquidation events on record. It ranks #2 of all
491 days in this dataset by burst-bin count, dominated by BTC/SOL/ETH -- the
same majors reported as hit hardest in public post-mortems of that event.

The event predates the b06 walk-forward's first out-of-sample fold (it sits
inside the initial 40% training window), so it has never been scored
out-of-sample. This stage trains BASELINE and FULL on data strictly before the
event and evaluates on an Oct 7-14 2025 window, reporting:

  1. ROC-AUC / PR-AUC on the window (out-of-sample, no leakage: train cutoff
     is 3 days before the window starts).
  2. Precision/recall at top-5% score, as in b06.
  3. Lead time -- minutes between the model's first alarm (score above a
     threshold calibrated on the training set's own top-5%) and the first
     actual liquidation-burst bin of the cascade.
  4. A timeline figure: predicted probability vs. actual burst bins through
     the event, for the appendix.

Input:  data/processed/burst_panel.parquet (from b01)
Output: pipeline/outputs/b07_oct2025_case_study/

Run:
    uv run python -m pipeline.b07_oct2025_case_study
"""

from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from pipeline._report import get_output_dir, save_fig, tee_stdout
from pipeline.b01_burst_baseline import PANEL_PATH, _fit_eval, _pr_auc, _print_box, _roc_auc
from src.burst import PanelConfig

_TRAIN_CUTOFF = int(datetime(2025, 10, 7, tzinfo=UTC).timestamp())
_WINDOW_START = int(datetime(2025, 10, 9, tzinfo=UTC).timestamp())
_WINDOW_END = int(datetime(2025, 10, 14, tzinfo=UTC).timestamp())
_TOP_K_FRAC = 0.05


def _lead_time_minutes(
    bin_ts: np.ndarray, label: np.ndarray, score: np.ndarray, threshold: float
) -> float | None:
    """Minutes between the model's first alarm (score >= threshold) and the
    first actual burst bin. Positive = model fires before the cascade."""
    burst_idx = np.where(label == 1)[0]
    alarm_idx = np.where(score >= threshold)[0]
    if len(burst_idx) == 0 or len(alarm_idx) == 0:
        return None
    first_burst_ts = float(bin_ts[burst_idx[0]])
    first_alarm_ts = float(bin_ts[alarm_idx[0]])
    return (first_burst_ts - first_alarm_ts) / 60.0


def _plot_timeline(
    bin_ts: np.ndarray,
    label: np.ndarray,
    p_full: np.ndarray,
    threshold: float,
    out_dir: Path,
    asset: str,
) -> None:
    times = [datetime.fromtimestamp(t, tz=UTC) for t in bin_ts]
    fig, ax1 = plt.subplots(figsize=(11, 4.5))
    ax1.plot(times, p_full, color="steelblue", linewidth=0.8, label="full model P(burst)")
    ax1.axhline(threshold, color="gray", linestyle="--", linewidth=0.8, label="alarm threshold")
    ax1.set_ylabel("predicted P(burst)")
    burst_times = [t for t, y in zip(times, label, strict=True) if y == 1]
    for t in burst_times:
        ax1.axvline(t, color="crimson", alpha=0.15, linewidth=1.0)
    ax1.set_title(
        f"Oct 10-11 2025 liquidation event ({asset}): predicted P(burst) vs. actual burst bins (red)"
    )
    ax1.legend(loc="upper right")
    fig.autofmt_xdate()
    save_fig(fig, out_dir, "oct2025_timeline.png")


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

    train = panel.filter(pl.col("bin_ts") < _TRAIN_CUTOFF)
    window = panel.filter(
        (pl.col("bin_ts") >= _WINDOW_START) & (pl.col("bin_ts") < _WINDOW_END)
    )
    print(f"  train rows: {train.height:,} (cutoff {datetime.fromtimestamp(_TRAIN_CUTOFF, tz=UTC)})")
    print(
        f"  event window rows: {window.height:,} "
        f"({datetime.fromtimestamp(_WINDOW_START, tz=UTC)} to "
        f"{datetime.fromtimestamp(_WINDOW_END, tz=UTC)})"
    )
    print(f"  event window positive rate: {window['label'].mean():.4f}")
    print()

    base_res, p_base, _ = _fit_eval("oct2025 baseline", baseline_feats, train, window)
    full_res, p_full, full_model = _fit_eval("oct2025 full", full_feats, train, window)

    _print_box("OCT 10-11 2025 CASE STUDY: OUT-OF-SAMPLE RESULTS")
    print(f"  baseline  ROC {base_res.roc_auc:.4f}  PR {base_res.pr_auc:.4f}")
    print(f"  full      ROC {full_res.roc_auc:.4f}  PR {full_res.pr_auc:.4f}")
    print(f"  lift      ROC {full_res.roc_auc - base_res.roc_auc:+.4f}  PR {full_res.pr_auc - base_res.pr_auc:+.4f}")
    print()

    y = window["label"].to_numpy().astype(np.int8)

    k = max(1, int(len(p_full) * _TOP_K_FRAC))
    order = np.argsort(-p_full)
    top_idx = order[:k]
    precision_at_k = float(y[top_idx].mean())
    recall_at_k = float(y[top_idx].sum() / max(y.sum(), 1))
    print(f"  precision@{_TOP_K_FRAC:.0%} = {precision_at_k:.4f}   recall@{_TOP_K_FRAC:.0%} = {recall_at_k:.4f}")
    print()

    # Lead time on the single asset that dominates this event (BTC), rather
    # than a cross-asset mean, which dilutes any one asset's alarm signal.
    top_asset = (
        window.with_columns(pl.Series("_row_label", y))
        .group_by("asset")
        .agg(pl.col("_row_label").sum().alias("n"))
        .sort("n", descending=True)
        .head(1)["asset"][0]
    )
    asset_mask = (window["asset"] == top_asset).to_numpy()
    asset_ts = window["bin_ts"].to_numpy()[asset_mask]
    asset_label = y[asset_mask]
    asset_p = p_full[asset_mask]
    order_a = np.argsort(asset_ts)
    asset_ts, asset_label, asset_p = asset_ts[order_a], asset_label[order_a], asset_p[order_a]

    train_scores = full_model.predict_proba(train.select(full_feats).to_numpy())[:, 1]
    threshold = float(np.quantile(train_scores, 1 - _TOP_K_FRAC))
    lead_min = _lead_time_minutes(asset_ts, asset_label, asset_p, threshold)
    print(f"  dominant asset in event window: {top_asset} (n_burst_bins={int(asset_label.sum())})")
    print(f"  alarm threshold (train top-{_TOP_K_FRAC:.0%} score) = {threshold:.4f}")
    if lead_min is not None:
        print(
            f"  lead time on {top_asset} = {lead_min:+.0f} min "
            f"(positive = alarm before first burst bin)"
        )
    else:
        print(f"  no alarm crossed threshold on {top_asset} in this window")
    print()

    _plot_timeline(asset_ts, asset_label, asset_p, threshold, out_dir, top_asset)


def main() -> None:
    out_dir = get_output_dir("b07_oct2025_case_study")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

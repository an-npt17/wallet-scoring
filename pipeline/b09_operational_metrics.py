"""Stage B09: Operational metrics for deployment -- calibration, false
alarms/day, lead-time distribution, and notional-weighted PR.

@sec:robustness's PR-AUC/ROC-AUC summarize ranking quality but say nothing
about (a) whether the score is a calibrated probability, (b) how many false
alarms a fixed decision threshold fires per day, (c) how much warning time an
alarm gives before a cascade starts, or (d) whether big-dollar cascades are
caught preferentially over small ones. This stage answers all four from the
b06 walk-forward's pooled out-of-sample predictions
(data/processed/b06_oof.parquet), using the FULL LightGBM model's score.

  1. Calibration -- reliability diagram + Expected Calibration Error (ECE),
     10 equal-width bins.
  2. Operating point -- fix recall at _TARGET_RECALL, find the score
     threshold that achieves it on the pooled OOF set (a post-hoc reporting
     threshold, not a deployed one), then report false alarms per day.
  3. Lead time -- merge consecutive/near burst bins per asset into discrete
     burst "events", then for each event find the first alarm (score >=
     operating threshold) at or before its onset; report the distribution
     of (onset - first_alarm) in minutes.
  4. Economic (notional-weighted) PR-AUC -- average_precision_score with
     sample_weight = future_notional for positive rows (USD value of the
     cascade that follows) vs. weight 1 for negative rows, compared to the
     unweighted PR-AUC on the same predictions. Also reports notional recall
     vs. count recall at the operating threshold.

Input:  data/processed/b06_oof.parquet (written by b06_regime_robustness.py)
Output: pipeline/outputs/b09_operational_metrics/

Run:
    uv run python -m pipeline.b09_operational_metrics
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel
from sklearn.metrics import average_precision_score

from pipeline._report import get_output_dir, save_fig, tee_stdout
from pipeline.b01_burst_baseline import _print_box
from pipeline.b06_regime_robustness import OOF_PATH

_TARGET_RECALL = 0.80
_N_CALIB_BINS = 10
_EVENT_GAP_BINS = 3  # merge burst bins into one event if <= this many bins apart
_BIN_SECONDS = 300


class OperatingPoint(BaseModel):
    target_recall: float
    threshold: float
    achieved_recall: float
    precision: float
    false_alarms_per_day: float
    n_days: float


def _reliability_diagram(y: NDArray[np.int8], p: NDArray[np.float64], out_dir: Path) -> float:
    """Equal-width-bin calibration curve + ECE. Returns ECE."""
    bins = np.linspace(0.0, 1.0, _N_CALIB_BINS + 1)
    bin_idx = np.clip(np.digitize(p, bins) - 1, 0, _N_CALIB_BINS - 1)
    bin_conf = np.zeros(_N_CALIB_BINS)
    bin_acc = np.zeros(_N_CALIB_BINS)
    bin_count = np.zeros(_N_CALIB_BINS)
    for b in range(_N_CALIB_BINS):
        mask = bin_idx == b
        bin_count[b] = mask.sum()
        if mask.any():
            bin_conf[b] = p[mask].mean()
            bin_acc[b] = y[mask].mean()
    ece = float(np.sum(bin_count / len(p) * np.abs(bin_acc - bin_conf)))

    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    valid = bin_count > 0
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="perfect calibration")
    ax.plot(bin_conf[valid], bin_acc[valid], "o-", color="steelblue", label="full model")
    ax.set_xlabel("predicted P(burst)")
    ax.set_ylabel("observed burst frequency")
    ax.set_title(f"Reliability diagram (ECE = {ece:.4f})")
    ax.legend()
    save_fig(fig, out_dir, "reliability_diagram.png")
    return ece


def _operating_point(y: NDArray[np.int8], p: NDArray[np.float64], n_days: float) -> OperatingPoint:
    order = np.argsort(-p)
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    total_pos = y.sum()
    recall = tp / total_pos
    idx = min(int(np.searchsorted(recall, _TARGET_RECALL)), len(p) - 1)
    threshold = float(p[order[idx]])
    false_alarms = float(fp[idx])
    return OperatingPoint(
        target_recall=_TARGET_RECALL,
        threshold=threshold,
        achieved_recall=float(recall[idx]),
        precision=float(tp[idx] / max(tp[idx] + fp[idx], 1)),
        false_alarms_per_day=false_alarms / n_days,
        n_days=n_days,
    )


def _cluster_events(burst_ts: NDArray[np.int64], gap_bins: int) -> NDArray[np.int64]:
    """Assigns an event id to each (already time-sorted) burst bin: bins
    within `gap_bins` of the previous one join the same event."""
    event_id = np.zeros(len(burst_ts), dtype=np.int64)
    cur = 0
    for i in range(1, len(burst_ts)):
        if (burst_ts[i] - burst_ts[i - 1]) > gap_bins * _BIN_SECONDS:
            cur += 1
        event_id[i] = cur
    return event_id


def _episode_start(ts: NDArray[np.int64], alarm: NDArray[np.bool_], onset_idx: int) -> int | None:
    """Walks back from onset_idx to the nearest alarm bin at/before it, then
    further back through the contiguous run of alarm==True bins, returning
    the bin index where that alarm episode started (None if never alarmed
    before onset). Using the episode start -- not just the nearest alarm bin
    -- avoids reporting a near-zero lead time when the model has simply been
    alarming continuously in the run-up to the cascade."""
    idx = onset_idx
    while idx >= 0 and not alarm[idx]:
        idx -= 1
    if idx < 0:
        return None
    start = idx
    while start - 1 >= 0 and alarm[start - 1] and (ts[start] - ts[start - 1]) <= _BIN_SECONDS:
        start -= 1
    return start


def _lead_time_distribution(oof: pl.DataFrame, threshold: float, out_dir: Path) -> None:
    """For every discrete burst event (per asset, gap-merged), finds the
    start of the alarm episode at/before onset and plots the lead-time
    distribution (minutes, positive = early warning) for events that got
    any alarm."""
    lead_times: list[float] = []
    n_missed = 0
    n_events = 0
    for asset in sorted(oof["asset"].unique().to_list()):
        sub = oof.filter(pl.col("asset") == asset).sort("bin_ts")
        ts = sub["bin_ts"].to_numpy()
        y = sub["label"].to_numpy().astype(np.int8)
        p = sub["pred_full"].to_numpy()
        alarm = p >= threshold
        burst_ts = ts[y == 1]
        if len(burst_ts) == 0:
            continue
        event_id = _cluster_events(burst_ts, _EVENT_GAP_BINS)
        for eid in np.unique(event_id):
            n_events += 1
            onset = burst_ts[event_id == eid][0]
            onset_idx = int(np.searchsorted(ts, onset))
            start_idx = _episode_start(ts, alarm, onset_idx)
            if start_idx is None:
                n_missed += 1
                continue
            lead_times.append((onset - ts[start_idx]) / 60.0)

    lead_arr = np.array(lead_times)
    # Some "episodes" are the model sitting continuously in alarm state for
    # days before a quiet asset finally bursts -- not a discrete warning, so
    # they'd swamp the histogram. Clip display to 48h and report the clipped
    # fraction in the title instead of hiding it.
    _clip_min = 48 * 60.0
    n_clipped = int((lead_arr > _clip_min).sum())
    display = np.clip(lead_arr, None, _clip_min)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.hist(display, bins=30, color="steelblue", edgecolor="white")
    ax.axvline(0.0, color="crimson", linestyle="--", linewidth=1.0)
    ax.set_xlabel("lead time (minutes, positive = alarm before onset; clipped at 48h)")
    ax.set_ylabel("number of events")
    ax.set_title(
        f"Lead-time distribution ({len(lead_arr)}/{n_events} events alarmed, "
        f"{n_clipped} >48h clipped)"
    )
    save_fig(fig, out_dir, "lead_time_distribution.png")

    print(f"  events (gap-merged, all assets): {n_events:,}")
    print(
        f"  events with >=1 alarm before/at onset: {len(lead_arr):,} "
        f"({len(lead_arr) / max(n_events, 1):.1%})"
    )
    print(f"  events missed (no alarm fired): {n_missed:,}")
    if len(lead_arr) > 0:
        print(
            f"  lead time: mean {lead_arr.mean():+.1f} min  median {np.median(lead_arr):+.1f} min  "
            f"p10 {np.percentile(lead_arr, 10):+.1f} min  p90 {np.percentile(lead_arr, 90):+.1f} min"
        )
        print(
            f"  ({n_clipped:,} events had lead time >48h -- model sat continuously in "
            f"alarm state, not a discrete warning; mean above is tail-dominated by these, "
            f"median/p90 are the representative operational numbers)"
        )
        late = int((lead_arr <= 0).sum())
        print(f"  alarms that fired at/after onset (lead<=0): {late:,} ({late / len(lead_arr):.1%})")


def _economic_pr(
    y: NDArray[np.int8], p: NDArray[np.float64], notional: NDArray[np.float64]
) -> tuple[float, float]:
    """Notional-weighted average precision vs. the standard (unweighted) one,
    on the same OOF predictions. Weighting by raw USD notional lets a single
    multi-million-dollar cascade dominate the whole precision-recall integral
    (future_notional spans $0 to $39.5M here); log1p-compressing the weight
    keeps the "bigger cascades matter more" signal without one outlier
    determining the entire metric."""
    weight = np.where(y == 1, np.log1p(np.maximum(notional, 0.0)), 1.0)
    standard_ap = float(average_precision_score(y, p))
    economic_ap = float(average_precision_score(y, p, sample_weight=weight))
    return standard_ap, economic_ap


def _notional_vs_count_recall(
    y: NDArray[np.int8],
    p: NDArray[np.float64],
    notional: NDArray[np.float64],
    threshold: float,
) -> tuple[float, float]:
    flagged = p >= threshold
    tp = flagged & (y == 1)
    count_recall = float(tp.sum() / max(y.sum(), 1))
    total_notional = float(notional[y == 1].sum())
    caught_notional = float(notional[tp].sum())
    notional_recall = caught_notional / max(total_notional, 1.0)
    return count_recall, notional_recall


def _run(out_dir: Path) -> None:
    oof = pl.read_parquet(OOF_PATH)
    y = oof["label"].to_numpy().astype(np.int8)
    p = oof["pred_full"].to_numpy()
    notional = oof["future_notional"].to_numpy()
    n_days = (oof["bin_ts"].max() - oof["bin_ts"].min()) / 86400.0
    print(f"  pooled OOF rows: {oof.height:,}  span: {n_days:.1f} days  pos_rate: {y.mean():.4f}")
    print()

    _print_box("CALIBRATION")
    ece = _reliability_diagram(y, p, out_dir)
    print(f"  ECE (full model, {_N_CALIB_BINS} bins): {ece:.4f}")
    print()

    _print_box(f"OPERATING POINT (target recall = {_TARGET_RECALL:.0%})")
    op = _operating_point(y, p, n_days)
    print(f"  threshold: {op.threshold:.4f}")
    print(f"  achieved recall: {op.achieved_recall:.4f}   precision: {op.precision:.4f}")
    print(f"  false alarms/day: {op.false_alarms_per_day:.1f}  (over {op.n_days:.1f} days of pooled OOF)")
    n_assets = oof["asset"].n_unique()
    print(f"  false alarms/day/asset: {op.false_alarms_per_day / n_assets:.2f}  ({n_assets} assets)")
    print()

    _print_box("LEAD-TIME DISTRIBUTION")
    _lead_time_distribution(oof, op.threshold, out_dir)
    print()

    _print_box("ECONOMIC (NOTIONAL-WEIGHTED) PR-AUC")
    standard_ap, economic_ap = _economic_pr(y, p, notional)
    print(f"  standard PR-AUC: {standard_ap:.4f}")
    print(f"  economic PR-AUC (weighted by log1p(future USD notional)): {economic_ap:.4f}")
    count_recall, notional_recall = _notional_vs_count_recall(y, p, notional, op.threshold)
    print(f"  at the {_TARGET_RECALL:.0%}-recall operating point:")
    print(f"    count recall:    {count_recall:.4f}")
    print(f"    notional recall: {notional_recall:.4f}  (fraction of future USD notional caught)")
    print()


def main() -> None:
    out_dir = get_output_dir("b09_operational_metrics")
    with tee_stdout(out_dir):
        _run(out_dir)


if __name__ == "__main__":
    main()

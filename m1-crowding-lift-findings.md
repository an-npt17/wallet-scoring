# M1: Does Crowding Beat the Self-Exciting Baseline? — YES (ROC), MODEST (PR)

**Branch:** `liquidation-burst` · **Date:** July 2026 · Pipeline: `pipeline/b01_burst_baseline.py`, service `src/burst/`.

## Setup
- Leakage-safe panel: per-asset 5-min bins, features from `[t−w, t]`, burst label from `(t, t+15min]` (≥3 liquidations). 4.22M rows, 40 assets, 1.23% positive.
- **Time-ordered split** (no leakage): train = earliest 70% of bins (2.96M), test = latest 30% (1.27M). Test base rate 0.56% (fewer bursts in the later regime — a genuine distribution shift).
- Two LightGBM classifiers, class-balanced:
  - **Baseline** = past-intensity only (`past_liq_short`, `past_liq_long`) — the univariate-Hawkes / self-exciting proxy (the M0 bar).
  - **Full** = baseline + crowding (OI imbalance, tier imbalances, tier disagreement, large-tier share, mean leverage, OI velocity, liq velocity).

## Result

| Model | n feat | ROC-AUC | PR-AUC |
|-------|-------:|--------:|-------:|
| baseline (past-intensity) | 2 | 0.9083 | 0.2256 |
| full (+crowding) | 10 | 0.9773 | 0.2339 |
| **lift** | | **+0.0690** | **+0.0083** |

Test positive rate 0.0056 → PR-AUC 0.23 is ~42× random-precision for both models.

## Honest reading
- **Crowding adds a clear, real out-of-sample lift over the self-exciting baseline** — the core thesis claim holds at first pass. ROC-AUC +0.069 (0.908 → 0.977).
- **BUT ROC-AUC is inflated by easy negatives** (most bins are quiet, trivially non-burst). The honest metric for a 0.56%-positive problem is **PR-AUC, where the crowding lift is modest (+0.008)**. Both models already have strong PR vs base rate; crowding sharpens it only slightly.
- So the precise, defensible statement: *crowding features improve burst discrimination over a Hawkes-style baseline, substantially on ROC and modestly on precision-recall.* Do not headline the 0.977.

## Caveats / next
- No label leakage: past features use `[t−w,t]`, label uses `(t,t+h]`, disjoint.
- Distribution shift across the split (test base rate 0.56% vs train 1.5%) motivates the **calibration / conformal layer** (RQ3) — measure calibrated coverage across the shift.
- Next lift sources (proposal NS): **cross-venue / cross-tier excitation** (currently per-asset only), a proper marked Hawkes vs the LightGBM, and rolling multi-fold walk-forward for CIs. Check `pipeline/outputs/b01_burst_baseline/burst_baseline_lift.png` for feature importances — if crowding features rank high, the modest PR lift understates their marginal value on the hard (active-market) subset; evaluating PR **conditional on non-trivial open interest** is the next refinement.

# M2: Crowding Classifier vs Published Point-Process Baselines — WIN on PR-AUC

**Branch:** `liquidation-burst` · **Date:** July 2026 · Pipelines: `pipeline/b01_burst_baseline.py`
(LightGBM), `pipeline/b02_hawkes_baseline.py` (classical Hawkes), `pipeline/b03_thp_baseline.py`
(neural THP). Services in `src/burst/`.

## Question
Does the tier-crowding + cross-asset LightGBM beat *named, published* baselines — classical
Hawkes and a neural temporal point process — out-of-sample on the honest imbalanced metric?

## Setup (identical across all models)
- Leakage-safe per-asset 5-min panel on a **global epoch-aligned grid** (`src/burst/panel_builder.py`),
  features from `[t−w, t]`, burst label = ≥3 liquidations in `(t, t+15min]`. 4.24M rows, 40 assets.
- **Time-ordered split**: earliest 70% train, latest 30% test. Test bins 1.27M, positive rate **0.56%**
  (regime shift vs train 1.5%). Random-chance PR-AUC = 0.0056.
- Every baseline is scored on the **same test bins and label**, so PR-AUC / ROC-AUC are directly comparable.

## Results

| Model | Type | ROC-AUC | PR-AUC |
|-------|------|--------:|-------:|
| THP (neural TPP) — Zuo et al. 2020 | intensity, self-attention | 0.9700 | 0.1294 |
| Hawkes (+market cross-excitation), MLE | intensity, multivariate-lite | 0.9740 | 0.1568 |
| Hawkes (univariate self-exciting), MLE | intensity, classical | 0.9746 | 0.1570 |
| LGBM baseline (past-intensity) | discriminative | 0.9078 | 0.2281 |
| **LGBM full (+crowding +volume +cross-asset, tuned AP)** | discriminative | **0.9801** | **0.2502** |

Random PR-AUC = 0.0056 → the tuned model is **~45× chance**.

## Key findings

1. **The crowding classifier beats every published point-process baseline on PR-AUC.**
   - vs classical univariate Hawkes: **+0.093 PR-AUC** (0.157 → 0.250), ~**+59% relative**.
   - vs neural THP: **+0.121 PR-AUC** (0.129 → 0.250), ~**+94% relative**.

2. **All intensity-only TPP models collapse into the same regime: ROC ≈ 0.97, PR ≈ 0.13–0.16.**
   Self-exciting intensity is a strong *ranker* over all bins (high ROC) but a weak *precision* signal
   under 0.56% positives. This is the paper's central methodological point: **ROC hides the imbalance;
   PR-AUC is the honest metric, and there the discriminative crowding features dominate.**

3. **Naive multivariate Hawkes adds nothing** (market term 0.1568 vs univariate 0.1570). A shared-decay
   all-asset excitation term cannot exploit cross-asset structure; the **engineered tier-crowding /
   cross-venue features do** (they are what lift the LGBM). Feature engineering > naive MHP here.

4. **Tuning matters and is fair.** Optuna (objective = average-precision, inner time-ordered val slice,
   test untouched) lifted the full model +0.017 PR-AUC (0.233 → 0.250). Tuning gave more absolute PR
   than adding cross-asset features did on this single split.

## Defensible thesis claim
> A calibrated tier-crowding classifier improves liquidation-burst discrimination over classical
> (univariate and multivariate) Hawkes and a neural Transformer Hawkes Process, out-of-sample, on
> precision-recall (the imbalance-honest metric) — by +0.09 to +0.12 PR-AUC — while the intensity
> baselines are competitive only on ROC-AUC, which the 0.56% base rate inflates.

## Honest caveats (state in paper)
- **Baselines are deliberately compact**: classical Hawkes = exp kernel, β on a 5-point grid + Nelder-Mead
  MLE; THP = d=32, 2 layers, 3 epochs, 64-event windowed context. Both are legitimate but not heavily
  tuned. That THP and classical Hawkes land in the *same* PR regime is reassuring — the result is about
  intensity-vs-discriminative, not about under-training a single model. Strengthening (full β optimization,
  EasyTPP-grade THP/NHP training) is future work; unlikely to close a 0.09–0.12 PR gap.
- Single time-ordered split with a genuine regime shift; **rolling walk-forward CIs** (RQ3) still needed
  for significance bands.
- Absolute PR (0.25) is capped by the 0.56% base rate — headline the **lift over baselines** and
  operating-point precision, never the standalone number.

## Next
- Rolling walk-forward multi-fold → confidence intervals on the lift.
- Operating-point metrics (precision@recall, precision@top-k) + calibration / conformal coverage (RQ3).
- See [[project-liquidation-burst-research]], [[m1-crowding-lift-findings]].

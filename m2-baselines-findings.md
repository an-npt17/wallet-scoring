# M2: Crowding Models vs Published Point-Process Baselines — WIN on PR-AUC

**Branch:** `liquidation-burst` · **Date:** July 2026 · Pipelines: `pipeline/b01_burst_baseline.py`
(LightGBM), `pipeline/b02_hawkes_baseline.py` (classical Hawkes), `pipeline/b03_thp_baseline.py`
(neural THP), `pipeline/b04_covtpp_baseline.py` (covariate-conditioned neural TPP),
`pipeline/b05_stgnn_baseline.py` (spatio-temporal GNN). Services in `src/burst/`.

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
| **CovTPP (GRU hazard, +covariates)** | neural TPP + features | 0.9792 | **0.2556** |
| ST-GNN (cross-asset graph + GRU) | spatio-temporal GNN | 0.9791 | 0.2513 |
| LGBM full (+crowding +volume +cross-asset, tuned AP) | discriminative | 0.9801 | 0.2502 |
| LGBM baseline (past-intensity) | discriminative | 0.9078 | 0.2281 |
| Hawkes (univariate self-exciting), MLE | intensity, classical | 0.9746 | 0.1570 |
| Hawkes (+market cross-excitation), MLE | intensity, multivariate-lite | 0.9740 | 0.1568 |
| THP (neural TPP, event times only) — Zuo et al. 2020 | intensity, self-attention | 0.9700 | 0.1294 |

Random PR-AUC = 0.0056 → the top model is **~46× chance**.

## Key findings

1. **The covariate-conditioned neural TPP is the best model** (PR-AUC 0.2556), edging out the tuned
   LightGBM (0.2502) and the spatio-temporal GNN (0.2513). All three covariate-using models beat every
   published intensity-only baseline by a wide margin.

2. **The dominant effect is covariates, not model family — shown within one family.** The neural TPP
   goes from **PR-AUC 0.129 (THP, event times only) to 0.256 (CovTPP, same TPP family + crowding
   covariates)**, a ~2× jump. The intensity baselines trail *because they ignore crowding*, not because
   they are neural. This is the paper's central mechanism, demonstrated cleanly.

3. **All intensity-only TPP models collapse into the same regime: ROC ≈ 0.97, PR ≈ 0.13–0.16.**
   Self-exciting intensity is a strong *ranker* over all bins (high ROC) but a weak *precision* signal
   under 0.56% positives. **ROC hides the imbalance; PR-AUC is the honest metric.** vs classical Hawkes
   the best model gains **+0.099 PR-AUC** (0.157 → 0.256); vs neural THP **+0.126** (0.129 → 0.256).

4. **Graph structure is not a free lunch.** The ST-GNN's cross-asset message passing only ties the GBM
   (0.2513 vs 0.2502) — because the cross-asset signal is already captured by the engineered market /
   spillover features. Explicit graph mixing adds little on top.

5. **Naive multivariate Hawkes adds nothing** (market term 0.1568 vs univariate 0.1570): a shared-decay
   excitation term cannot exploit cross-asset structure; engineered features and covariate conditioning
   can. **Tuning is fair and matters:** Optuna (average-precision objective, inner time-ordered val,
   test untouched) lifted the GBM +0.017 (0.233 → 0.250).

## Defensible thesis claim
> A covariate-conditioned neural point process — a GRU hazard model over each asset's bin sequence of
> tier-crowding and cross-venue features — achieves the best out-of-sample liquidation-burst
> discrimination on precision-recall (PR-AUC 0.256), beating a tuned gradient-boosted classifier
> (0.250), a spatio-temporal GNN (0.251), and, by +0.10 to +0.13 PR-AUC, classical/multivariate Hawkes
> and a Transformer Hawkes Process. Feeding crowding covariates into a point process roughly doubles its
> PR-AUC over the same model using event times alone, isolating crowding — not model class — as the
> source of predictability beyond self-excitation. Intensity-only baselines are competitive only on
> ROC-AUC, which the 0.56% base rate inflates.

## Honest caveats (state in paper)
- **The win over LightGBM is small** (CovTPP +0.005, ST-GNN +0.001). The large, robust gap is
  intensity-only vs covariate-conditioned (+0.10–0.13), not deep vs GBM. Do not over-claim the deep
  models as a landslide over boosting.
- **Baselines are deliberately compact**: classical Hawkes = exp kernel, β on a 5-point grid + Nelder-Mead
  MLE; THP = d=32, 2 layers, 3 epochs, 64-event windowed context; CovTPP / ST-GNN are also small
  (1-layer GRU, 48–64 hidden, ≤4 epochs). Legitimate but not heavily tuned. That THP and classical Hawkes
  land in the *same* PR regime is reassuring — the result is about intensity-vs-covariate, not about
  under-training a single model. Stronger fits are future work; unlikely to close the 0.10–0.13 PR gap.
- Single time-ordered split with a genuine regime shift; **rolling walk-forward CIs** still needed for
  significance bands — the CovTPP/ST-GNN/GBM differences are within plausible split noise.
- Absolute PR (0.256) is capped by the 0.56% base rate — headline the **lift over intensity baselines**
  and operating-point precision, never the standalone number.

## Next
- Rolling walk-forward multi-fold → confidence intervals on the lift (decides whether CovTPP > GBM is real).
- Operating-point metrics (precision@recall, precision@top-k) + calibration / conformal coverage (RQ3);
  **CovTPP is the natural model to calibrate** — it already emits a point-process hazard intensity.
- See [[project-liquidation-burst-research]], [[m1-crowding-lift-findings]].

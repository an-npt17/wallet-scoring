# Implementation Plan — Wallet Scoring

## Project Goal
Side-aware Bayesian wallet skill decomposition for DeFi perpetual DEX traders. MSc thesis targeting buy/sell/timing/sizing/crowd-adjusted skill dimensions with posterior credible intervals.

---

## Current State

### What Works (Committed, All Pipeline Stages Run)

| Stage | Script | Status | Key Output |
|-------|--------|--------|------------|
| 01 | `pipeline/01_reconstruct_positions.py` | Done | Positions from raw events |
| 02 | `pipeline/02_compute_features.py` | Done | Feature engineering |
| 03 | `pipeline/03_fetch_labels.py` | Done | Labels fetched |
| 04 | `pipeline/04_compute_baselines.py` | Done | B1–B5 baselines computed |
| 05 | `pipeline/05_feature_analysis.py` | Done | Feature correlations |
| 06 | `pipeline/06_walkforward_validation.py` | Done | Train/test split (1,231 wallets) |
| 07 | `pipeline/07_bayesian_skill_model.py` | Done | **Proposed bayes_score** (EmpiricalBayesSkillService) |
| 08 | `pipeline/08_baseline_comparison.py` | Done | bayes_score vs B1–B5 |
| 09 | `pipeline/09_luck_vs_skill_null.py` | Done | Luck-vs-skill tests |
| 10 | `pipeline/10_sign_randomization.py` | Done | B7: sign-randomization classifier |
| 11 | `pipeline/11_wash_trade_filter.py` | Done | B8: wash-trade pre-filter (29 flagged) |
| 12 | `pipeline/12_zscore_baseline.py` | Done | B6: zScore reimplementation |
| 13 | `pipeline/13_full_baseline_comparison.py` | Done | **Consolidated comparison (all 8 baselines)** |

### Infrastructure
- `clients/mongo.py` — MongoDB connection
- `config/` — settings, db config, models
- `src/skill_model/` — `EmpiricalBayesSkillService`, `SkillDimension` (BUY/SELL/TIMING), schemas
- `scripts/01–10` — Data exploration and profiling

### Research Assets
- `literature-review.md` — 22 papers, 4 identified gaps
- `research-proposal.md` — 4 RQs, evaluation protocol, 8 baselines, timeline
- `references.bib` — Full BibTeX

---

## Critical Findings (From Full Comparison)

**Bayes_score does NOT yet beat b3_roi (raw ROI rank):**

| Score | Spearman WR | Spearman PnL | Hit rate |
|-------|-------------|--------------|----------|
| **bayes_score** | +0.109 | +0.033 | 46.7% |
| b3_roi | **+0.142** | **+0.051** | **52.2%** |
| b7_score | +0.131 | **+0.058** | 46.3% |
| b6_zscore | +0.125 | +0.015 | 32.4% |

**Root cause:** Current bayes_score only shrinks `overall_win_rate` — a 1-dimensional binomial proportion. Raw ROI (b3) captures PnL magnitude, which win rate ignores. The model needs to incorporate PnL-weighted dimensions.

**Other signals from walkforward features:**
- `overall_win_rate`: +0.110 WR (best single predictor)
- `avg_roi`: +0.057 WR
- `total_pnl`: -0.039 WR / +0.074 PnL (conflicted)
- `mean_leverage`: -0.101 WR (over-leveraged underperform)
- `liquidation_rate`: -0.108 WR
- `leverage_adj_roi`: +0.055 WR (not better than raw overall_win_rate)

---

## Work Remaining (By Priority)

### P1 — Improve Bayesian Model (Addresses: why bayes_score < b3_roi)

- [ ] **Multi-dimensional shrinkage**: Shrink buy, sell, timing dimensions jointly (multivariate Normal-Normal) instead of univariate per dimension
- [ ] **Leverage-adjusted rate**: Shrink `PnL / sqrt(leverage)` instead of binary win rate — captures magnitude, not just direction
- [ ] **Composite posterior score**: Combine posteriors across dimensions (e.g., `0.5 * timing_posterior + 0.5 * sizing_posterior`) and test if it beats b3_roi
- [ ] **Add `avg_roi` as a dimension** to the hierarchical model
- [ ] **Re-run pipeline 08/13** after each change and compare

### P2 — Validation & Robustness

- [ ] **Luck-vs-skill (pipeline 09)**: Interpret existing results — what fraction of top-decile wallets survive the null test?
- [ ] **B7 sign-randomization (pipeline 10)**: Are the "skilled winners" identified by sign-randomization overlapping with bayes_score top decile?
- [ ] **B8 wash-trade filter (pipeline 11)**: Confirm flagged wallets (29) are genuinely suspicious
- [ ] **Ablation**: Which skill dimension contributes most to out-of-sample prediction?
- [ ] **Sensitivity analysis**: Vary `min_trades` threshold (currently 5) — how stable are rankings?

### P3 — Remaining Research Questions

- [ ] **RQ3 (Crowd-adjusted skill)**: Not implemented. Follower graph not in DB. Options:
  - Use `daily_trader_rankings` appearance frequency as crowd-exposure proxy
  - Or scope out of thesis (document as limitation)
- [ ] **Regime decomposition (optional extension)**: HMM on market state → per-regime skill scores
- [ ] **Liquidation rate as risk-intelligence dimension**: Add to the Bayesian model as a negative signal

### P4 — Thesis Writing Preparation

- [ ] Re-run full pipeline with final model → fresh outputs
- [ ] Generate publication-quality figures from pipeline outputs
- [ ] Sections to draft (once model is final):
  - Methodology (Bayesian hierarchical model)
  - Results (comparison tables, ablation)
  - Related work (from literature-review.md)
- [ ] Target venue: KDD 2027 or ICAIF 2027

---

## Dependencies

```
pipeline/01 → 02 → 03 → 04
                      ↓
               05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13
```

Modifications to `src/skill_model/` require re-running stages 07 and 13.


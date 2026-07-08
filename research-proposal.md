# Research Proposal: Tier-Aware Crowding and Calibrated Early Warning of Synchronized Liquidation Bursts in On-Chain Perpetual Futures

**Branch:** `liquidation-burst` · **Date:** July 2026 · **Target venues:** ICAIF 2027, KDD 2027 (Applied Data Science), or ACM AFT / ML-for-finance workshops.

______________________________________________________________________

## 1. Overview (5W1H)

> **M0 status (July 2026, locked).** Two feasibility probes were run before committing. (1) The liquidation-**magnet** hypothesis (price attracted to liquidation-price walls) was **rejected** on BTC/SOL/ETH, two test forms, all null (`m0-magnet-findings.md`) — **dropped as a claim**; the wall map is retained only as a candidate feature. (2) The liquidation-**burst label** **passed**: dense and strongly learnable (`m0-burst-findings.md`). **Locked primary label: h = 15 min, threshold ≥ 3 liquidations** (3.8% base rate, 52,182 positives). **Baseline to beat: past-intensity / univariate Hawkes**, which alone already reaches AUC ≈ 0.83–0.87 — so the contribution is *lift over the self-exciting baseline*, not mere burst predictability.

- **What.** Forecast *synchronized liquidation bursts* — short windows in which many perpetual-futures positions on an asset are force-closed together — and issue *calibrated* early warnings with quantified lead time.
- **Why.** Liquidation cascades are the primary systemic risk of leveraged crypto venues; existing signals (funding rate, open interest, long/short ratio) are heuristic thresholds, not calibrated predictive models. A calibrated warning is both a risk product and a scientific test of cascade contagion.
- **Who.** Exchange risk desks, market makers, on-chain risk dashboards, and market-surveillance / systemic-risk researchers.
- **When / Where.** On-chain perp data across 5 venues (Hyperliquid, Jupiter, GMX-v2, APX, Myx) and 5 chains, 491 days (2025-02-19 → 2026-06-26).
- **How.** Tier-aware crowding + co-positioning-graph features → marked/multivariate self-exciting point process with covariate-modulated intensity → adaptive-conformal calibration → time-ordered, per-venue evaluation by lead time, PR-AUC, and calibration.

______________________________________________________________________

## 2. Research Questions

**RQ1 (Features).** Do *tier-resolved* crowding features (small-vs-large disagreement, tier long/short imbalance, positioning concentration, consensus velocity) and co-positioning-graph features improve prediction of synchronized liquidation bursts over (a) the practitioner funding/imbalance heuristic and (b) standard learners on naive size/OI features?

**RQ2 (Contagion model).** Does a *marked, covariate-modulated* self-exciting point process with **cross-tier and cross-venue excitation** predict bursts better than (a) an independent-asset univariate Hawkes and (b) the published multivariate-Hawkes baseline [Cao & Palaash, 2025] adapted to perps?

**RQ3 (Calibration under shift).** Can adaptive conformal prediction maintain target coverage of the burst-probability early warning across market regimes, improving the lead-time / false-alarm tradeoff versus static calibration?

Each RQ is falsifiable and measured against explicit baselines (§6–7).

______________________________________________________________________

## 3. Data and Label Construction (grounded in verified schema)

**Source collections** (`database/mongo/schema.py`): `logs` (40.5M Open/Close events with `size_usd`, `side`, `leverage`, `owner_account`, `asset`, `platform`, `timestamp`), `closed_positions` (1.34M, `realizedPnl`, `lastClosedAt`), `opening_positions` (live open state, `unrealizedPnl`), `aggregated_assets` (market-wide small/medium/large tier long/short size & count snapshot), `market_stats` (`whaleBehavior`, whale dominance, risk-appetite flow). Verified facts: **190,583 explicit `Liquidate` close events**, 533,274 positions with ≥1 liquidation, 249 assets, 5 platforms.

**Burst label (self-supervised, reliable).** For asset $a$ and time bin $t$ (e.g. 5-min), let $L\_{a,t}$ = count of liquidation/forced-close events. Define a burst indicator
$$
Y^{(h)}_{a,t} = \\mathbf{1}!\\left\[\\ \\sum_{\\tau \\in (t,,t+h\]} L\_{a,\\tau}\\ \\ge\\ Q\_{a}(1-\\alpha)\\ \\right\],
$$
with absolute threshold $\theta$ and horizon $h$. **M0 locked the primary operating point at $h = 15$ min, $\theta = 3$** (pooled base rate 3.8%, 52,182 positives); secondary $h = 60$ min, $\theta \ge 5$ (7.9%, 108,807 positives). An absolute threshold is preferred over an asset-quantile $Q_a(1-\alpha)$, which would fix the base rate by construction; the absolute threshold lets base rate track genuine activity. M0 confirmed the label is dense and **strongly learnable — a single past-intensity feature already gives AUC 0.83–0.87** (`m0-burst-findings.md`) — so the modelling target is *incremental lift over the self-exciting baseline*, not mere burst predictability.

**Strict leakage control.** All features for prediction at time $t$ are computed from the window $[t-w, t]$; the label uses $(t, t+h\]$. No random splitting: evaluation is time-ordered rolling-origin walk-forward (reusing the Stage-15 machinery already built), with a purge/embargo gap of $h$ between train and test to prevent horizon leakage.

______________________________________________________________________

## 4. Feature Engineering

Reconstructed per asset (and per venue) from the `logs` event stream on rolling windows:

1. **Tier crowding.** Classify wallets into small/medium/large tiers (by trailing size percentiles; validated against the `aggregated_assets` tier definitions). Per tier: long/short size imbalance, count imbalance, dominant-side flips.
1. **Small-vs-large disagreement.** Signed divergence between small- and large-tier net positioning — informed-vs-uninformed flow proxy.
1. **Positioning concentration.** Herfindahl–Hirschman index of open size across wallets; share of open interest in the top-$k$ wallets.
1. **Consensus velocity.** First/second differences of net imbalance and concentration — is crowding *accelerating*?
1. **Leverage stress.** Distribution of `leverage` among currently-open positions; fraction near liquidation-price bands (proxied from entry price, side, leverage).
1. **Co-positioning-graph topology (ablation).** Build a graph where wallets sharing (asset, side, time-window) are linked; extract centrality and persistent-homology summaries (Betti-0/1, persistence velocity) of the crowd. Honest caveat: this is a constructed graph, not a transfer graph.
1. **Event-time clock.** Funding-window phase (hourly / 8-hourly known times) as cyclical features — funding *rate* is unobserved, only its *clock* is used.

______________________________________________________________________

## 5. Model

**Notation.** Marked point process with events ${(t_i, k_i)}$, mark $k_i = (\\text{tier}, \\text{asset}, \\text{venue})$. Conditional intensity for mark $k$:
$$
\\lambda_k(t) ;=; \\underbrace{\\mu_k\\big(x\_{k}(t)\\big)}_{\\text{crowding-modulated baseline}} ;+; \\sum_{k'} \\sum\_{t_j < t} \\alpha\_{k' \\to k}, \\phi!\\left(t - t_j\\right),
$$
where $x_k(t)$ is the crowding/graph feature vector (baseline intensity is a link function, e.g. softplus, of features), $\\phi$ is an exponential (or power-law) triggering kernel, and $\\alpha\_{k'\\to k}$ is the cross-mark excitation matrix capturing **cross-tier and cross-venue contagion**. Fit by maximum likelihood (penalized for the excitation matrix); the crowding-modulated baseline is the novel component versus a plain Hawkes.

**Variants.** (i) Parametric marked Hawkes (primary); (ii) neural-intensity variant (RNN/transformer conditional intensity) as a stretch extension benchmarked against (i); (iii) a discriminative alternative — gradient-boosted classifier on the same features predicting $Y^{(h)}\_{a,t}$ — as both a baseline and a deployable simple model.

**Calibration layer.** Wrap the burst-probability output in **Adaptive Conformal Inference** [Gibbs & Candès 2021; Zaffran et al. 2022] to maintain target coverage online under regime shift (RQ3).

______________________________________________________________________

## 6. Baselines (all reproducible; contrast with prior project's broken B1–B8)

| Baseline | Type | Effort |
|----------|------|--------|
| Base rate / always-alarm-above-threshold | trivial | one-liner |
| **Funding/imbalance heuristic** (crowding > τ) | practitioner signal | low |
| Logistic regression on features | standard | low |
| **Gradient boosting (LightGBM)** on features | standard, strong | low (installed) |
| **Past-intensity / univariate Hawkes** — *the bar to beat (M0: AUC ≈ 0.83–0.87)* | point-process | moderate (MLE / `tick`) |
| **Multivariate Hawkes** [Cao & Palaash 2025], adapted to perps | published SOTA-adjacent | moderate (reimplement from description) |
| Static (split) conformal vs adaptive conformal | calibration | low |

Only the multivariate-Hawkes and the parametric self-exciting fit require real effort; everything else is a `scikit-learn` / `lightgbm` call on self-contained data. No external dataset or unreleased code is required — a decisive contrast to the prior project's dependence on reproducing eight published wallet scores.

______________________________________________________________________

## 7. Evaluation Protocol

- **Splitting.** Rolling-origin walk-forward, time-ordered, per-venue holdout, purge/embargo = $h$. Report mean ± std across folds (reuse Stage-15 code).
- **Discrimination.** PR-AUC and ROC-AUC (PR-AUC primary due to class imbalance); precision at fixed recall.
- **Early-warning utility.** Lead-time distribution (how early before the burst the alarm fires) vs false-alarm rate; alarm-precision at operational thresholds.
- **Calibration.** Reliability diagrams, Brier score, empirical coverage of conformal intervals vs nominal, across regimes.
- **Contagion evidence.** Estimated branching ratio and cross-mark excitation matrix $\\alpha\_{k'\\to k}$ (interpretable output for RQ2).
- **Ablations.** Remove tier features / graph features / cross-venue excitation / calibration layer, each independently.

______________________________________________________________________

## 8. Feasibility, Risks, and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Label base rate too rare/common** at chosen $(h,\\alpha)$ | High | M0 grid over $(h,\\alpha)$; pick balance ~5–20% positive; report sensitivity |
| Leakage between features and horizon label | High | Strict $[t-w,t]$ / $(t,t+h\]$ split + embargo $h$ |
| Co-positioning graph weaker than transfer graph | Medium | Carry as ablation, not core claim (stated in review) |
| No funding-rate data | Medium | Use funding *clock* only; do not claim funding-rate modeling |
| `aggregated_assets` is a snapshot | Low | Rebuild crowding time series from `logs`; use snapshot only to validate tiers |
| Cross-venue timestamps mis-aligned | Medium | Normalize to UTC epoch; per-venue models first, then joint |
| Multivariate Hawkes MLE unstable at 249 assets × 3 tiers × 5 venues | Medium | Restrict marks to top-K assets by liquidation volume; regularize $\\alpha$ |

______________________________________________________________________

## 9. Timeline (indicative, ~6 months)

- **M0 (Weeks 1–2):** Label feasibility — burst base rates over $(h,\\alpha)$ grid; confirm learnability; lock label definition.
- **M1 (Weeks 3–5):** Feature pipeline (tier crowding, concentration, velocity) from `logs`; leakage-safe windowing on Stage-15 walk-forward.
- **M2 (Weeks 6–8):** Baselines — heuristic, logistic, LightGBM, univariate Hawkes; first PR-AUC / lead-time numbers.
- **M3 (Weeks 9–12):** Marked covariate-modulated Hawkes with cross-tier/cross-venue excitation (RQ2); multivariate-Hawkes baseline reimplementation.
- **M4 (Weeks 13–15):** Adaptive-conformal calibration layer (RQ3); calibration + lead-time/false-alarm evaluation across regimes.
- **M5 (Weeks 16–18):** Graph-topology ablation (RQ1 add-on); neural-intensity stretch variant if time permits.
- **M6 (Weeks 19–24):** Full ablations, robustness, writing; submit to ICAIF/KDD-ADS or AFT.

______________________________________________________________________

## 10. Expected Contributions

1. The first **perp, tier-marked, crowding-modulated self-exciting model** of synchronized liquidation bursts (G1, G3).
1. A **calibrated, drift-aware early-warning system** with lead-time / false-alarm benchmarks, beating heuristic funding/imbalance signals (G2, G4).
1. An **open, reproducible benchmark** for on-chain liquidation-burst forecasting with self-supervised event-count labels (contrast to noise-limited wallet-skill labels).
1. Honest evidence on whether **co-positioning-graph topology** adds predictive value when a native transaction graph is unavailable (G5).

______________________________________________________________________

## 11. Status and Next Step

**M0 complete (both gates):** magnet rejected (`m0-magnet-findings.md`), burst label passed and locked at $h=15$ min, $\theta=3$ (`m0-burst-findings.md`). **Now M1:** leakage-safe feature panel (per-asset 5-min bins; past-window tier-crowding / imbalance / concentration / leverage-stress features vs future-window burst label) on a time-ordered split, and the first measurement of **lift over the past-intensity self-exciting baseline** (AUC ≈ 0.83–0.87). Implemented in `pipeline/b01_burst_baseline.py`.

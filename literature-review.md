# Literature Review: Tier-Aware Crowding and Early Warning of Synchronized Liquidation Bursts in On-Chain Perpetual Futures

**Branch:** `liquidation-burst` · **Date:** July 2026 · **Author:** MSc Computer Science Thesis

> Scope note. This review was assembled via WebSearch (Zotero MCP was unavailable in
> this session). arXiv IDs and venues are recorded in `references.bib`; entries added
> in the last search pass (2025–2026 preprints) are flagged there as requiring
> author/DOI verification before camera-ready.

---

## 1. Motivation and Problem Setting

Perpetual futures ("perps") are the dominant crypto derivative, with daily volume regularly exceeding \$100B, and are increasingly the venue where *price discovery* happens (spot follows perps). Their defining risk is the **liquidation cascade**: once a cluster of leveraged positions breaches maintenance margin, forced liquidations sell into the market, push price further, and trip the next layer of leveraged positions — a self-exciting, contagious unwind. Practitioners already treat crowded positioning (extreme funding rates, long/short imbalance, record open interest) as informal early-warning signals, but these are heuristic thresholds ("funding > 15% APR"), not calibrated predictive models.

This thesis proposes to (a) engineer **tier-aware crowding and co-positioning-graph features** from on-chain perp event streams, (b) forecast **synchronized liquidation bursts** with a **marked/multivariate self-exciting point process** whose intensity is modulated by those features, and (c) deliver **calibrated, drift-aware early warnings** using adaptive conformal prediction. The available database (`perpetuals_knowledge_graph`) records 1.34M closed positions across 249 assets and 5 venues over 491 days, with 190,583 explicit `Liquidate` events — a dense, self-supervised label source, in contrast to the noise-dominated win-rate labels that limited the prior wallet-scoring effort.

Five literature pillars support the design.

---

## 2. Pillar 1 — Liquidation Cascades and Self-Exciting Dynamics

Self-exciting (Hawkes) processes are the canonical model for event contagion in finance: the arrival of one event transiently raises the intensity of further events via an (often exponential) triggering kernel [Bacry et al., 2015]. Reflexivity — the degree to which market activity is endogenously self-generated rather than driven by exogenous news — has been quantified through the branching ratio of Hawkes fits and proposed as a flash-crash precursor [Filimonov & Sornette, 2012].

Directly adjacent, **Cao & Palaash (2025)** fit a **3-variate Hawkes process to cross-protocol DeFi liquidation clustering** (Aave V3, Compound V3, Morpho), estimating exponential triggering kernels via MLE on ~7,500 on-chain liquidation events (2023–2025). This is the closest prior work and the primary methodological baseline to beat. **Crucially, it differs from this thesis on three axes**: (i) it models *DeFi lending* liquidations (collateral health-factor breaches), not *perpetual-futures* margin liquidations; (ii) events are aggregated at the *protocol* level, with no wallet-tier structure or positioning covariates; and (iii) it is a *descriptive* clustering model, not a *calibrated predictive* early-warning system evaluated by lead time / false alarms. A modulated-renewal Hawkes variant has also been applied to extreme mid-price drops on cryptocurrencies [UNSW thesis], and Markov-modulated Hawkes to high-frequency manipulation detection [arXiv:2502.04027], confirming that regime-switching intensities matter in this domain.

**Takeaway.** The Hawkes family is the correct mechanistic prior, and a strong published baseline exists — but no one has fit a *perp*, *tier-marked*, *covariate-modulated* liquidation point process.

---

## 3. Pillar 2 — Perp Microstructure, Crowding, and Funding as Early-Warning Signals

Microstructure work frames the cascade mechanism precisely: crowding thins the market's "error bars," so a modest (1–5%) adverse move breaches maintenance margins, and forced market orders deepen the move and trigger the next layer [perp-microstructure practitioner literature, 2026]. Funding rates and open interest are the standard crowding proxies; Granger-causality studies report that *extreme* funding has predictive value for subsequent moves, and the recent **Slippage-at-Risk (SaR)** framework [arXiv:2603.09164] builds a *forward-looking* liquidity-risk measure for perp exchanges.

**Gap for this thesis.** These signals are venue-level, funding-rate-dependent, and heuristic. The `perpetuals_knowledge_graph` schema exposes something richer and finer: per-event `size_usd`, `side`, `leverage`, `owner_account`, and timestamp in `logs`, plus a market-wide `aggregated_assets` snapshot that already defines **small/medium/large wallet tiers** with long/short size and count percentages. This permits *tier-resolved* crowding features (small-vs-large disagreement, tier imbalance, positioning concentration, consensus velocity) that funding rate alone cannot express. Note two schema constraints, addressed in the proposal: (i) `aggregated_assets` is a *snapshot* (no timestamp), so the crowding *time series* must be reconstructed from `logs`; (ii) **no funding-rate field exists**, so funding enters only as a known *event-time clock* (hourly / 8-hourly windows), not an observed covariate.

---

## 4. Pillar 3 — Marked and Neural Point Processes

Beyond parametric Hawkes, neural point processes learn flexible conditional-intensity functions with RNNs, transformers, and state-space models [neural STPP, Zhou et al., 2022; Transformer/Mamba Hawkes, arXiv:2407.05302], and recent work targets *multi-event* forecasting on spatiotemporal point processes [Beyond Hawkes, arXiv:2211.02922]. Marks (event covariates such as wallet tier, asset, venue) let a single process model heterogeneous events and cross-type excitation.

**Relevance.** The proposed model treats each liquidation as a *marked* event (mark = wallet tier × asset × venue), enabling cross-tier and cross-venue excitation — e.g. large-wallet liquidations exciting small-wallet liquidations, or Hyperliquid unwinds exciting Jupiter unwinds. Parametric marked Hawkes is the primary model; a neural-intensity variant is a stretch extension, benchmarked against it rather than assumed superior.

---

## 5. Pillar 4 — Topology of On-Chain Transaction / Positioning Graphs

Topological Data Analysis (TDA) on dynamic blockchain networks captures structural change (connected components, loops, higher-order voids) that precedes price anomalies. Persistent-homology methods detect anomalies in dynamic multilayer blockchain networks [Ofori-Boateng et al., 2021], predict extreme **XRP price surges from topological features** [arXiv:2603.18021], and a **hierarchical persistence-velocity** method targets crypto-market network anomalies [arXiv:2512.14615].

**Caveat honestly stated.** These works use *native transaction graphs* (address-to-address transfers). This database has **no counterparty edges** — perp positions are wallet-vs-protocol. Therefore this thesis constructs a **co-positioning graph** (wallets sharing asset + side + time window form edges) and extracts centrality / persistence features of the *crowd's* structure. This is a weaker topological object than a transfer graph, so graph features are proposed as an *ablation-tested add-on*, not the core claim — the review is explicit that the TDA-on-transaction-graph novelty does not transfer wholesale.

---

## 6. Pillar 5 — Calibrated Prediction Under Distribution Shift

Real-time early warning must stay calibrated as regimes change. **Adaptive Conformal Inference** [Gibbs & Candès, 2021] updates the miscoverage level online — widening intervals after a miss, narrowing after a hit — to control long-run coverage under distribution shift without modeling the shift. **Adaptive Conformal Predictions for Time Series** [Zaffran et al., 2022] extends this to dependent series, and drift-aware / spectral variants handle non-exchangeable streaming data [arXiv:2606.15953]. Conformal anomaly detection with time-series foundation models has also emerged [arXiv:2604.20122].

**Relevance.** A liquidation-burst warning is only actionable if its probability is *calibrated* and stays calibrated across bull/bear/chop regimes. Wrapping the point-process (or classifier) output in adaptive conformal gives calibrated alarm intervals and a principled lead-time / false-alarm tradeoff — a contribution orthogonal to, and stackable on, the intensity model.

---

## 7. Synthesis and Identified Gaps

| # | Gap | Evidence it is open |
|---|-----|---------------------|
| **G1** | No **tier-structured, covariate-modulated** liquidation point process for **perps** | Cao & Palaash (2025) is protocol-level DeFi-lending, descriptive, no tiers/covariates |
| **G2** | Crowding early-warning is **heuristic** (funding/OI thresholds), not a **calibrated predictive model** | Funding-rate signals are Granger-causal heuristics; SaR is liquidity-risk, not burst prediction |
| **G3** | **Cross-tier / cross-venue excitation** of liquidation bursts is unstudied | Hawkes-finance work is single-asset or single-protocol |
| **G4** | No **calibrated, drift-aware** early-warning with lead-time / false-alarm benchmarks in this domain | ACI/time-series conformal exist but are unapplied to on-chain liquidation bursts |
| **G5** | Positioning-**graph topology** as intensity covariate is unexplored (with honest limits) | TDA-on-blockchain uses transfer graphs; co-positioning graph is novel but weaker |

**Positioning.** The thesis's defensible core is **G1 + G2 + G4**: a perp, tier-marked, crowding-modulated self-exciting model delivering *calibrated* liquidation-burst early warnings, benchmarked against (i) the practitioner funding/imbalance heuristic, (ii) standard learners (logistic, gradient boosting), and (iii) the published multivariate-Hawkes baseline adapted to perps. G3 and G5 are higher-risk extensions carried as ablations.

**Why this fits the data (and avoids the prior project's failure).** The prior wallet-scoring work collapsed because its evaluation label (future win rate) was ~99% sampling noise. The label here — a synchronized liquidation/close burst in the next 5/15/60 minutes — is an **event count**, dense (190k liquidations) and self-supervised, so measurable model improvement is achievable and reviewer-defensible.

---

## 8. Key References (full entries in `references.bib`)

- Bacry, Mastromatteo, Muzy (2015) — *Hawkes processes in finance*.
- Filimonov & Sornette (2012) — *Quantifying reflexivity … prediction of flash crashes*.
- Cao & Palaash (2025) — *DeFi liquidations cluster across protocols: a multivariate Hawkes framework* (closest prior work / primary baseline).
- Zhou et al. (2022) — *Neural point process for spatiotemporal event dynamics*; *Beyond Hawkes* (2022).
- Ofori-Boateng et al. (2021) — *Topological anomaly detection in dynamic multilayer blockchain networks*; XRP topological anomaly prediction (2026).
- Gibbs & Candès (2021) — *Adaptive conformal inference under distribution shift*; Zaffran et al. (2022) — *Adaptive conformal predictions for time series*.
- Slippage-at-Risk (2026); Markov-modulated Hawkes manipulation detection (2025).

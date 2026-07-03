# Research Proposal: Side-Aware Bayesian Wallet Skill Decomposition for DeFi Copy Trading

**Date:** 2026-07-02\
**Program:** MSc Computer Science – Thesis\
**Related collection:** Research-WalletScoring-2026-07 (Zotero)

______________________________________________________________________

## 1. Problem Statement

Existing crypto wallet scoring systems rank wallets by a single composite score—typically realized PnL, win rate, or Sharpe ratio. This design conflates at least four orthogonal dimensions of trading edge that the traditional finance literature treats as distinct:

1. **Buy skill**: ability to enter positions with positive expected return
1. **Sell skill**: ability to exit positions to maximize realized gain (not just unrealized)
1. **Timing skill**: hit ratio—fraction of directionally correct decisions
1. **Sizing skill**: win/loss ratio—whether position sizes are larger on winning trades
1. **Crowd-adjusted skill**: alpha above the synchronized behavior of followers and copiers

The finance literature shows that buy and sell skill are orthogonal—selling skill is the primary driver of aggregate performance, not buying skill (Lim et al., 2022). Timing and sizing decompose the information ratio into two separately estimable components, with timing being approximately twice as informative (Van Loon, 2018). Meanwhile, in heavy-tailed environments like crypto, historical performance is largely indistinguishable from random luck without Bayesian uncertainty quantification (Kosowski et al., 2006; Choi et al., 2025).

No published wallet scoring system for DeFi or CEX copy trading addresses any of these three issues. The result is that copy-trading platforms surface wallets by luck-contaminated PnL, assign equal confidence to a 5-trade wallet and a 500-trade wallet, and ignore the decay of edge as a wallet becomes widely copied.

**This proposal defines a framework for side-aware, Bayesian, crowd-adjusted wallet skill decomposition.**

______________________________________________________________________

## 2. Research Questions

**RQ1 (Decomposition):** Can buy-side skill and sell-side skill be separately identified for on-chain crypto wallets, and are they empirically orthogonal (low correlation)?

**RQ2 (Uncertainty):** Can a Bayesian hierarchical model produce reliable posterior skill distributions with calibrated credible intervals for each skill dimension, given the short trade histories typical of active DeFi wallets?

**RQ3 (Crowd adjustment):** Does a wallet's future copy-trader return diminish as its follower count grows, and can a crowd-decay function be estimated to produce a copy-adjusted expected value?

**RQ4 (Validation):** Does a multi-dimensional skill score outperform single-score baselines in predicting future copy-trader returns, measured at 7-day, 30-day, and 90-day horizons on Solana and EVM chains?

______________________________________________________________________

## 3. Proposed Framework

### 3.1 Skill Dimensions

For each wallet *w* with trade history up to time *t*, define:

**Buy skill** $s^{\\text{buy}}\_w$: risk-adjusted excess return on entry decisions.\
Operationalization: for each buy transaction, compute forward return over a standardized holding window (24h, 7d, 30d). Benchmark: average token return over the same window. Buy alpha = mean(wallet forward return) − mean(token forward return), risk-adjusted by volatility.

**Sell skill** $s^{\\text{sell}}\_w$: risk-adjusted alpha on exit decisions vs. two benchmarks:\
(a) immediate exit at time of buy (opportunity cost benchmark)\
(b) mean exit timing across all wallets for the same token\
Operationalization: for each sell, compute realized return vs. (a) and (b). Sell alpha = mean(realized − benchmark).

**Timing skill** $\\tau_w$: hit ratio of directionally correct entry decisions.\
Operationalization: $\\tau_w = \\frac{1}{N} \\sum\_{i=1}^{N} \\mathbf{1}\[\\text{price}_{t_i+H} > \\text{price}_{t_i}\]$ where $H$ is a fixed horizon.

**Sizing skill** $\\sigma_w$: win/loss ratio conditioned on position size.\
Operationalization: split trades into above/below median size for that wallet; compute separate alpha for each group; sizing skill = (large-position alpha) − (small-position alpha).

**Crowd-adjusted skill** $\\kappa_w$: alpha net of the synchronized crowd.\
Operationalization: identify follower-set $F_w$ of wallets that copy *w* within $\\Delta t$ blocks. Crowd-return = mean return of copycat trades. Crowd-adjusted alpha = $s^{\\text{buy}}_w - \\text{return}_{\\text{crowd}}$.

### 3.2 Bayesian Hierarchical Model

Each skill dimension is modeled as a latent variable with a hierarchical prior:

$$\\theta^{(d)}\_w \\sim \\mathcal{N}(\\mu^{(d)}, \\tau^{(d)2})$$
$$\\hat{s}^{(d)}\_w | \\theta^{(d)}\_w, \\sigma^{(d)}\_w \\sim \\mathcal{N}(\\theta^{(d)}\_w, \\sigma^{(d)2}\_w / N_w)$$

where $d \\in {\\text{buy, sell, timing, sizing, crowd}}$, $\\mu^{(d)}$ and $\\tau^{(d)}$ are population-level hyperparameters estimated from data, and $\\sigma^{(d)}\_w$ is the within-wallet noise. The posterior $p(\\theta^{(d)}\_w | \\hat{s}^{(d)}\_w, N_w)$ produces shrinkage toward the population mean—wallets with few trades shrink strongly, wallets with many trades retain their empirical estimate.

**Posterior credible interval** for each dimension: 95% HPDI from MCMC sampling (PyMC or NumPyro).

**Score for copy-trading decision:** Expected return at delay $\\Delta t$ with followers $|F_w|$:

$$\\text{EV}^{\\text{copy}}\_w = \\mathbb{E}[\\theta^{\\text{sell}}\_w] \\cdot f(|F_w|, \\Delta t)$$

where $f$ is a learned crowd-decay function (log-logistic or exponential).

### 3.3 Regime Decomposition (Optional Extension)

Condition skill estimates on market regime (bull/bear, high/low volatility, pre/post major catalyst) using a Hidden Markov Model on chain-level indicators. Per-regime skill scores reveal whether a wallet's edge is robust or regime-specific.

______________________________________________________________________

## 4. Data

**Scope:** Perpetual futures positions (not spot DEX swaps) across four platforms and three chains.

| Dimension | Details |
|-----------|---------|
| **Platforms** | Jupiter (Solana), Hyperliquid, GMX-v2 (Arbitrum), Myx Finance (EVM), APX Finance |
| **Chains** | Solana, Hyperliquid L1, Arbitrum, BSC, Ethereum |
| **Period** | Jan 2024 – Jul 2026 (estimated from data; verify with `scripts/01_accounts_overview.py`) |
| **Data source** | Private `perpetuals_knowledge_graph` MongoDB (env: `MONGO_SOURCE_URL`) |
| **Raw event log** | `logs` collection — ~40M Open/Close/Deposit/Withdraw events |
| **Closed positions** | `closed_positions` collection — realized PnL per completed position |
| **Aggregated accounts** | `accounts` collection — per-wallet cumulative stats + `logs` daily PnL dict |
| **Existing baseline** | `daily_trader_rankings` collection — daily composite score snapshots |
| **Scale** | Exact wallet count TBD from script 01; estimate 50K–500K active accounts |

**Key data fields enabling the research questions:**

- `action` ∈ {Open, Close, Deposit, Withdraw} — separates entry from exit events (RQ1)
- `side` ∈ {Long, Short} — enables Long-skill vs Short-skill decomposition (RQ1)
- `sizeUsd`, `collateralUsd`, `leverage` — leverage-adjusted skill and sizing skill (Ideas 2, 3)
- `realizedPnl` in `closed_positions` — ground-truth PnL without reconstruction
- `accounts.logs: dict[str, float]` — daily PnL time series per wallet (RQ2 persistence)
- `daily_trader_rankings.traders[].score` — existing baseline to compare against

**Data already available — no external APIs needed.** Crowd-follower graph (RQ3) is not in the DB; RQ3 requires either the Nansen/GMGN follower API or scoping out of the thesis.

______________________________________________________________________

## 5. Evaluation Protocol

### 5.1 Backtest Design

Rolling forward evaluation: train on months 1–18, test on months 19–24, then slide forward by 6-month windows. Prevent look-ahead bias by using only data available at time of scoring.

### 5.2 Metrics

| Metric | Description |
|--------|-------------|
| Hit rate of top-decile wallets | % of top-decile wallets by proposed score that outperform market in next 30d |
| Copier return | Mean return of followers who copy top-decile wallets at 1-block delay |
| Calibration | Coverage probability of 95% CI (should be ≈95% on held-out wallets) |
| Rank correlation | Spearman ρ between proposed multi-dim score and future copier return vs. PnL baseline |
| Crowd-decay fit | R² of crowd-decay function predicting copier return degradation as $|F_w|$ grows |

### 5.3 Baselines

All baselines are computable from the existing `perpetuals_knowledge_graph` DB:

| Baseline | Source field | Formula |
|----------|-------------|---------|
| **B1 — Existing composite** | `daily_trader_rankings.traders[].score` | `risk_reward*0.25 + wl_holding*0.25 + wl_roi*0.25 + win_pct*0.25` |
| **B2 — Raw PnL rank** | `accounts.PNL` | `sort(PNL, descending)` |
| **B3 — Raw ROI rank** | `accounts.ROI` | `sort(ROI, descending)` |
| **B4 — Win-rate rank** | `accounts.profitableRatio` | `sort(profitableRatio, descending)` |
| **B5 — Sharpe ratio** | `accounts.logs` daily series | `mean(daily_pnl) / std(daily_pnl) * sqrt(365)` |
| **B6 — zScore (Anon et al., 2025)** | Reimplement on perp data | ML composite from arXiv:2507.20494 |

B1–B5 are directly extractable from the DB. B6 requires reimplementation on perp events (the original uses Uniswap v3 swap data).

______________________________________________________________________

## 6. Novelty Contributions

1. **First paper to decompose crypto wallet skill into buy, sell, timing, sizing, and crowd-adjusted components** — no prior DeFi paper applies the Lim (2022) or Van Loon (2018) frameworks to on-chain data.

1. **First Bayesian posterior wallet scoring with credible intervals** — enables uncertainty-aware copy decisions and distinguishes lucky-5-trade wallets from reliably-skilled-500-trade wallets.

1. **First crowd-adjusted expected copy value** — directly quantifies the decay in actionable edge as a wallet gains followers, filling the gap identified by Liu et al. (2023).

1. **Empirical test of buy/sell orthogonality in crypto** — extends Lim et al. (2022) from mutual funds to on-chain wallets; expected to hold but not confirmed.

______________________________________________________________________

## 7. Limitations and Risks

| Risk | Mitigation |
|------|-----------|
| On-chain address fragmentation (one entity, many wallets) | Accounts are platform-scoped `{platform}_{chain}_{address}`; cross-platform identity unification out of scope |
| Survivorship bias in wallet selection | Include all wallets active ≥20 trades, including those now inactive |
| Regime non-stationarity | Rolling windows; regime-conditioned model variant |
| Short trade histories → posterior dominated by prior | Sensitivity analysis on prior strength; min 20-trade threshold (verify wallet count via script 04) |
| Crowd-follower graph absent from DB | Scope RQ3 to future work OR use `daily_trader_rankings` appearance frequency as crowd-exposure proxy |
| Gaming of scoring metric | Adversarial robustness analysis following Gao et al. (2026) |
| ADL events create artificial liquidation spikes | Filter events from known ADL dates (e.g., 2025-10-10 Hyperliquid ADL) in robustness checks |
| `accounts.logs` field structure unverified | Run sample query before committing to daily-series Bayesian model |

______________________________________________________________________

## 8. Timeline

| Month | Milestone |
|-------|-----------|
| 1 | EDA: run scripts 01–07 to characterize wallet population, verify skill dimensions feasible |
| 2 | Feature engineering: position-level Long/Short alpha, leverage-adjusted ROI, sizing skill from `sizeUsd` |
| 3–4 | Buy/sell skill estimator: compute `long_alpha` and `short_alpha` per wallet, test orthogonality (RQ1) |
| 5–6 | Bayesian hierarchical model: PyMC implementation, MCMC sampling, calibration on held-out wallets (RQ2) |
| 7 | Leverage-adjusted score: `roi / sqrt(leverage)` dimension + liquidation penalty |
| 8 | Evaluation: backtest against B1–B5 baselines using rolling forward windows |
| 9–10 | Ablation studies: which skill dimensions drive predictive improvement? |
| 11–12 | Thesis writing, conference submission (KDD 2027 or ICAIF 2027) |

______________________________________________________________________

## 9. References

Full BibTeX in `references.bib`. Key references:

- Lim et al. (2022) — Buy/sell skill asymmetry [doi:10.1007/s11156-022-01065-9]
- Van Loon (2018) — Timing/sizing decomposition [doi:10.3905/jpm.2018.44.3.025]
- Kosowski et al. (2006) — Bayesian bootstrap for hedge fund skill [doi:10.1016/j.jfineco.2005.12.009]
- Berk & van Binsbergen (2015) — AUM-adjusted skill, Bayesian hierarchical model [doi:10.1016/j.jfineco.2015.05.002]
- Liu, Yang & Tan (2023) — Crowd effects in social trading [doi:10.2139/ssrn.4528456]
- Gao et al. (2026) — Adversarial copy trading [arXiv:2601.08641]
- Anon et al. (2025) — zScore DeFi wallet scoring [arXiv:2507.20494]
- Choi et al. (2025) — VC skill vs. random in heavy tails [arXiv:2605.03980]
- Papaioannou et al. (2024) — Luck vs. skill in investment competitions [arXiv:2412.04490]

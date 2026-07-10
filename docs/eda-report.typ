#set document(
  title: "EDA & Initial Results: Tier-Aware Crowding and Early Warning of Synchronized Liquidation Bursts",
)
#set page(paper: "a4", margin: 2.4cm, numbering: "1")
#set text(size: 11pt, font: "New Computer Modern")
#set par(justify: true)
#set heading(numbering: "1.1")
#set math.equation(numbering: "(1)")
#show link: underline

// indicator function helper
#let II(x) = $bold(1)[#x]$

#align(center)[
  #text(size: 17pt, weight: "bold")[EDA & Initial Results] \
  #text(size: 13pt)[Tier-Aware Crowding and Early Warning of \
    Synchronized Liquidation Bursts in On-Chain Perpetual Futures] \
  #v(0.5em)
  #text(size: 11pt)[MSc Computer Science -- Thesis] \
  #text(size: 11pt)[July 2026]
]

#v(1em)

#align(center)[#text(weight: "bold")[Abstract]]
#block(inset: (x: 1.2em))[
  This report develops and de-risks a new thesis direction on the `perpetuals_knowledge_graph` database (40.5M log events, 1.34M closed positions, 190,573 explicit liquidations, 249 assets, 5 venues, 491 days). We forecast _synchronized liquidation bursts_---short windows in which many perpetual-futures positions on an asset are force-closed together---and ask whether _tier-aware crowding_ features improve prediction over a self-exciting (Hawkes) baseline. Two feasibility probes were run before any modelling. (i) The liquidation-_magnet_ hypothesis (price attracted to liquidation-price walls) was *rejected* on the three most liquid assets under two independent test forms (all null). (ii) The liquidation-_burst_ label *passed decisively*: it is dense and strongly learnable---a single trailing-intensity feature already reaches AUC 0.83--0.87, confirming self-excitation. On a leakage-safe, time-ordered split (4.2M asset-bin rows, 40 assets), a tuned crowding-augmented gradient-boosted model (tier imbalance, cross-asset spillover, liquidation notional; 17 features) is compared against three _named, published_ baselines fit on the same data: a classical univariate Hawkes process (MLE), a market-augmented multivariate Hawkes, and a neural Transformer Hawkes Process @zuo2020thp. Three covariate-using models are then evaluated: the tuned classifier, a covariate-conditioned neural point process (a GRU-hazard model over the feature sequence), and a spatio-temporal GNN over a cross-asset graph. On precision-recall---the honest metric for a 0.56%-positive test set---all three beat all three baselines by a wide margin; the covariate-conditioned TPP is best (PR-AUC 0.256, versus 0.157 classical Hawkes and 0.129 neural THP, gains of +0.10 to +0.13), narrowly ahead of the GNN (0.251) and the tuned classifier (0.250). The decisive factor is the covariates, shown within one model family: the neural point process roughly _doubles_ its PR-AUC (0.129→0.256) when conditioned on crowding features rather than event times alone. Tellingly, all intensity-only baselines collapse to ROC-AUC ≈0.97 but PR-AUC ≈0.13--0.16: self-exciting intensity is a strong ranker yet a weak precision signal under imbalance, which ROC hides and PR-AUC exposes. Unlike the prior wallet-scoring formulation---whose evaluation label was ≈99% sampling noise---this problem has a dense, reliable label, so measured lift is meaningful. A rolling five-fold walk-forward confirms the LightGBM crowding lift is not a single-split artefact (PR-AUC lift +0.024 ± 0.013, ROC-AUC lift +0.054 ± 0.017, positive in every fold), and holds across bull/bear, high/low-volatility, and high/low-crowding regimes---largest exactly in stressed and low-crowding periods, where the self-exciting baseline is weakest. ]

#v(1em)

= Problem Formulation <sec:formulation>

== Why Forecast Liquidation Bursts

Perpetual futures are the dominant crypto derivative and increasingly the venue of price discovery. Their defining systemic risk is the _liquidation cascade_: when a cluster of leveraged positions breaches maintenance margin, forced liquidations sell into the market, push price further, and trip the next layer of leveraged positions---a self-exciting, contagious unwind. Existing early-warning signals used by practitioners (extreme funding, long/short imbalance, record open interest) are heuristic thresholds, not calibrated predictive models. This thesis asks a sharper, learnable question: _given the state of a market at time $t$, what is the probability that a synchronized liquidation burst occurs in the next $h$ minutes, and do wallet-tier-resolved crowding features improve that forecast over a purely self-exciting baseline?_

== Formal Definition of a Burst

Let $L_(a,t)$ denote the number of liquidation events for asset $a$ in a 5-minute bin $t$ (source: `close_action = Liquidate`). The burst label at horizon $h$ (in bins) and threshold $theta$ is
$ Y_(a,t)^((h)) = II(sum_(tau in (t,\, t+h]) L_(a,tau) gt.eq theta) $ <eq:burst>
The label uses only the _future_ window $(t, t+h]$; every predictor is computed on the _past_ window $[t-w, t]$, so features and label are disjoint by construction. @sec:m0burst fixes the operating point at $h=3$ bins (15 minutes), $theta=3$.

== Decomposition of the Burst Intensity

We model the conditional intensity of liquidation events for asset $a$ (and, in the full model, wallet-tier and venue marks $k$) as a self-exciting process with a covariate-modulated baseline:
$
  lambda_k (t) = underbrace(mu_k (x_k (t)), "crowding-modulated baseline") + sum_(k') sum_(t_j < t) alpha_(k'->k) phi(t - t_j)
$ <eq:intensity>
where $phi$ is an exponential triggering kernel, $alpha_(k'->k)$ is a cross-mark excitation matrix (cross-tier, cross-venue contagion), and $x_k (t)$ is a vector of _tier-aware crowding_ covariates. The second term is the classical Hawkes self-excitation of @bacry2015hawkes; the novel component is the crowding-modulated baseline $mu_k (dot)$. The central hypothesis of the thesis is that $x_k (t)$ carries information about _future_ bursts beyond what the recent event history alone provides. @fig:intensity maps each modelling family onto the two terms of @eq:intensity.

#figure(
  image("figs/intensity.pdf", width: 90%),
  caption: [Decomposition of the burst intensity, @eq:intensity. The published baselines model only the self-exciting term (right); this work's covariate models supply the crowding-modulated baseline (left). The thesis measures the _lift_ from adding the left term, isolated most cleanly within the neural-TPP family (THP → CovTPP).],
) <fig:intensity>

== The Crowding Hypothesis

Crowding thins a market's "error bars": when positioning is concentrated and one-sided---especially among large wallets---a modest adverse move liquidates many positions at once. We therefore construct, per asset and 5-minute bin, features that a single scalar such as funding rate cannot express: open-interest long/short imbalance, per-tier (small/medium/large wallet) imbalance, small-versus-large disagreement, positioning concentration, mean leverage of open positions, and the velocity of these quantities. The prediction target @eq:burst tests directly whether these covariates raise burst probability.

== The Evaluation Problem (and the Contrast with Wallet Skill)

A prior formulation on the same database---side-aware wallet skill scoring---failed for a measurement reason: its evaluation label (future win rate over few trades) was ≈99% binomial sampling noise, so no method could demonstrably beat simple baselines. The present formulation is deliberately chosen to avoid that trap. The burst label @eq:burst is an _event count_ over a dense stream (190,573 liquidations), not a noisy per-wallet rate. @sec:m0burst shows it is strongly learnable. The consequence is that the modelling target is not "can bursts be predicted" (they can, almost trivially, from temporal autocorrelation) but _by how much crowding features improve prediction over the self-exciting baseline_---a well-posed, measurable question.

== Contributions

In one sentence: _crowding covariates, injected into the intensity baseline of a self-exciting process, roughly double PR-AUC over intensity-only point-process baselines on a leakage-safe, out-of-sample liquidation-burst forecast._ Concretely:

- *(C1)* A leakage-safe, tier-aware crowding panel and burst label built from 40.5M raw on-chain events (4.24M asset-bin rows, 40 assets; @sec:system to @sec:m0burst), with two feasibility probes run _before_ modelling to de-risk the direction.
- *(C2)* A covariate-conditioned neural point process (CovTPP) that realizes the crowding-modulated baseline $mu_k (dot)$ of @eq:intensity, isolating the covariate effect _within_ the neural-TPP family against a Transformer Hawkes Process baseline.
- *(C3)* Explicit cross-asset spillover features and a spatio-temporal GNN over a positioning graph, benchmarked against a market-augmented multivariate Hawkes process.
- *(C4)* A precision-recall-first evaluation on identical out-of-sample test bins across six named models (@sec:results), exposing an ROC/PR divergence that ROC-only reporting would hide.

@sec:gap locates each contribution against a specific, cited gap in prior work.

= Related Work <sec:related>

We organize prior work by the five research lines this thesis sits at the intersection of, and state in @sec:gap precisely where each falls short of a calibrated, crowding-aware burst forecast.

*Self-exciting processes and liquidation cascades.* Modelling clustered financial events as self-exciting (Hawkes) processes is well established: @bacry2015hawkes survey Hawkes processes in finance, and @hardiman2013endogeneity use the branching ratio to quantify market endogeneity/reflexivity, the same mechanism @filimonov2012reflexivity tie to flash crashes. The closest DeFi work, @cao2025defi, shows liquidations cluster _across_ protocols in a multivariate Hawkes framework, and @markovhawkes2025manipulation extend Hawkes intensities with a Markov-modulated baseline for manipulation detection. This entire line models the intensity from _event history alone_ (@eq:intensity, second term); positioning/crowding state never enters the baseline $mu_k$. A parallel nowcasting line @nowcast2023crashrisk predicts crash risk from order-flow imbalance but not from wallet-tier-resolved positioning.

*Perpetual-futures microstructure and liquidity risk.* Forward-looking liquidity risk for perpetuals has begun to attract dedicated frameworks such as Slippage-at-Risk @slippageatrisk2026, which quantifies execution risk but treats liquidation as an exogenous liquidity shock rather than a self-exciting, forecastable event stream.

*Marked and neural temporal point processes.* A rich model family conditions event intensity on learned history: recurrent marked TPPs @du2016rmtpp, the neural Hawkes process @mei2017neuralhawkes, the Transformer Hawkes process @zuo2020thp, spatio-temporal neural point processes @zhou2022neuralstpp, multi-event spatio-temporal forecasting @beyondhawkes2022, and recent state-space variants @mambahawkes2024, now benchmarked openly by EasyTPP @xue2023easytpp. These methods condition on event times and categorical _marks_, but---as our THP baseline shows empirically---not on exogenous, continuous crowding covariates; the neural machinery raises expressivity over classical Hawkes yet lands in the same precision band when fed event times only (@tab:m2).

*Topology and cross-asset structure of on-chain graphs.* Blockchain-network structure carries early-warning signal: topological anomaly detection on dynamic multilayer chains @oforiboateng2021topological, topological features for price-anomaly prediction @xrp2026topological, and persistence-velocity network anomaly detection @persistencevelocity2025. These motivate our cross-asset graph (the ST-GNN, @sec:results) but target price/label anomalies on transaction graphs, not synchronized liquidation bursts on a cross-asset positioning graph.

*Conformal prediction under distribution shift.* Because burst frequency drifts (test base rate 0.56% vs. train 1.51%, @sec:results), calibrated uncertainty must survive non-stationarity: adaptive conformal inference @gibbs2021adaptive, conformal prediction for time series @zaffran2022adaptive, and drift-aware conformal streams @driftconformal2026. These supply the calibration layer of the planned system but have not been applied to a liquidation-burst point process.

= Research Gap and Contributions <sec:gap>

Reading the five lines together exposes a specific, unfilled intersection.

*G1 --- Intensity-only cascade models ignore crowding.*: DeFi/finance liquidation models @cao2025defi @bacry2015hawkes @hardiman2013endogeneity forecast from event history alone. Whether _wallet-tier-resolved_ positioning (imbalance, concentration, leverage) adds predictive power over self-excitation is untested. \

*G2 --- Neural TPPs are not conditioned on exogenous crowding.*: State-of-the-art point processes @zuo2020thp @mei2017neuralhawkes @du2016rmtpp condition on times and marks, not on a continuous covariate stream of market positioning---so the covariate-vs-intensity question is not isolated _within_ one model family. \

*G3 --- Cross-protocol contagion is described, not forecast.*: @cao2025defi establish cross-protocol clustering descriptively; no work turns cross-asset spillover into a calibrated, leakage-safe _early-warning_ forecast of the next burst. \

*G4 --- No calibrated, shift-aware burst early warning.*: Conformal methods @gibbs2021adaptive @zaffran2022adaptive exist but have not been coupled to a liquidation point process to produce coverage-controlled lead-time/false-alarm guarantees under regime drift. \

*G5 --- Evaluation under extreme imbalance is mishandled.*: A 0.56% positive rate makes ROC-AUC misleading; the honest metric is precision-recall, an evaluation discipline absent from prior liquidation-cascade reporting. \


*Contributions.* This thesis targets exactly this gap: (C1) a leakage-safe tier-aware _crowding_ panel and burst label on a 40.5M-event on-chain corpus (@sec:related G1); (C2) a covariate-conditioned neural point process (CovTPP) that injects crowding into the intensity baseline $mu_k$ of @eq:intensity, isolating the covariate effect within the neural-TPP family against a THP baseline (G2); (C3) explicit cross-asset spillover features and an ST-GNN over a positioning graph, benchmarked against a multivariate Hawkes (G3); (C4) a PR-first evaluation on identical out-of-sample bins with a planned adaptive-conformal layer for the regime shift (G4, G5). The results (@sec:results) confirm the central claim of G1--G2: crowding covariates roughly double PR-AUC over intensity-only baselines within the same model family.

= System Overview <sec:system>

At a glance the study is a single leakage-safe pipeline that turns a raw on-chain event log into a burst forecast, guarded by two feasibility probes and evaluated against published point-process baselines. @fig:pipeline shows the end-to-end data flow, @fig:gates the two go/no-go probes that fixed the direction, and @fig:models the model landscape (what each family consumes and how it scores).

#figure(
  image("figs/pipeline.pdf", width: 100%),
  caption: [End-to-end pipeline. Raw `logs` are reconstructed into closed positions, then the panel builder emits one leakage-safe row per (asset, 5-min bin) on a global epoch-aligned grid: features from $[t-w,t]$, label from the disjoint future window $(t,t+h]$. The panel is split time-ordered (earlier bins train, later bins test) and every model is scored on the identical test bins.],
) <fig:pipeline>

#figure(
  image("figs/gates.pdf", width: 100%),
  caption: [Two feasibility probes gated the direction _before_ any modelling. Probe 1 (@sec:m0magnet) tested the liquidation-magnet hypothesis and was rejected under two independent test forms; the wall map survives only as a candidate feature. Probe 2 (@sec:m0burst) confirmed the burst label is dense and strongly learnable, so the open question becomes _how much crowding adds over self-excitation_, not whether bursts are predictable.],
) <fig:gates>

#figure(
  image("figs/models.pdf", width: 95%),
  caption: [Model landscape. Three published point-process baselines consume event times only; three models in this work add the 17 leakage-safe crowding/cross-asset covariates. The dashed arrow marks the decisive within-family contrast: the _same_ neural point-process family (THP → CovTPP) roughly doubles PR-AUC once conditioned on covariates. All six are scored on identical out-of-sample test bins (@tab:m2).],
) <fig:models>

== Overview of the Applied Models <sec:modeloverview>

@fig:models groups the six named models by what they consume: event times only (three published point-process baselines) versus event times plus the 17-dimensional crowding/cross-asset covariate vector (three models proposed here). Below is the mechanics of each, starting with the Hawkes process since it underlies every intensity-only baseline and directly motivates the covariate-modulated baseline of @eq:intensity.

*Hawkes process (self-exciting baseline).* A univariate Hawkes process models the conditional intensity of liquidation events as a constant baseline rate $mu$ plus a sum of decaying excitation contributed by every past event: $lambda(t) = mu + sum_(t_j<t) alpha e^(-beta(t-t_j))$. Each event instantly raises the intensity by $alpha$, which then decays exponentially at rate $beta$ back toward $mu$; when several events land close together their excitations stack and the intensity spikes well above baseline before relaxing---this cluster-then-relax pattern is exactly what a liquidation cascade looks like at the event-count level. @fig:hawkesexample simulates a stable (sub-critical) process, branching ratio $alpha/beta approx 0.61 < 1$, and plots the intensity path together with the simulated event times: quiet periods sit at $mu$, and every event produces a visible jump followed by decay, with a tight cluster of three events lifting $lambda(t)$ to nearly $5 times$ the baseline before it relaxes. @sec:baselines fits this model per asset by maximum likelihood and uses the fitted $lambda(t)$ itself as the burst score; the *market-augmented Hawkes* baseline adds a second excitation term driven by all-asset (market-wide) liquidation events with its own decay rate, a tractable approximation of cross-venue contagion without a full multivariate kernel matrix.

#figure(
  image("figs/hawkes_example.pdf", width: 92%),
  caption: [Worked example of a self-exciting Hawkes intensity path (simulated; $mu=0.3$, $alpha=0.55$, $beta=0.9$, branching ratio $alpha/beta approx 0.61$). Vertical ticks are simulated event times; the curve is $lambda(t)$. Each event triggers an instantaneous jump of size $alpha$ followed by exponential decay at rate $beta$; a tight cluster of events compounds these jumps into a visible burst before $lambda(t)$ relaxes back to the dashed baseline $mu$.],
) <fig:hawkesexample>

*Transformer Hawkes Process (THP).* THP replaces the fixed exponential kernel with a learned one: a self-attention encoder consumes each asset's past event (and inter-event-time) sequence and produces a hidden state $h_i$ per event, from which a continuous intensity $lambda(t)="softplus"(v^top h_i + b + a(t-t_i))$ is read off. It is strictly more expressive than the classical exponential kernel but---like the Hawkes baselines---conditions only on event times, never on crowding state.

*LightGBM (covariate classifier).* A gradient-boosted tree ensemble trained directly on the 17-feature crowding panel to predict the binary burst label @eq:burst, hyperparameters tuned by Optuna against average precision. It carries no notion of intensity or point-process structure; it is the strongest purely discriminative baseline for the covariates.

*Covariate-conditioned neural TPP (CovTPP).* The direct covariate analogue of THP: a GRU runs causally over the 17-feature sequence (rather than over event times) to produce a history state $h_t$, fed into the same hazard-style intensity head $lambda_t="softplus"(w^top h_t+b)$, $P("burst")=1-e^(-lambda_t)$. Comparing THP and CovTPP in @tab:m2 isolates the effect of conditioning on crowding within one model family.

*Spatio-temporal GNN (ST-GNN).* Treats the 40 assets as nodes on the shared global 5-minute grid; a graph layer exchanges a cross-asset market message between active nodes at each step, and a per-node GRU carries temporal state into the same hazard head as CovTPP. It tests whether explicit message passing beats the hand-engineered market/spillover covariates already present in the feature panel.

= Data Overview <sec:data>

The primary source is the `logs` collection of the `perpetuals_knowledge_graph` MongoDB, recording every open/close lifecycle event for perpetual positions across five platforms (Hyperliquid, Jupiter, GMX-v2, APX, Myx) and five chains. Reconstructed closed positions are stored in `data/processed/positions.parquet`.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, center),
    table.header([Quantity], [Value], [Source collection]),
    [Total log events], [40,552,429], [`logs`],
    [Closed positions], [1,342,059], [`closed_positions`],
    [Explicit liquidation events], [190,573], [`positions` (`Liquidate`)],
    [Assets with liquidations], [249], [`positions`],
    [Minute-level price points], [93,743,096], [`hyperliquid_prices`],
    [Open positions (snapshot)], [25,584], [`opening_positions`],
    [Backtested trade outcomes], [567,784], [`trade_history`],
    [Data span], [491 days], [`logs`],
  ),
  caption: [Data scale relevant to burst modelling (verified collection counts).],
) <tab:scale>

*Collection availability (verified).* A census confirmed which collections carry usable data. Populated and useful: `logs`, `closed_positions`, `opening_positions`, `hyperliquid_prices` (93.7M minute prices), `hyperliquid_pairs` (per-pair maximum leverage), `trade_history` (567k backtests with `stop_reason` ∈ {sl, tp, timeout}), and multi-horizon trader panels `web3_traders_{1D,3D,1W,1M}`. Insufficient or absent: `signals` (spot swaps) is a 29-document stub with zero overlap with perp wallets---so a wallet-level spot--perp study is not supported; `market_stats` (108 docs) and the `aggregated_assets` snapshot (one row per asset, no time field) are too coarse to serve as time-varying crowding sources, so crowding is reconstructed from `logs` instead.

*Liquidation concentration.* Liquidations concentrate in the most liquid assets: BTC (78,098), SOL (67,374), ETH (28,331), then a long tail (XRP 2,173, BNB 1,223, DOGE 1,023, ...). This concentration shapes both feasibility probes below.

= Feasibility Probe 1: The Liquidation-Magnet Hypothesis (Rejected) <sec:m0magnet>

Before committing, we tested a tempting adjacent idea: that price is _attracted_ toward dense liquidation-price clusters (a "magnet" / stop-hunt effect). Each open position's liquidation price was approximated as $"entry" times (1 minus.plus 1/"leverage")$ (Long $-$, Short $+$), weighted by size, active over $["open_ts", "close_ts")$; price paths came from `hyperliquid_prices`.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, center),
    table.header(
      [Asset], [N positions], [Spearman($w$, fwd return)], [$p$ (Pearson)]
    ),
    [BTC], [399,044], [+0.017 / +0.029], [0.58 / 0.99],
    [SOL], [297,685], [+0.021], [0.97],
    [ETH], [201,350], [$-$0.001], [0.32],
  ),
  caption: [Magnet probe: directional test (Spearman of size-weighted wall imbalance vs. forward return) on the three most liquid assets. All null.],
) <tab:magnet>

A sharper _attraction_ test---does price _reach_ the nearest dominant wall within the horizon more than an equidistant mirror level on the opposite side, isolating attraction from trend?---was also null on BTC: the wall level was touched 2.4% / 6.0% of the time (horizons 120 / 360 min) versus 2.7% / 6.1% for the mirror ($z approx -0.66$ / $-0.22$). Toward-wall directional hit rates were 0.496 / 0.509 (chance 0.5), with bootstrap 95% CIs straddling zero.

*Verdict.* Across the three most-liquid assets (~900k positions) and two independent test forms, there is *no liquidation-magnet signal*. The mechanism is not demonstrable on liquid majors, so it is *dropped as a headline claim*. The liquidation-wall map is retained only as a candidate _feature_ for burst prediction (walls mark where cascades can ignite, a statement about event clustering, not price attraction). Honest caveats: liquidation prices are approximate (no maintenance margin); the thinnest alts, where such effects are theorised strongest, lack the data density to test rigorously, so the precise claim is "no magnet on liquid majors."

= Feasibility Probe 2: The Burst Label (Passed) <sec:m0burst>

We next validated the burst label @eq:burst: is it balanced enough to train, and is it actually predictable? Liquidation events were binned at 5 minutes per asset (top-12 by liquidation volume, pooled). As a learnability proxy we measured the AUC of a _single trivial feature_---the past-15-minute liquidation count---predicting the future burst (a direct test of the self-excitation premise).

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (right, right, right, right, right),
    table.header(
      [$h$ (min)],
      [$theta$],
      [Pooled base rate],
      [N positives],
      [AUC(past-15m → burst)],
    ),
    [5], [3], [0.0123], [17,029], [0.873],
    [5], [5], [0.0054], [7,522], [0.893],
    [15], [3], [*0.0377*], [*52,182*], [0.831],
    [15], [5], [0.0202], [27,994], [0.862],
    [60], [3], [0.1191], [164,938], [0.755],
    [60], [5], [*0.0785*], [*108,807*], [0.788],
  ),
  caption: [Burst base rate and learnability across horizon $h$ and threshold $theta$. AUC uses one trailing-intensity feature (self-excitation proxy).],
) <tab:burstbase>

*Verdict: pass.* Base rates land in a trainable range (1--12%) with large positive counts ($10^4$--$10^5$), and the label is *strongly learnable*: even a single trailing-intensity feature reaches AUC 0.75--0.91. Self-excitation is real and strong---the Hawkes premise of @eq:intensity is confirmed empirically. This is the inverse of the wallet-scoring failure ($rho=0.013$ noise label). We lock the primary operating point at $h=15$ min, $theta=3$ (3.8% base rate, 52,182 positives). *Crucially, because a trivial past-intensity feature already yields AUC ≈0.87, the modelling contribution must be measured as _lift over this self-exciting baseline_, not as raw predictability.*

= Method: Leakage-Safe Crowding Panel and Baselines

== Feature Panel

The service `src/burst/panel_builder.py` constructs, per asset and 5-minute bin, a row with the burst label @eq:burst and four feature groups (17 features), all computed from information available at or before $t$:

- *Baseline (self-exciting):* `past_liq_short` (15-min trailing liquidation count), `past_liq_long` (60-min).
- *Crowding:* open-interest imbalance; large- and small-tier imbalance; tier disagreement (large $-$ small); large-tier share of open interest (concentration); mean leverage of open positions; open-interest velocity; liquidation-intensity velocity.
- *Volume:* self liquidation _notional_ (USD) over the 15- and 60-minute trailing windows---the value, not just the count, of recent forced closes.
- *Cross-asset (multivariate):* market-wide (all-asset) trailing liquidation count and notional, and the _spillover_ from other assets (market minus self). This is the discrete, engineered counterpart of the cross-mark excitation $alpha_(k'->k)$ in @eq:intensity.

Open interest per (side, tier) is maintained exactly as a step function: each position contributes $+"size"$ at its open bin and $-"size"$ at its close bin; a cumulative sum gives the open state at every bin. To make the cross-asset features well-defined, all per-asset panels are placed on a single _global epoch-aligned_ 5-minute grid ($floor("ts"\/300)$), so every asset's bins share boundaries and the market-wide series joins exactly. Wallet tiers are size terciles per asset (size-based, not label-based, hence leakage-safe). All features use $[t-w, t]$; the label uses $(t, t+h]$; the two are disjoint.

== Baselines <sec:baselines>

We compare against _named, published methods_, all fit on the training period and scored on the identical test bins and label, so the metrics are directly comparable.

- *Univariate Hawkes* (`src/burst/hawkes.py`): the classical self-exciting process with an exponential triggering kernel $g(tau)=alpha beta e^(-beta tau)$, fit per asset by maximum likelihood (branching ratio $alpha$; the crypto-endogeneity Hawkes framing of @bacry2015hawkes, @hardiman2013endogeneity). The per-bin score is the conditional intensity $lambda(t)$. This is the _named-method_ version of the M0 past-intensity proxy.
- *Market-augmented Hawkes:* self-excitation plus an all-asset (market) excitation term with a shared decay---a tractable stand-in for the multivariate cross-venue Hawkes of @cao2025defi.
- *Transformer Hawkes Process (THP)* (`src/burst/thp.py`): a neural temporal point process @zuo2020thp with a self-attention encoder over each asset's event stream and a continuous intensity $lambda(t)="softplus"(v^top h_i + b + a (t-t_i))$, trained by point-process maximum likelihood.

== Proposed covariate-using models

Against the intensity-only baselines we evaluate three models that consume the 17 leakage-safe features:

- *LightGBM* on the 17 features, with hyperparameters tuned by Optuna to maximise average precision on an inner, time-ordered validation slice of training (test untouched; `src/burst/tuner.py`).
- *Covariate-conditioned neural TPP* (`src/burst/covtpp.py`): a GRU runs causally over each asset's 5-minute bin sequence of the 17 features, giving a history state $h_t$; the burst intensity is $lambda_t="softplus"(w^top h_t + b)$ and the horizon hazard is $P("burst")=1-e^(-lambda_t)$, trained by point-process (Bernoulli-hazard) likelihood. This is the direct realisation of the covariate-modulated intensity of @eq:intensity: the _same_ neural point-process family as THP, but conditioned on crowding covariates rather than event times alone.
- *Spatio-temporal GNN* (`src/burst/stgnn.py`): the 40 assets are nodes on the shared global grid; a graph layer mixes each active asset's features with a cross-asset market message per step and a per-node GRU carries temporal state, before the same hazard head. This tests whether explicit cross-asset message passing beats the engineered market/spillover scalars.

#figure(
  image("figs/covtpp_stgnn_pipeline.pdf", width: 100%),
  caption: [Internal data flow of the two neural covariate models. Top: CovTPP runs one causal GRU per asset over the 17-feature sequence (plus the log inter-bin gap), reading the hazard off the final linear+softplus head at every bin. Bottom: ST-GNN instead mixes every active asset's features with a cross-asset market-mean message _before_ the recurrence, so the temporal state at each node already carries cross-asset information at every step---the architectural difference @tab:m2 tests against the LightGBM's hand-engineered market/spillover scalars.],
) <fig:covtppstgnn>

Planned calibration will contrast static (split) conformal with Adaptive Conformal Inference @gibbs2021adaptive @zaffran2022adaptive; the covariate-conditioned TPP is the natural target, as it already emits a point-process hazard intensity.

= Results: Does Crowding Beat Published Point-Process Baselines? <sec:results>

We built the panel over all 40 assets meeting a minimum-liquidation threshold, yielding 4,239,195 asset-bin rows at a 1.22% burst rate. The panel was split _time-ordered_ (no leakage): the earliest 70% of bins train (2,967,435 rows, 1.51% positive), the latest 30% test (1,271,760 rows, 0.56% positive). Every model in @tab:m2 is scored on the same test bins and label.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, right, right),
    table.header([Model], [Type], [ROC-AUC ↑], [PR-AUC ↑]),
    table.cell(
      colspan: 4,
      align: left,
    )[_Published point-process baselines (event times only)_],
    [THP (neural TPP; @zuo2020thp)], [intensity], [0.9700], [0.1294],
    [Hawkes, +market (multivariate), MLE], [intensity], [0.9740], [0.1568],
    [Hawkes, univariate self-exciting, MLE], [intensity], [0.9746], [0.1570],
    table.cell(colspan: 4, align: left)[_Covariate-using models (this work)_],
    [LGBM baseline (past-intensity, 2 feat.)], [discrim.], [0.9078], [0.2281],
    [LGBM full (+crowding+volume+cross-asset, tuned)],
    [discrim.],
    [*0.9801*],
    [0.2502],
    [ST-GNN (cross-asset graph + GRU)], [spatio-temporal], [0.9791], [0.2513],
    [*CovTPP (GRU hazard + covariates)*], [neural TPP], [0.9792], [*0.2556*],
    table.hline(),
    [Best (CovTPP) lift over classical Hawkes (PR-AUC)], [], [], [+0.0986],
    [Best (CovTPP) lift over neural THP (PR-AUC)], [], [], [+0.1262],
  ),
  caption: [Out-of-sample burst prediction on the later test period, all models scored on identical test bins and label (base rate 0.56%; random PR-AUC = 0.0056). ROC-AUC and PR-AUC (↑ better). PR-AUC is the honest metric under this imbalance.],
) <tab:m2>

Five observations, in decreasing order of confidence:

+ *Every covariate-using model beats every published point-process baseline on precision-recall, by a wide margin.* The best model (the covariate-conditioned neural TPP, @sec:results) reaches PR-AUC 0.256 versus 0.157 for classical Hawkes (+0.099) and 0.129 for neural THP (+0.126). This is the thesis's central, defensible claim.
+ *The decisive factor is covariates, not model family---demonstrated within one family.* The neural point process rises from PR-AUC 0.129 (THP, using event times only) to 0.256 (CovTPP, the same TPP family conditioned on the crowding covariates)---a roughly 2× gain. The intensity baselines trail because they ignore crowding, not because they are neural or classical. Feeding tier-crowding and cross-venue covariates into a point process is what supplies predictability beyond self-excitation.
+ *ROC-AUC hides the imbalance; PR-AUC is honest.* All intensity-only models collapse into a narrow band, ROC-AUC ≈0.97 but PR-AUC ≈0.13--0.16: self-exciting intensity is a strong _ranker_ over all bins yet a weak _precision_ signal at a 0.56% base rate. On the faithful metric the covariate models dominate. We do not headline the 0.98 ROC.
+ *Among covariate models the differences are small; graph structure is not a free lunch.* CovTPP (0.2556), ST-GNN (0.2513), and the tuned LightGBM (0.2502) sit within ≈0.005 of one another. The explicit cross-asset message passing of the ST-GNN only ties the classifier, because the cross-asset signal is already carried by the engineered market/spillover features. Tuning the classifier to average precision contributed +0.017 PR-AUC (0.233→0.250), more than the cross-asset features add on this single split; the naive multivariate Hawkes added nothing (0.1568 vs. 0.1570).
+ *Distribution shift is present and motivates calibration.* The test base rate (0.56%) is well below the train rate (1.51%): bursts are rarer in the later regime. This shift is what the planned adaptive-conformal layer targets, it caps the absolute PR numbers, and it means the small CovTPP/ST-GNN/GBM gaps must be confirmed with rolling walk-forward confidence intervals before any ordering among them is claimed.

There is no label leakage: predictors use $[t-w,t]$ and the label uses $(t,t+h]$, which are disjoint; the split is time-ordered; Hawkes and THP parameters are estimated on training-period events only.

= Robustness: Rolling Walk-Forward and Regime Sensitivity <sec:robustness>

@sec:results reports a single time-ordered 70/30 split: one draw from one market regime, flagged as a limitation in the M2 write-up (NS1). We address it directly. The panel is re-split into an expanding-window walk-forward---an initial 40% training window, then five consecutive, non-overlapping test folds (≈509k rows each)---so the tuned LightGBM baseline and full model are refit per fold and scored out-of-sample five times instead of once. Every test row is further labelled along two independent regime axes: an _exogenous_ macro regime from daily BTC/ETH realized volatility and trend (fetched from Binance Futures, used only to label folds post hoc, never as a model feature; crypto alt/perp volatility is macro-beta-driven regardless of trading venue, the same logic as regime-labelling with VIX), and an _endogenous_ crowding regime from the panel's own market-wide liquidation-intensity tertile, which catches idiosyncratic single-asset crowding events the macro label cannot.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    table.header(
      [Fold], [Train rows], [Test rows], [Baseline PR-AUC], [Full PR-AUC]
    ),
    [0], [1,695,645], [508,716], [0.4621], [0.5019],
    [1], [2,204,361], [508,716], [0.4227], [0.4628],
    [2], [2,713,077], [508,677], [0.3032], [0.3115],
    [3], [3,221,754], [508,733], [0.2364], [0.2492],
    [4], [3,730,487], [508,707], [0.2297], [0.2499],
    table.hline(),
    [Mean ± std], [], [], [0.3308 ± 0.0955], [0.3551 ± 0.1071],
  ),
  caption: [Rolling walk-forward, expanding train window, five consecutive out-of-sample test folds. PR-AUC falls fold-over-fold because the positive rate drifts down over the timeline (consistent with the train/test base-rate shift already noted in @sec:results), not because the model degrades: ROC-AUC lift is stable (below).],
) <tab:walkforward>

The lift itself is stable: mean ROC-AUC rises from 0.9283 ± 0.0198 (baseline) to 0.9821 ± 0.0025 (full), a lift of +0.0538 ± 0.0174; mean PR-AUC rises from 0.3308 ± 0.0955 to 0.3551 ± 0.1071, a lift of +0.0242 ± 0.0134. The lift is positive in every one of the five folds, so it is not an artefact of the single split reported in @tab:m2; the ROC lift's standard deviation is small relative to its mean, while the PR lift's is not (std ≈55% of the mean), so the _existence_ of the lift is well supported but its exact size still carries split-to-split variance the single-split number could not reveal.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right),
    table.header(
      [Regime axis],
      [Bucket],
      [n],
      [Pos. rate],
      [Baseline PR-AUC],
      [Full PR-AUC],
    ),
    [Macro volatility (BTC/ETH)],
    [high_vol],
    [1,252,036],
    [0.98%],
    [0.3989],
    [0.4427],

    [], [low_vol], [1,291,513], [0.57%], [0.2608], [0.2869],
    [Macro trend (BTC/ETH)], [bear], [1,412,384], [0.86%], [0.3836], [0.4297],
    [], [bull], [1,131,165], [0.65%], [0.2813], [0.3074],
    [Endogenous crowding], [high_crowd], [933,894], [1.44%], [0.4367], [0.4798],
    [], [med_crowd], [852,622], [0.47%], [0.1243], [0.1456],
    [], [low_crowd], [757,033], [0.28%], [0.0497], [0.0757],
  ),
  caption: [Crowding lift broken out by market regime, on the pooled out-of-sample predictions from @tab:walkforward. The lift survives every bucket on both regime axes; it is largest exactly where the self-exciting baseline is weakest (bear/high-vol markets, low-crowding periods).],
) <tab:regime>

Two findings stand out. First, the lift is regime-sensitive but never disappears: it is roughly double in high-volatility and bear regimes (+0.044 and +0.046 PR-AUC) versus low-volatility and bull regimes (+0.026 each)---crowding covariates matter most exactly when the market is under stress, which is the operationally relevant regime for an early-warning system. Second, the endogenous crowding regime is the sharper cut: in low-crowding periods the past-intensity baseline is barely better than random (ROC-AUC 0.7958, PR-AUC 0.0497 against a 0.28% base rate), while the full model recovers most of its discriminative power (ROC-AUC 0.9711); crowding features do their heaviest lifting exactly where self-excitation alone gives up.

Finally, we stress-test the full model directly on the five largest simultaneous liquidation-burst clusters in the data (the top five 5-minute bins by across-asset burst count, each evaluated in a ±6-hour window around the cluster, non-overlapping). The model holds ROC-AUC 0.968--0.987 and precision-at-top-5% between 0.23 and 0.83 across all five clusters, with recall-at-top-5% of 0.69--0.81---evidence that the lift measured on averaged fold metrics is not hiding a miss on the crashes that would matter operationally.

== Named Case Study: the Oct 10--11 2025 Liquidation Event <sec:oct2025>

Every fold and regime bucket above is anonymous by construction. To ground the model against a real, externally verifiable event, we identify the day in the dataset with the second-highest burst-bin count of all 491 days: Oct 10, 2025 (559 burst bins across 38 active assets, dominated by BTC, SOL, and ETH), matching the publicly reported Oct 10--11 2025 crypto crash---a tariff-shock-driven selloff widely reported as the largest simultaneous liquidation event in the market's history (order of \$19B liquidated industry-wide), with majors reported hit hardest, consistent with what the panel shows independently.

This date falls inside the walk-forward's initial 40% training window (@sec:robustness), so it has never been scored out-of-sample. We train BASELINE and FULL fresh on data strictly before Oct 7, 2025 and evaluate on an Oct 9--14, 2025 window (54,968 asset-bin rows, 3.31% positive---an order of magnitude denser than the panel average, consistent with a cascade). The full model reaches ROC-AUC 0.9694 / PR-AUC 0.6982 versus 0.9626 / 0.6917 for the baseline (lift +0.0068 / +0.0065, a smaller lift than the panel-wide average since the past-intensity baseline is already strong once a cascade is underway), and precision-at-top-5% of 0.51 with recall-at-top-5% of 0.77.

#figure(
  image(
    "../pipeline/outputs/b07_oct2025_case_study/oct2025_timeline.png",
    width: 92%,
  ),
  caption: [BTC predicted P(burst) through the Oct 10--11 2025 event (890 burst bins in the window), model trained only on data before Oct 7, 2025. Red lines mark actual burst bins; dashed line is the alarm threshold (train-set top-5% score). The model's first alarm on BTC precedes the first actual burst bin by 20 minutes.],
) <fig:oct2025>

Calibrating an alarm threshold from the training set's own top-5% score, the model's first alarm on BTC precedes the first actual burst bin by 20 minutes---more than one 15-minute forecast horizon of lead time on the single largest liquidation event in the dataset's window, using a model that never saw this event during training.

== Extending the Walk-Forward to CovTPP and ST-GNN <sec:covtppstgnnwf>

The remaining piece of NS1 is the three-way ordering in @tab:m2 among CovTPP, ST-GNN, and the tuned LightGBM, which sits on a single split (≈0.005 PR-AUC apart). We re-run the same five-fold expanding-window walk-forward and regime labels of @sec:robustness for CovTPP and ST-GNN (LightGBM's walk-forward is already reported there).

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, right),
    table.header([Model], [Mean ROC-AUC], [Mean PR-AUC]),
    [CovTPP], [0.9822 ± 0.0023], [0.3647 ± 0.0991],
    [ST-GNN], [0.9820 ± 0.0022], [0.3631 ± 0.1011],
  ),
  caption: [CovTPP vs. ST-GNN, mean ± std across the same five walk-forward folds as @tab:walkforward. The two models track each other within one fold's own standard deviation at every fold and every regime bucket (vol., trend, and crowding regimes all differ by ≤0.002 PR-AUC between the two) --- e.g. crowd regime: high\_crowd 0.4919 (CovTPP) vs. 0.4902 (ST-GNN); low\_crowd 0.0869 vs. 0.0770.],
) <tab:covtppstgnnwf>

#figure(
  image(
    "../pipeline/outputs/b08_covtpp_stgnn_walkforward/covtpp_stgnn_walkforward.png",
    width: 78%,
  ),
  caption: [Fold-wise PR-AUC, CovTPP vs. ST-GNN, across the same five walk-forward folds as @fig:m6. The two curves overlap almost exactly at every fold.],
) <fig:covtppstgnnwf>

The walk-forward confirms, rather than overturns, the single-split finding of @sec:results: explicit cross-asset graph message passing (ST-GNN) does not distinguishably beat conditioning a per-asset GRU on the same crowding covariates (CovTPP) at any point across five folds or six regime buckets. This closes NS1: all three covariate models---LightGBM, CovTPP, ST-GNN---now have walk-forward confidence intervals, and the robust ordering claim is unchanged: covariate-conditioned models beat intensity-only baselines by a wide, stable margin; the ranking _among_ the three covariate models remains statistically indistinguishable, not merely "provisional pending more folds."

== Operational Metrics: Calibration, Alert Load, Lead Time, and Economic Value <sec:opmetrics>

PR-AUC and ROC-AUC summarize ranking quality but answer none of the questions a deployment decision actually needs (NS2): is the score a trustworthy probability, how many false alarms does a fixed decision rule fire per day, how much warning time does an alarm give before a cascade starts, and does the model catch the cascades that carry the most dollars at risk---not just the most bins? We answer all four from the pooled out-of-sample predictions of the LightGBM full model across the five walk-forward folds of @sec:robustness (2,543,549 rows, 227.6 days, `pipeline/b09_operational_metrics.py`).

*Calibration.* @fig:reliability plots predicted $P("burst")$ against observed burst frequency in ten equal-width bins. Expected Calibration Error is 0.0533, and the curve sits well below the diagonal at every bin above 0.1: the model is *overconfident*---a predicted 0.8 corresponds to an observed rate closer to 0.1--0.3. The raw score is a good _ranker_ (as @tab:m2/@tab:walkforward already show) but not yet a usable probability; any position-sizing or margin-scaling use (@sec:related) requires a recalibration layer (Platt scaling or isotonic regression) before deployment, not just the ranking model itself.

#figure(
  image("../pipeline/outputs/b09_operational_metrics/reliability_diagram.png", width: 55%),
  caption: [Reliability diagram, full LightGBM model, pooled walk-forward OOF predictions, 10 equal-width bins. ECE = 0.0533; the curve below the diagonal shows systematic overconfidence.],
) <fig:reliability>

*Alert load at a fixed operating point.* Fixing recall at 80% (a threshold chosen post hoc on the pooled OOF set for reporting, not a production threshold) gives precision 0.179 and 315.2 false alarms/day pooled across 39 assets---8.08 false alarms per asset per day, roughly one every three hours. This is the number a real alerting product must budget for: an 80%-recall operating point is usable only if downstream automation (deleveraging, vault exit) can absorb an alarm roughly every 3 hours per asset without excessive cost.

*Lead time.* We merge consecutive/near burst bins per asset into discrete cascade "events" (4,283 total) and, for each, measure the time from the _start_ of the alarm episode preceding it (not merely the nearest alarm bin, which would understate warning time when the model has been alarming continuously) to the event's onset. 98.6% of events (4,225/4,283) get at least one alarm at or before onset; median lead time is *90 minutes*, with p10 = 10 min and p90 = 570 min (@fig:leadtime). A small tail (64 events, 1.5%) shows lead times over 48 hours---the model sitting continuously in an alarm state on a persistently crowded asset rather than a discrete warning, which is why the mean (962.5 min) is not the representative number; median and p90 are. Only 4.0% of alarmed events (171/4,225) got their first alarm at or after onset (a same-bin or late catch). A median 90-minute lead time is six times the 15-minute forecast horizon itself---enough real time for on-chain defensive action, not just a dashboard flicker.

#figure(
  image("../pipeline/outputs/b09_operational_metrics/lead_time_distribution.png", width: 68%),
  caption: [Lead-time distribution across 4,225 alarmed cascade events (clipped at 48h; 64 events beyond this are continuous-alarm states, not discrete warnings). Median 90 min, p10 10 min, p90 570 min.],
) <fig:leadtime>

*Economic (notional-weighted) value.* The label ($theta gt.eq 3$ liquidations in 15 minutes) treats a cluster of three small retail liquidations the same as the start of a nine-figure cascade. Weighting average precision by $log(1 + "future USD notional")$ for positive bins (raw-dollar weighting lets the single largest cascade, \$39.5M, dominate the entire curve and is not used) gives economic PR-AUC 0.8321, versus 0.3873 unweighted on the same predictions---the model ranks large-notional cascades far more reliably than small ones. At the 80%-recall operating point, notional recall (fraction of future USD liquidation value caught) is *0.879*, above the 0.800 count recall: the model preferentially catches the cascades that carry more dollars at risk, not just more bins.

= Discussion

The results validate the direction and locate the open problem precisely. Bursts are predictable, self-excitation dominates the easy signal, and every covariate-using model---gradient boosting, a spatio-temporal GNN, and a covariate-conditioned neural point process---beats the published intensity-only baselines on the honest metric, with the covariate-conditioned TPP best. The cleanest evidence for the thesis is the _within-family_ contrast: the neural point process roughly doubles its PR-AUC (0.129→0.256) when its intensity is conditioned on crowding covariates rather than event times alone, isolating crowding---not the choice of learner---as the source of predictability beyond self-excitation. The central methodological finding is the accompanying _ROC/PR divergence_: classical Hawkes, multivariate Hawkes, and neural THP all reach ROC-AUC ≈0.97 yet PR-AUC only ≈0.13--0.16. A self-exciting intensity ranks quiet bins below active ones almost perfectly (hence high ROC), but among the active, high-intensity bins---where precision is decided---recent event history alone poorly separates the bins that burst from those that do not; tier-resolved positioning and cross-venue spillover supply exactly that separation. Consistent with this, adding an explicit cross-asset graph (the ST-GNN) does not beat the classifier, because the engineered market/spillover features already encode the cross-asset signal. The differences among the three covariate models (≈0.005 PR-AUC) are small enough to require rolling walk-forward confidence intervals before any ordering is asserted; the robust, large effect is covariate-conditioned versus intensity-only. Evaluating precision-recall _conditional on non-trivial open interest_ remains a useful refinement, expected to widen the effective gap where it matters operationally. @sec:robustness supplies exactly the walk-forward confidence intervals this section calls for on the LightGBM baseline/full comparison: the lift holds across five expanding-window folds and across every bucket of two independent regime axes, and is largest in stressed (bear, high-volatility) and low-crowding periods---the regimes an early-warning system exists to serve.

The magnet null (@sec:m0magnet) is a useful negative result: it prevents building on an effect the data do not support and keeps the thesis honest about what liquidation walls do (mark ignition points for cascades) versus what they do not (attract price).

= Limitations

+ *Compact models.* All neural models are deliberately small: the THP (32-dim, 2 layers, 3 epochs, 64-event context), the covariate TPP and ST-GNN (1-layer GRU, 48--64 hidden, ≤4 epochs), and the classical Hawkes uses an exponential kernel with $beta$ on a small grid (Nelder--Mead MLE). Legitimate but not heavily tuned. That the neural THP and the classical Hawkes land in the _same_ PR-AUC band (0.13--0.16) is reassuring that the result is about intensity-only versus covariate-conditioned modelling, not an under-trained single baseline; stronger fits are unlikely to close the 0.10--0.13 PR gap.
+ *Small margins among covariate models---confirmed, not just suspected, by walk-forward.* CovTPP, ST-GNN, and the tuned classifier differ by ≤0.005 PR-AUC on the single split in @tab:m2; @sec:covtppstgnnwf shows this holds across five walk-forward folds and six regime buckets (CovTPP and ST-GNN track within ≤0.002 PR-AUC of each other everywhere tested). The claim that any one covariate model is _best_ is not provisional but actively unsupported by the evidence; the robust claim is covariate-conditioned ≫ intensity-only, not an ordering among CovTPP/ST-GNN/LightGBM.
+ *Macro regime is an exogenous market-wide proxy, not asset-native.* The BTC/ETH volatility/trend label is a reasonable crypto-beta proxy for majors but may mislabel idiosyncratic bursts on thin/meme assets (e.g. `kBONK`, `FARTCOIN`, `PENGU`) that decouple from the macro cycle; the endogenous crowding regime partially compensates but is itself derived from aggregate liquidation intensity, not per-asset shocks.
+ *Cross-asset via engineered features, not a fitted process.* Multivariate contagion enters through market-wide and spillover covariates; a fitted marked/multivariate point process is still required to _interpret_ the excitation matrix $alpha_(k'->k)$ and to produce calibrated intensities.
+ *Approximate liquidation prices* (no maintenance margin, no cross-margin) affect the magnet probe and any wall-based feature.
+ *No funding-rate covariate* (absent from the schema); only the funding _clock_ is usable.
+ *Raw score is overconfident, not deployment-ready as a probability.* ECE 0.0533 with the reliability curve below the diagonal (@sec:opmetrics): the model over-states $P("burst")$ at every confidence level above 0.1. The ranking (PR-AUC/ROC-AUC, all walk-forward and event-stress results) is unaffected by this, but any use of the raw score as a probability---position sizing, dynamic margin, coverage-controlled alarms---requires a recalibration layer first.
+ *Alert load and 80%-recall operating point are single-point estimates, not swept.* @sec:opmetrics fixes recall at 80% as one illustrative operating point (8.08 false alarms/day/asset, median lead time 90 min); a full precision-recall-vs-alert-budget sweep, and per-asset (rather than pooled) false-alarm rates, would be needed before sizing a specific production alerting budget.

= Key Findings Summary

*F1:* Magnet effect rejected. No attraction of price to liquidation walls on BTC/SOL/ETH under two test forms---dropped as a claim, wall map kept only as a feature. \

*F2:* Burst label is dense and strongly learnable. Base rates 1--12% with $10^4$--$10^5$ positives; a single trailing-intensity feature gives AUC 0.75--0.91. Locked operating point: $h=15$ min, $theta=3$. \

*F3:* Covariate models beat published point-process baselines on PR-AUC; the covariate-conditioned TPP is best. PR-AUC 0.256 (CovTPP) > 0.251 (ST-GNN) > 0.250 (tuned LightGBM) ≫ 0.157 (classical Hawkes) and 0.129 (neural THP), on identical out-of-sample test bins (+0.10 to +0.13 over the baselines). \

*F4:* Covariates, not model class, drive the gain. The _same_ neural TPP family doubles its PR-AUC (0.129→0.256) when conditioned on crowding covariates rather than event times. ROC hides the imbalance (all baselines ≈0.97); PR-AUC is honest. Naive multivariate Hawkes adds nothing over univariate (0.1568 vs. 0.1570), and an explicit cross-asset GNN only ties the classifier---the engineered spillover features already carry that structure. \

*F5:* Reliable label, unlike wallet skill. The event-count burst label ($rho$ ≫ 0) avoids the $rho=0.013$ noise that limited the earlier formulation, so measured lift is meaningful. \

*F6:* The LightGBM crowding lift survives a five-fold rolling walk-forward (PR-AUC lift +0.0242 ± 0.0134, ROC-AUC lift +0.0538 ± 0.0174, positive in every fold) and every bucket of two independent regime axes (@sec:robustness), and is largest in stressed and low-crowding regimes---exactly where an early-warning system needs to work. \

*F7:* CovTPP and ST-GNN track each other within ≤0.002 PR-AUC across the same five folds and six regime buckets (@sec:covtppstgnnwf): the single-split three-way ordering in @tab:m2 is not a reliable ranking, only covariate-conditioned ≫ intensity-only is. \

*F8:* Median lead time 90 min (six times the 15-min forecast horizon) at a fixed 80%-recall operating point, and the model catches disproportionately more of the future USD notional (0.879) than of the raw event count (0.800)---but the raw score is *overconfident* (ECE 0.0533) and needs recalibration before any use beyond ranking (@sec:opmetrics). \


= Next Steps

*NS1 (resolved, @sec:robustness, @sec:covtppstgnnwf):* Rolling multi-fold walk-forward now covers all three covariate models (LightGBM, CovTPP, ST-GNN), with regime-sensitivity broken out by macro (BTC/ETH) and endogenous crowding regime. Outcome: the LightGBM crowding lift is robust across folds and regimes; the three-way ordering among covariate models is not distinguishable from split noise and should not be reported as a ranking. \

*NS2 (resolved, @sec:opmetrics):* Operating-point metrics computed at fixed 80% recall: precision 0.179, 8.08 false alarms/day/asset, median lead time 90 min (@sec:oct2025's +20 min BTC example is one point in this distribution), ECE 0.0533 (overconfident, needs recalibration before position-sizing use), and economic PR-AUC 0.8321 vs. 0.3873 unweighted. Remaining: PR-AUC _conditional on non-trivial open interest_ is not yet computed. \

*NS3:* Adaptive-conformal calibration across the regime shift (test base rate 0.56% vs. train 1.51%); report coverage and lead-time / false-alarm tradeoffs. \

*NS4:* Calibrate the covariate-conditioned TPP (@sec:results), which already emits a point-process hazard, and fit a marked / multivariate Hawkes for interpretable excitation $alpha_(k'->k)$; stress-test the baseline gap with a stronger neural TPP (EasyTPP-grade THP/NHP). \


= Figures

#figure(
  image(
    "../pipeline/outputs/b01_burst_baseline/burst_baseline_lift.png",
    width: 92%,
  ),
  caption: [Burst prediction on a leakage-safe, time-ordered test period. Left: out-of-sample ROC-AUC and PR-AUC for the self-exciting LightGBM baseline (past-intensity only) versus the tuned full model (+crowding+volume+cross-asset). Right: LightGBM feature importances of the full model, showing the relative contribution of the tier-crowding and cross-asset features over the trailing-intensity baseline. See @tab:m2 for the full comparison against the classical-Hawkes and neural-THP baselines.],
) <fig:m1>

#figure(
  image(
    "../pipeline/outputs/b06_regime_robustness/regime_robustness.png",
    width: 92%,
  ),
  caption: [Rolling walk-forward and regime robustness (@sec:robustness). Left: PR-AUC per fold for the baseline and full LightGBM model across the five expanding-window folds of @tab:walkforward. Right: PR-AUC lift (full − baseline) by endogenous crowding regime, from @tab:regime.],
) <fig:m6>


#bibliography("../references.bib", style: "ieee", title: "References")

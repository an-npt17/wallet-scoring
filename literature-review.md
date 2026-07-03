# Literature Review: Elite Wallet Scoring with Side-Aware Skill Decomposition

**Collection:** Research-WalletScoring-2026-07\
**Date:** 2026-07-02\
**Scope:** Focused (2023–2026, 22 papers)

______________________________________________________________________

## 1. Introduction

Blockchain copy trading platforms promise retail participants access to "smart money" alpha by mirroring high-performing wallets. The commercial appeal is direct: identify elite wallets, rank them, and let followers copy. Yet this framing conceals a fundamental measurement problem. A single PnL score conflates four orthogonal sources of edge—entry timing, exit quality, position sizing discipline, and originality relative to the crowd—each of which may be present or absent independently. This review synthesizes 22 papers across on-chain wallet scoring, trader skill decomposition, Bayesian performance attribution, copy-trading dynamics, and informed-trading detection to identify the state of the art and its gaps.

______________________________________________________________________

## 2. On-Chain Wallet Scoring and DeFi Reputation

### 2.1 Composite Behavioral Scores

The most direct antecedent is the zScore framework of Anon et al. (2025) [2507.20494], which applies a deep residual neural network on Uniswap v3 data to produce two scores: a **Liquidity Provision Score** capturing strategic pool contributions, and a **Swap Behavior Score** reflecting trading intent, volatility exposure, and withdrawal discipline. Rule-based behavioral blueprints decompose activity into volume, frequency, holding time, and withdrawal patterns before feeding the supervised network. The framework demonstrates that wallet behavior is multi-dimensional; however, it (a) treats buying and selling as a single swap dimension, (b) produces point scores without uncertainty estimates, and (c) is tested on a single protocol.

An earlier credit-risk angle (Bao et al., 2026, Springer) uses a transaction-graph predictive hurdle model to decompose DeFi default risk into Probability of Default, Liquidation Severity, and Exposure at Default on Compound V2 data (AUC-ROC 0.866). This decomposes *risk* but not *skill*.

Survey papers on ML for blockchain data analysis (Zheng et al., 2024 [2404.18251]) and fraud detection in DeFi (Zhu et al., 2023 [2308.15992]) establish the feature engineering landscape: transaction graph structure (GNN node embeddings), temporal patterns, and protocol-level metadata are the standard inputs for address classification. However, classification for fraud or risk is a different objective than scoring genuine trading skill.

### 2.2 On-Chain Flow Signals

He et al. (2024) [2411.06327] examine the intraday return- and volatility-forecasting power of on-chain flows for BTC, ETH, and USDT. USDT outflows to exchanges positively predict BTC and ETH returns; ETH net inflows predict ETH returns negatively; BTC inflows predict lower volatility. These flow signals demonstrate that on-chain activity contains information about future price, which is the prerequisite for skill identification. However, the study measures asset-level signals, not wallet-level skill.

### 2.3 Perpetual DEX Market Structure

The perpetual futures DEX ecosystem that constitutes our data source has attracted a growing body of market-microstructure research. Chen et al. (2024) [2402.03953] classify perpetual exchange architectures into three models—vAMM, Oracle-based, and Central Limit Order Book (CLOB)—and document that each produces distinct behavioral signatures: under oracle-based pricing, traders act as price takers reacting to external price moves, while vAMM environments exhibit asymmetric long/short open-interest dynamics. Crucially, Chen et al. observe that **less informed traders overreact to positive news by increasing long exposure**, a systematic bias directly relevant to our Long-skill decomposition.

Barone and Lillo (2026) [2606.15715] study adverse selection and market impact on Hyperliquid—one of the primary platforms in our dataset. Using 4.3 million reconstructed metaorders, they demonstrate that visible TWAP orders attract liquidity and face lower permanent price impact than hidden orders. This establishes a microstructure baseline for Hyperliquid: trader order-flow visibility correlates with execution quality, implying that wallet-level informed-trading signals are embedded in the on-chain event stream we analyze. The **adverse selection burden** quantified by Barone and Lillo is the market-level manifestation of the informed trading we seek to measure at the wallet level.

Chitra (2026) [2512.01112] provides the first formal analysis of Hyperliquid's autodeleveraging (ADL) mechanism, documenting a $2.1B position closeout in 12 minutes on October 10, 2025. The paper identifies a trilemma: no ADL policy can simultaneously guarantee exchange solvency, revenue, and trader fairness. For wallet scoring, the ADL event creates a natural external shock that tests whether high-ranked wallets are genuinely skilled (can anticipate and hedge ADL risk) or merely lucky (high leverage that survives until a systemic event). **Liquidation rate under ADL stress is a proposed risk-intelligence dimension** in our framework.

______________________________________________________________________

## 3. Informed Trading Detection in Decentralized Markets

### 3.1 Prediction Market Evidence

The emergence of decentralized prediction markets (Polymarket) has produced the richest evidence on identifying skilled/informed traders at the wallet level. Three concurrent 2026 methodological papers represent the frontier:

**Gomez-Cram, Mitts, and Nechepurenko** are synthesized by Nechepurenko (2026) [2605.02287], who proposes a methodological taxonomy:

- **Composite screening** (Mitts & Ofir): Identified $143M in anomalous profit across 210,000+ wallet-market pairs.
- **Sign-randomization testing** (Gomez-Cram et al.): Event-level analysis classifying 3.14% of accounts as "skilled winners" via persistent directional accuracy.
- **Information Leakage Score (ILS)**: Per-market quantification of information front-loading at public-event timestamps.

Saguillo et al. (2026) [2605.02286] apply ILS to documented insider cases (US-Iran conflict markets), finding a 0.444 magnitude shift between event-based and resolution-proxy measurements, with 332 wallets active across correlated markets. The anatomy of Polymarket in the 2024 US election (2603.03136) quantified $3.6B in trading volume and demonstrated persistent order flow from a small subset of wallets.

The ForesightFlow framework (2026) [2605.00493] generalizes ILS into a systematic scoring system for any prediction market, quantifying per-market information advantage.

**Key insight for wallet scoring:** These methods show wallet-level skill can be identified on prediction markets through persistence testing and front-loading analysis. The fundamental methods (sign-randomization, Bayesian persistence) are transferable to DeFi trading with appropriate adaptations.

______________________________________________________________________

## 4. Trader Skill Decomposition in Traditional Finance

### 4.1 Buy/Sell Asymmetry

The most directly relevant empirical result is Lim et al. (2022) \[doi:10.1007/s11156-022-01065-9\]: **selling skill drives overall mutual fund performance, while buying skill is largely uncorrelated with aggregate alpha.** Fund managers with superior selling ability are significantly better at selecting stocks to buy as well, but the converse does not hold. This asymmetry arises because most academic and practitioner attention focuses on entry signals while exit decisions receive less systematic analysis.

This finding directly supports the research hypothesis: a single composite score that averages buy and sell behavior obscures the most economically meaningful dimension (sell skill). Platform ROI rankings that reward total PnL will promote wallets with strong buy skill even if those wallets give back all gains through poor exits.

### 4.2 Timing vs. Sizing Decomposition

Van Loon (2018) [doi:10.3905/jpm.2018.44.3.025] formalizes the decomposition of the Information Ratio (IR) into:

$$\\text{IR} = \\text{Hit Ratio (timing)} \\times \\text{Win/Loss Ratio (sizing)} \\times \\sqrt{\\text{Breadth}}$$

The hit ratio measures the proportion of directionally correct decisions (timing skill); the win/loss ratio measures whether position sizes are larger when correct (sizing skill). Van Loon demonstrates empirically that **timing skill is approximately twice as important as sizing skill** in generating positive risk-adjusted returns. Critically, positive IRs are achievable even with majority-wrong decisions if position sizing is disciplined enough.

Applied to DeFi wallets: a wallet with 40% hit rate but 3:1 win/loss ratio outperforms a wallet with 60% hit rate and 1.2:1 win/loss ratio, yet naive PnL-based ranking would conflate them.

### 4.3 Skill Persistence and Bayesian Attribution

Berk and van Binsbergen (2015) [doi:10.1016/j.jfineco.2015.05.002] measure mutual fund skill using AUM-adjusted alpha (value added in dollars) rather than return-based alpha. Skilled managers attract capital, which erodes per-unit returns—the standard performance metric therefore underestimates aggregate skill. The paper uses a Bayesian hierarchical framework with informative priors derived from cross-sectional distribution of managers.

Kosowski et al. (2006) [doi:10.1016/j.jfineco.2005.12.009] apply a Bayesian and bootstrap approach to hedge fund performance. Bootstrap simulations of 10,000 runs under the null hypothesis of zero skill establish a benchmark distribution; top-performing funds are evaluated against this null. **The top decile of hedge funds demonstrates alpha that cannot be attributed to sampling variation.** This provides the methodological template for distinguishing lucky from skilled wallets.

Fama and French (2010) [doi:10.1111/j.1540-6261.2010.01598.x] apply the bootstrap to mutual funds and find the opposite: *most* active managers lack genuine skill after adjusting for multiple comparisons. Combined with Kosowski et al., the picture is that a small tail of managers are genuinely skilled while the bulk are not—exactly the structure expected in crypto wallet populations.

______________________________________________________________________

## 5. Copy Trading Dynamics and Crowd Effects

### 5.1 Social Trading Networks

Liu, Yang, and Tan (2023) [doi:10.2139/ssrn.4528456] study the coevolution of trader networks on eToro, finding that **platform ranking and UI strongly influence follower-leader link formation**, with financial performance and social communication jointly determining network dynamics. Followers tend to connect with traders that are prominently displayed, not necessarily the most skilled. This has direct implications for wallet scoring systems: if a platform promotes wallets based on PnL rankings, followers will concentrate on those wallets regardless of whether the skill is persistent.

### 5.2 Meme Coin Copy Trading and Manipulation

The adversarial dimension is addressed by Gao et al. (2026) [2601.08641], who build a multi-agent LLM system to detect manipulative bots in meme coin copy-trading environments. Manipulative bots exploit copy-trading by front-running followers' replication of leader trades. The system achieves 3% average copier return under adversarial conditions through chain-of-thought reasoning that detects position concealment and sentiment fabrication. This paper establishes that **wallet scoring systems must be robust to strategic manipulation** by wallets gaming the scoring metric.

Perseus (Xu et al., 2025) [2503.01686] identifies masterminds behind pump-and-dump schemes by tracking coordinated wallet clusters. Wallets can achieve high PnL rankings by coordinating P&D schemes—another attack vector against naïve scoring.

______________________________________________________________________

## 6. Luck vs. Skill in Heavy-Tailed Environments

The M6 Investment Challenge analysis (Papaioannou et al., 2024) [2412.04490] demonstrates that **extreme Sharpe ratios in investment competitions are largely explainable by chance** when accounting for the number of participants. Strategic adversarial positioning—adjusting weights to beat competitors' portfolios—further decouples rankings from genuine skill. This finding is especially concerning for crypto wallet scoring: with millions of active wallets on Solana and Ethereum, some wallets will exhibit extraordinary past returns purely by chance.

The VC analogy (Choi et al., 2025) [2605.03980] reinforces this: when outcomes are dominated by rare extreme events, VC portfolio distributions are "remarkably close to their random benchmarks," with the right tail statistically indistinguishable from random allocation. Crypto token markets exhibit similar fat-tailed return distributions, making luck-skill separation critical.

______________________________________________________________________

## 7. Gap Analysis

### Gap 1: No Side-Aware Skill Decomposition for Crypto Wallets

The finance literature conclusively demonstrates that buy and sell skill are orthogonal dimensions (Lim et al., 2022) and timing/sizing are separately quantifiable (Van Loon, 2018). Yet all existing crypto wallet scoring—zScore, Nansen Smart Money, DeBankPro—uses a single composite PnL or return metric. **No published work decomposes crypto wallet skill into buy skill, sell skill, timing skill, sizing skill, or regime-specific skill.** A wallet could rank highly by making one spectacular buy during a bull market while systematically leaving gains on the table through poor exits—and existing scoring systems would reward this wallet equally to one with balanced, persistent multi-dimensional skill.

### Gap 2: No Bayesian Posterior Skill Scores with Confidence Intervals

Kosowski et al. (2006) and Berk and van Binsbergen (2015) establish that point performance estimates are unreliable due to sampling variability, especially with short track records. Bootstrap simulations or Bayesian hierarchical models are necessary to distinguish lucky from skilled performers. Every existing crypto wallet scoring system produces a point estimate. **No system produces a posterior skill distribution or confidence interval for any skill dimension.** Without uncertainty quantification, a wallet with 20 trades and 80% win rate scores identically to one with 200 trades and 80% win rate—despite vastly different statistical reliability.

### Gap 3: No Crowd-Adjusted Skill Correction

Social trading literature (Liu et al., 2023) shows that when many followers copy a leader, the leader's edge degrades—subsequent followers face slippage, front-running by bots (Gao et al., 2026), and price impact from the crowd's collective action. A wallet's historical skill score may reflect edge that has already been arbitraged away by the time a new follower copies it. **No existing wallet scoring system discounts skill estimates based on crowding or copy-follower count.** Expected future value if copied with delay requires not just a skill estimate but a crowd-adjusted decay function.

### Gap 4: No Leverage-Normalized Skill Score for Perpetual Traders

Perpetual DEX research (Chen et al., 2024; Chitra, 2026) documents that traders use leverage ranging from 1x to 100x+ on platforms such as Hyperliquid and Jupiter. All existing wallet scoring systems—including the composite formula deployed in our source dataset (`risk_reward * 0.25 + win_loss_holding_time * 0.25 + win_loss_roi * 0.25 + win_pct * 0.25`)—treat ROI as a raw ratio without leverage normalization. A wallet generating 50% ROI at 50x leverage has the same notional risk exposure as one generating 1% ROI at 1x leverage, yet earns a higher composite score. **No published work adjusts perpetual wallet performance scores for leverage consumed, despite leverage being the primary risk dimension in perpetuals markets.**

______________________________________________________________________

## 8. Conclusion

The literature converges on four conclusions relevant to elite wallet scoring:

1. **Skill is multi-dimensional**: Buy/sell asymmetry (Lim et al., 2022) and timing/sizing orthogonality (Van Loon, 2018) are robust findings in traditional finance with direct applicability to on-chain perpetuals trading.

1. **Skill needs uncertainty quantification**: In heavy-tailed environments, most apparent skill is luck (Fama-French 2010; Papaioannou 2024; Choi 2025). Bayesian or bootstrap methods (Kosowski 2006; Berk-van Binsbergen 2015) are necessary for reliable identification of genuinely skilled wallets.

1. **Copied skill decays**: Platform dynamics (Liu et al., 2023) and adversarial bots (Gao et al., 2026) erode the value of publicly ranked wallets. A crowd-aware scoring function is a prerequisite for actionable copy-trading recommendations.

1. **Perpetual DEX microstructure introduces leverage-specific risks**: Adverse selection (Barone & Lillo, 2026), ADL shocks (Chitra, 2026), and exchange-design behavioral biases (Chen et al., 2024) are unique to perp markets and absent from existing wallet scoring literature—which focuses on spot DEX or CEX data.

No existing on-chain wallet scoring system addresses all four. This constitutes a clear research gap with direct commercial value: a side-aware, leverage-adjusted, Bayesian wallet skill score for perpetual DEX traders would be the first of its kind in the academic literature.

______________________________________________________________________

## References

See `references.bib` for full BibTeX entries.

| Key | Paper |
|-----|-------|
| [zScore2025] | Anon et al. (2025). Deep Reputation Scoring in DeFi. arXiv:2507.20494 |
| [OnChainFlows2024] | He et al. (2024). Return and Volatility Forecasting Using On-Chain Flows. arXiv:2411.06327 |
| [ILS2026] | Nechepurenko (2026). Per-Market Information Leakage and Order-Flow Skill. arXiv:2605.02287 |
| [ILSdl2026] | Saguillo et al. (2026). Empirical Evaluation of Deadline-Resolved ILS. arXiv:2605.02286 |
| [Polymarket2026] | Foley et al. (2026). Anatomy of a Blockchain Prediction Market. arXiv:2603.03136 |
| [ForesightFlow2026] | Xu et al. (2026). ForesightFlow. arXiv:2605.00493 |
| [TimingSizing2018] | Van Loon (2018). Timing versus Sizing Skill. JPM. doi:10.3905/jpm.2018.44.3.025 |
| [SellSkill2022] | Lim et al. (2022). Fund manager skill: selling matters more! Rev. Quant. Finance Acc. doi:10.1007/s11156-022-01065-9 |
| [BerkBinsbergen2015] | Berk & van Binsbergen (2015). Measuring skill in the mutual fund industry. JFE. doi:10.1016/j.jfineco.2015.05.002 |
| [Kosowski2006] | Kosowski et al. (2006). Do hedge funds deliver alpha? JFE. doi:10.1016/j.jfineco.2005.12.009 |
| [FamaFrench2010] | Fama & French (2010). Luck versus Skill. JF. doi:10.1111/j.1540-6261.2010.01598.x |
| [M6Challenge2024] | Papaioannou et al. (2024). M6 Investment Challenge. arXiv:2412.04490 |
| [VCRandom2025] | Choi et al. (2025). Do Venture Capitalists Beat Random Allocation? arXiv:2605.03980 |
| [SocialTrading2023] | Liu, Yang & Tan (2023). Coevolution of Trader Networks. SSRN:4528456 |
| [MemeCoinCopy2026] | Gao et al. (2026). Resisting Manipulative Bots in Meme Coin Copy Trading. arXiv:2601.08641 |
| [Perseus2025] | Xu et al. (2025). Perseus: Tracing Pump-and-Dump Masterminds. arXiv:2503.01686 |
| [DeFiFraud2023] | Zhu et al. (2023). AI-powered Fraud Detection in DeFi. arXiv:2308.15992 |
| [MLBlockchain2024] | Zheng et al. (2024). ML for Blockchain Data Analysis. arXiv:2404.18251 |
| [IndividualInvestors2013] | Barber & Odean (2013). The Behavior of Individual Investors. doi:10.1016/b978-0-44-459406-8.00022-6 |
| [HedgeFundAlpha2006] | Kosowski, Naik & Teo (2006). Do Hedge Funds Deliver Alpha? doi:10.1016/j.jfineco.2005.12.009 |
| [AdaptiveTrend2025] | Zhang et al. (2025). Systematic Trend-Following. arXiv:2602.11708 |
| [DeFiEvent2025] | Li et al. (2025). Event-Aware Forecasting in DeFi. arXiv:2604.20374 |
| [PerpDEXBehavior2024] | Chen, Ma & Nie (2024). How DEX Designs Shape Traders' Behavior on Perpetual Futures. arXiv:2402.03953 |
| [HyperliquidAdverse2026] | Barone & Lillo (2026). Trading in the Sunshine or in the Shade: Market Impact and Adverse Selection on Hyperliquid. arXiv:2606.15715 |
| [AutodeleveragingADL2026] | Chitra (2026). Autodeleveraging: Impossibilities and Optimization. arXiv:2512.01112 |

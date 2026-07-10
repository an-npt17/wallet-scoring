# Literature Review: Liquidation Burst in DeFi

## Overview

This document provides a structured analysis of 10 research papers examining liquidation dynamics, cascading failures, and systemic risk in Decentralized Finance (DeFi) lending protocols. The papers span theoretical modeling, empirical analysis, and case studies of major liquidation events.

---

## 1. Liquidation Dynamics in DeFi and the Role of Transaction Fees

**Authors:** Agathe Sadeghi & Zachary Feinstein  
**Year:** 2026  
**Source:** arXiv (2602.12104)

### Research Question & Motivation
How do transaction fees in Constant Product Market Makers (CPMMs) affect the security of liquidation mechanisms against predatory price manipulation and Oracle Extractable Value (OEV)?

### Core Methodology
- Dynamic programming to characterize optimal liquidation strategies from a profit-maximizing liquidator's perspective
- Explicit modeling of Oracle Extractable Value (OEV) where liquidators manipulate CPMMs with sandwich attacks
- Derivation of closed-form liquidation bounds
- Analysis of CPMM transaction fees as security parameters

### Key Findings & Contributions
- CPMM transaction fees act as a critical security parameter, not merely reducing but potentially eliminating attacker profits
- Fees serve a dual purpose: compensating liquidity providers and endogenously hardening CPMM oracles against manipulation
- Demonstrated that fees can make manipulations unprofitable beyond a critical threshold
- Proposed an alternative to time-weighted averages or medianization for oracle security

### Limitations & Future Work
- Focuses specifically on CPMM-based oracles; generalizability to other oracle types unexplored
- Assumes rational profit-maximizing attackers; behavioral variations not modeled
- Future work could explore dynamic fee mechanisms and multi-block attack strategies

---

## 2. Shock Propagation in Decentralized Lending Networks

**Authors:** Natkamon Tovanich, Stefania Marcassa, Stefan Kitzler, Christos Makridis, Julien Prat  
**Year:** 2025  
**Source:** SSRN (5380164)

### Research Question & Motivation
How do financial shocks propagate through decentralized lending networks, and what network properties predict contagion?

### Core Methodology
- Novel dataset from Compound protocol (Jan 2020 - Jun 2024)
- Construction of daily balance sheets for users and pools
- Modeling liability network structure
- Application of DebtRank algorithm to simulate distress cascades
- Network topology analysis

### Key Findings & Contributions
- Network topology is the most robust predictor of contagion, outperforming standard financial indicators
- Systemic risk varies over time and across asset types
- Stablecoin pools exhibit more concentrated and persistent vulnerabilities than crypto-asset pools
- Demonstrated need for topology-aware risk monitoring in algorithmic credit systems

### Limitations & Future Work
- Limited to Compound protocol; cross-protocol interactions not fully captured
- Static network assumptions may miss dynamic user behavior
- Future work should incorporate cross-protocol dependencies and real-time monitoring

---

## 3. Liquidation Mechanisms and Price Impacts in DeFi

**Authors:** Phoebe Tian & Yu Zhu  
**Year:** 2025  
**Source:** Bank of Canada Staff Working Paper 25-12

### Research Question & Motivation
How do different liquidation mechanisms (fixed-spread vs. auction-based) affect price impacts in DeFi lending?

### Core Methodology
- Theoretical framework modeling liquidator participation costs
- Empirical analysis of Ethereum blockchain data
- Comparison of fixed-spread and auction-based liquidation mechanisms
- Price impact measurement across multiple DEXs

### Key Findings & Contributions
- Auctions mitigate price impact when liquidator participation cost is low
- Auctions amplify price impact when participation cost is high
- Auction-based liquidations lead to smaller price drops by increasing competition
- Competition raises collateral prices and reduces liquidation volumes
- Emphasized importance of liquidation design in promoting market stability

### Limitations & Future Work
- Analysis limited to Ethereum-based protocols
- Does not account for cross-chain liquidation dynamics
- Future work could explore hybrid mechanisms and dynamic participation costs

---

## 4. DeFi Lending: Returns, Leverage, and Liquidation Risk

**Authors:** Jonathan Chiu (Bank of Canada) & Furkan Danisman (University of Toronto)  
**Year:** 2026  
**Source:** Bank of Canada Staff Analytical Paper 2026-13

### Research Question & Motivation
How does decentralized lending on Aave V3 function in terms of revenue generation, borrower behavior, and liquidation dynamics?

### Core Methodology
- Transaction-level data analysis from Aave V3 (Jan 2023 - May 2025)
- Revenue model analysis
- Behavioral analysis of leverage and margin trading
- Liquidation dynamics modeling

### Key Findings & Contributions
- Protocol earnings concentrated in few tokens (WETH, USDT, USDC = 83% of earnings)
- Margin trading accounts for ~20% of borrowing volume despite overcollateralization requirements
- Liquidations occur in concentrated waves; 10 largest waves = 80% of liquidated volume
- Only 4 tokens (WETH, wstETH, WBTC, weETH) account for 90% of liquidated value
- Sharp ETH price drops identified as primary liquidation trigger
- Borrowers lose 10-30% of collateral during liquidations
- DeFi lending is operationally viable but faces capital efficiency and systemic fragility constraints

### Limitations & Future Work
- Limited to single protocol (Aave V3)
- Does not capture cross-protocol risk propagation
- Future work should explore regulatory implications and cross-chain dynamics

---

## 5. From Risk to Rescue: An Agentic Survival Analysis Framework

**Authors:** Fernando Spadea & Oshani Seneviratne (Rensselaer Polytechnic Institute)  
**Year:** 2026  
**Source:** arXiv (2604.14583)

### Research Question & Motivation
Can autonomous agents using survival analysis proactively prevent liquidations in DeFi protocols?

### Core Methodology
- Survival analysis (Cox proportional hazards model) for time-to-event prediction
- Counterfactual optimization loop for intervention selection
- High-fidelity Aave v3 simulator for evaluation
- Numerically stable "return period" metric for risk normalization

### Key Findings & Contributions
- Successfully differentiates between actionable financial risks and negligible "dust" events
- Agent perceives risk, simulates counterfactual futures, and executes protocol-faithful interventions
- Demonstrated ability to prevent liquidations in imminent-risk scenarios where static rules fail
- Zero worsening rate maintained, providing safety guarantee
- "Saving the unsavable" - proactive rather than reactive risk management

### Limitations & Future Work
- Evaluated on historical data; real-time deployment challenges unaddressed
- Does not account for oracle manipulation or extreme network congestion
- Future work should explore multi-protocol coordination and adversarial robustness

---

## 6. Systemic Fragility in Decentralised Markets

**Authors:** Alfred Lehar & Christine A. Parlour  
**Year:** 2022  
**Source:** BIS Working Paper 1062

### Research Question & Motivation
How do third-party liquidations affect protocol risk, collateral risk, and systemic risk in DeFi?

### Core Methodology
- Unique dataset of collateral liquidations on Compound and Aave (~$9B and ~$11B locked respectively)
- Observation of arbitrageur behavior (own inventory vs. flash loans)
- High-frequency price impact analysis across 9 decentralized exchanges
- Return distribution analysis

### Key Findings & Contributions
- Documented temporary and permanent price impacts of collateral liquidations
- Deleveraging leads to lower prices on both DEXs and subsequently off-chain markets
- Negative feedback loops: liquidations → price pressure → more liquidations
- Flash loans enable permissionless liquidation, amplifying systemic fragility
- Consistent with large block trade dynamics in equity markets

### Limitations & Future Work
- Static analysis of historical data; real-time dynamics not captured
- Does not model cross-protocol contagion pathways
- Future work should incorporate network effects and dynamic stability mechanisms

---

## 7. October 10, 2025: The $19 Billion DeFi Liquidation Cascade

**Authors:** Aegis Markets  
**Year:** 2025  
**Source:** Aegis Markets Blog

### Research Question & Motivation
What caused the largest single-day liquidation event in crypto history, and how did infrastructure failures amplify the cascade?

### Core Methodology
- Event analysis of October 10, 2025 crash
- Feedback loop modeling (price drops → liquidations → forced selling → more liquidations)
- Infrastructure stress testing analysis
- Market microstructure examination

### Key Findings & Contributions
- $19.37 billion in leveraged positions liquidated in single day
- 70% of liquidations occurred in 40 minutes (20:50-21:30 UTC)
- $3.21 billion evaporated in single minute (21:15 UTC)
- Liquidation rate accelerated 86x from pre-cascade baseline
- Order book depth collapsed by 98%
- Bitcoin perpetual swap spreads widened 1,321x
- USDe stablecoin depegged to $0.65, amplifying cascade
- Dynamic fees and protocol-owned liquidity proposed as solutions

### Limitations & Future Work
- Case study; generalizability to other crash scenarios unverified
- Does not model potential interventions during cascade
- Future work should explore real-time circuit breakers and cross-exchange coordination

---

## 8. Anatomy of a $285M DeFi Contagion: Stream Finance xUSD Collapse

**Authors:** BlockEden (Dora Noda)  
**Year:** 2025  
**Source:** BlockEden Blog

### Research Question & Motivation
How did Stream Finance's collapse expose systemic vulnerabilities in DeFi's composability and risk management?

### Core Methodology
- Forensic analysis of Stream Finance's xUSD stablecoin collapse
- On-chain data analysis of exposure across protocols
- Incentive structure analysis
- Contagion pathway mapping

### Key Findings & Contributions
- $93 million loss cascaded to $285 million in cross-protocol exposure
- Recursive leverage loops created 4x+ leverage ratios
- Redemption mechanism suspension caused catastrophic depeg (89% collapse)
- Curators had misaligned incentives (earn fees during good times, externalize losses)
- Hybrid CeDeFi models cannot use on-chain tools to fix off-chain problems
- Key lesson: redemption mechanisms are non-negotiable for stablecoin stability

### Limitations & Future Work
- Post-hoc analysis; predictive indicators not developed
- Does not propose formal risk metrics for early warning
- Future work should develop composability risk frameworks and automated circuit breakers

---

## 9. Quantifying Blockchain Extractable Value

**Authors:** Kaihua Qin, Liyi Zhou, Arthur Gervais  
**Year:** 2021 (Published 2022)  
**Source:** IEEE Symposium on Security and Privacy

### Research Question & Motivation
How much value do opportunistic traders extract from DeFi smart contracts, and what are the security implications?

### Core Methodology
- Quantitative analysis of sandwich attacks, liquidations, and DEX arbitrage
- 32 months of blockchain data analysis
- BEV relay system formalization
- Generalized trading bot algorithm development

### Key Findings & Contributions
- Estimated $540.54M USD extracted over 32 months from 11,289 addresses
- Highest single BEV instance: $4.1M USD (616.6x Ethereum block reward)
- First concrete algorithm for generalized trading bots (57,037.32 ETH profit over 32 months)
- BEV relay systems aggravate consensus layer attacks
- Demonstrated BEV deteriorates blockchain consensus security

### Limitations & Future Work
- Historical analysis; evolving MEV landscape not fully captured
- Does not account for Layer-2 solutions and cross-chain MEV
- Future work should explore MEV mitigation strategies and fair ordering mechanisms

---

## 10. The Liquidation Economy

**Author:** Joel Obafemi  
**Year:** 2026  
**Source:** Medium/Blog Publication

### Research Question & Motivation
How has the "liquidation economy" become a structural feature of crypto markets, and who profits from forced selling?

### Core Methodology
- Market structure analysis of perpetual futures and stablecoin dynamics
- Historical comparison of liquidation cycles (2022-2024 vs 2026)
- Analysis of leverage as infrastructure
- Examination of stablecoins as "natural brakes" removal

### Key Findings & Contributions
- Liquidations are core mechanism of crypto price discovery
- Perpetual futures turned leverage into infrastructure
- Stablecoins removed natural market brakes
- 2026 liquidations stem from market structure rather than individual failures
- Multiple $500M-$1B+ cascades in single weeks
- Healthy deleveraging vs. systemic risk breakdown distinction needed

### Limitations & Future Work
- Qualitative analysis; lacks rigorous quantitative modeling
- Does not propose specific regulatory or technical solutions
- Future work should develop formal models of liquidation economy dynamics

---

## Synthesis & Research Gaps

### Common Themes
1. **Feedback Loops**: All papers identify positive feedback loops (liquidations → price drops → more liquidations) as central to cascade dynamics
2. **Infrastructure Fragility**: Current DeFi infrastructure amplifies rather than absorbs shocks
3. **Concentration Risk**: Revenue, collateral, and liquidation activity concentrated in few tokens/protocols
4. **MEV/BEV Exploitation**: Predatory extraction exacerbates liquidation impacts

### Identified Research Gaps
1. **Cross-Protocol Contagion**: Most studies focus on single protocols; inter-protocol risk propagation underexplored
2. **Real-Time Monitoring**: Limited development of early warning systems for cascade detection
3. **Dynamic Risk Management**: Static thresholds dominate; adaptive mechanisms needed
4. **Regulatory Frameworks**: Little work on how regulation could mitigate systemic risk
5. **Layer-2 and Cross-Chain**: Most analysis on Ethereum mainnet; L2 and cross-chain dynamics understudied
6. **Behavioral Modeling**: Rational actor assumptions may not capture panic and herding behavior

### Future Research Directions
- Development of topology-aware risk monitoring systems
- Cross-protocol stress testing frameworks
- Real-time circuit breaker mechanisms
- Adaptive liquidation parameters
- Regulatory sandbox approaches for DeFi stability
- Integration of survival analysis and machine learning for early warning
- Cross-chain liquidation dynamics and coordination

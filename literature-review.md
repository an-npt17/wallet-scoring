# Literature Review: Liquidation Burst in DeFi

## 1. Introduction

Liquidation bursts in Decentralized Finance (DeFi) represent a critical systemic risk where automated liquidation mechanisms, designed to maintain protocol solvency, can trigger cascading failures that amplify market volatility. This review examines 15 research papers covering theoretical modeling, empirical analysis, and case studies of major liquidation events. The literature spans oracle manipulation, MEV extraction, network contagion, and protocol design, revealing both the mechanisms that drive cascades and potential mitigation strategies.

## 2. Theoretical Foundations

### 2.1 Liquidation Dynamics and Transaction Fees

Sadeghi & Feinstein (2026) characterize optimal liquidation strategies from a profit-maximizing liquidator's perspective using dynamic programming. Their key contribution is demonstrating that CPMM transaction fees serve a dual purpose: compensating liquidity providers and endogenously hardening oracles against manipulation. They prove that fees above a critical threshold can completely eliminate Oracle Extractable Value (OEV) attacks, providing closed-form liquidation bounds that establish security parameters for AMM-based oracles.

### 2.2 Liquidation Mechanism Design

Tian & Zhu (2025) compare fixed-spread and auction-based liquidation mechanisms through a theoretical framework and empirical analysis. Their findings reveal a nuanced relationship: auctions mitigate price impact when liquidator participation costs are low, but amplify it when costs are high. The competition effect (more participants driving up liquidation prices) versus the entry effect (more liquidators increasing total liquidation volume) determines which mechanism performs better. This work establishes that liquidation design choices have direct implications for market stability and fire-sale risks.

### 2.3 Ergodic Optimal Liquidations

The ergodic control problem for DeFi liquidations (2026) addresses how decentralized derivatives exchanges should manage disposal of positions accrued through liquidations. By formulating the problem as maximizing long-term average reward subject to inventory penalties, the authors derive closed-form solutions showing the optimal strategy is to dispose of a fraction of inventory per unit time. This approach minimizes price impact and provides a framework for exchanges to optimize insurance pool P&L.

## 3. Empirical Analysis

### 3.1 Aave V3 Lending Dynamics

Chiu & Danisman (2026) provide comprehensive transaction-level analysis of Aave V3, the largest DeFi lending protocol by TVL. Their findings reveal:

- **Revenue Concentration**: Protocol earnings heavily concentrated in WETH, USDT, and USDC (83% of earnings)
- **Leverage Behavior**: Margin trading accounts for ~20% of borrowing volume despite overcollateralization requirements
- **Liquidation Patterns**: Liquidations occur in concentrated waves; the 10 largest waves account for 80% of total liquidated volume
- **Asset Concentration**: Only 4 tokens (WETH, wstETH, WBTC, weETH) account for 90% of liquidated value
- **Borrower Losses**: Realized losses including liquidation penalties and missed price recoveries amount to 10-30% of liquidated value

The paper documents that liquidations are primarily triggered by rapid collateral price declines rather than debt increases, establishing that DeFi lending faces fundamental constraints related to capital efficiency and systemic fragility.

### 3.2 Network Shock Propagation

Tovanich et al. (2025) study shock propagation through Compound's lending network using the DebtRank algorithm. Their analysis of daily balance sheets from January 2020 to June 2024 demonstrates that network topology is the most robust predictor of contagion, outperforming standard financial indicators. Key findings include:

- Stablecoin pools exhibit more concentrated and persistent vulnerabilities than crypto-asset pools
- Systemic risk structure varies over time and across asset types
- Topology-aware risk monitoring is essential for algorithmic credit systems

### 3.3 Systemic Fragility

Lehar & Parlour (2022) analyze collateral liquidations on Compound and Aave, documenting temporary and permanent price impacts across nine decentralized exchanges. Their work establishes the fundamental feedback loop: liquidations → price pressure → more liquidations. They show that flash loans enable permissionless liquidation, amplifying systemic fragility by allowing anyone to become a liquidator without capital requirements.

## 4. Case Studies

### 4.1 October 10, 2025 Cascade

The October 10, 2025 cascade represents the largest single-day liquidation event in crypto history (Aegis Markets, 2025):

- **Scale**: $19.37 billion in leveraged positions liquidated across centralized and decentralized exchanges
- **Speed**: 70% of liquidations occurred in 40 minutes (20:50-21:30 UTC)
- **Intensity**: $3.21 billion evaporated in a single minute (21:15 UTC)
- **Acceleration**: Liquidation rate increased 86x from pre-cascade baseline
- **Infrastructure Collapse**: Order book depth collapsed by 98%, Bitcoin perpetual swap spreads widened 1,321x
- **Stablecoin Impact**: USDe stablecoin depegged to $0.65, amplifying the cascade

The cascade was driven by oracle-dependent liquidation logic creating reflexive feedback loops. Every protocol using price-based liquidation thresholds and oracle-dependent triggers participated in the cascade dynamics.

### 4.2 Stream Finance xUSD Collapse

The Stream Finance collapse (BlockEden, 2025) demonstrates cross-protocol contagion:

- **Initial Loss**: $93 million loss from external fund manager failure
- **Contagion**: Cascaded to $285 million in cross-protocol exposure
- **Depeg**: xUSD collapsed 77% from $1.00 to $0.26
- **Systemic Impact**: Elixir's deUSD lost 98% of value, major lending protocols faced liquidity crises

The collapse exposed critical vulnerabilities: off-chain counterparty risk, oracle hardcoding preventing proper liquidations, and the double-edged nature of DeFi composability. Protocols had hardcoded xUSD's oracle price at $1.00 to prevent cascading liquidations, but this created massive bad debt when the token depegged.

### 4.3 stETH Depeg Cascade

The July 2025 stETH/Aave cascade (OAK Framework) illustrates withdrawal-queue-depth saturation:

- **Trigger**: Single-actor liquidity withdrawal (~$1.7B from Aave's wETH pool)
- **Propagation**: Aave borrow-rate spike → looped-leverage carry-flip → forced deleveraging
- **Queue Saturation**: Beacon Chain validator-exit queue reached 743k ETH
- **Market Impact**: stETH/ETH traded at 0.3-0.6% discount

This case demonstrates that post-Shapella structural fixes do not retire the cascade surface—they retire specific sub-classes while queue-depth-saturation remains operational.

## 5. MEV and Oracle Manipulation

### 5.1 Blockchain Extractable Value

Qin et al. (2021) quantify $540.54M extracted over 32 months through sandwich attacks, liquidations, and DEX arbitrage. Their work establishes that BEV deteriorates blockchain consensus security, with a rational miner with 10% hashrate willing to fork if BEV exceeds 4× the block reward. They introduce the first concrete algorithm for generalized trading bots, demonstrating application-agnostic transaction replay.

### 5.2 Speculative Oracle Extractable Value

Sevim & Torres (2026) identify speculative OEV across Layer-2 blockchains. On October 10, 2025, they detected 64 speculative liquidators on Aave (57% of all detected liquidators) and 831 successful speculative liquidations across Arbitrum, Base, and Optimism. Their analysis reveals that independent Chainlink DONs consume identical off-chain price data nearly simultaneously yet publish updates at different times, creating statistically predictable cross-chain exploitation windows.

### 5.3 The Liquidation Economy

Obafemi (2026) analyzes the structural features of the "liquidation economy":

- **Leverage as Infrastructure**: Perpetual futures turned leverage into a structural feature
- **Natural Brakes Removed**: Stablecoins eliminated traditional market circuit breakers
- **Concentration**: 569 bots compete for liquidations, but 91% are unprofitable
- **MEV Impact**: Chainlink SVR has recaptured ~$16M in liquidation-related MEV from Aave

## 6. Mitigation Strategies

### 6.1 Dynamic Fees and Protocol-Owned Liquidity

The October 10 cascade analysis suggests dynamic fee hooks that adjust based on volatility can protect LPs and reduce cascade severity. Protocol-owned liquidity hooks create permanent positions that cannot be withdrawn during stress events, providing a floor of liquidity depth.

### 6.2 Agentic Liquidation Prevention

Spadea & Seneviratne (2026) propose survival analysis agents that proactively prevent liquidations. Using Cox proportional hazards models, their agent differentiates between actionable financial risks and negligible events, executing protocol-faithful interventions to prevent "unsavable" liquidations with zero worsening rate.

### 6.3 Oracle State Synchronization

Oraclizer (2025) proposes continuous state synchronization to eliminate OEV at its source. By replacing discrete price updates with atomic state updates and preemptive lock mechanisms, the approach theoretically eliminates the temporal arbitrage windows that MEV bots exploit.

## 7. Research Gaps

### 7.1 Cross-Protocol Contagion Modeling
Most studies focus on single protocols (Aave, Compound). The Stream Finance case demonstrates $93M losses cascading to $285M across protocols, but formal models of cross-protocol risk propagation remain underdeveloped.

### 7.2 Real-Time Cascade Prediction
Current approaches are reactive (triggered by price drops). While survival analysis shows promise (Spadea & Seneviratne, 2026), scalable real-time prediction systems that capture cascade dynamics before they occur are needed.

### 7.3 Adaptive Liquidation Mechanisms
Fixed-spread vs. auction mechanisms are studied separately. Research on hybrid mechanisms that dynamically adjust based on market conditions, participation costs, and systemic risk indicators is limited.

### 7.4 Cross-Chain Liquidation Dynamics
Most research focuses on Ethereum mainnet. Liquidation behavior on L2 rollups, cross-chain MEV opportunities, and coordinated liquidation across chains are understudied despite evidence of cross-chain exploitation windows (Sevim & Torres, 2026).

### 7.5 Oracle Design for Cascade Resilience
Oracle manipulation as an MEV vector is well-documented, but oracle architectures that provide timely price feeds while minimizing cascade amplification potential are needed. The tension between oracle latency and security requires novel approaches.

### 7.6 Systemic Risk Metrics
DebtRank applied to DeFi networks (Tovanich et al., 2025) shows topology matters, but real-time systemic risk monitoring that captures cascade potential across interconnected protocols remains undeveloped.

## 8. Future Research Directions

1. **Cross-Protocol Stress Testing**: Frameworks for evaluating systemic risk across interconnected DeFi protocols
2. **Real-Time Circuit Breakers**: Mechanisms that can pause or slow liquidations during cascade events without compromising protocol solvency
3. **Adaptive Risk Parameters**: Liquidation thresholds, bonuses, and oracle update frequencies that adjust based on market conditions
4. **Machine Learning for Prediction**: Models that predict liquidation cascades before they occur using on-chain data
5. **Regulatory Frameworks**: Approaches to regulating DeFi stability without undermining decentralization
6. **Cross-Chain Coordination**: Protocols for managing liquidation dynamics across L1 and L2 environments

## 9. Conclusion

The literature reveals that liquidation bursts in DeFi are not isolated events but structural features of current protocol designs. The feedback loops between liquidations, price impacts, and oracle updates create systemic fragility that can be triggered by single events (Stream Finance) or macro shocks (October 10, 2025). While mitigation strategies exist—dynamic fees, protocol-owned liquidity, agentic prevention—the fundamental tension between protocol solvency and market stability remains unresolved. Future research must address cross-protocol contagion, real-time prediction, and adaptive mechanisms to build a more resilient DeFi ecosystem.

---

## References

See `references.bib` for complete BibTeX entries.

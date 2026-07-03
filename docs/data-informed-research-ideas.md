# Data-Informed Research Ideas
## Wallet Scoring Thesis — Revision After Data Access

**Date:** 2026-07-03  
**Status:** Active — revising research-proposal.md with empirical grounding  
**Data source:** `perpetuals_knowledge_graph` MongoDB, exported as `logs.json` (~40M records)

---

## What the Data Contains (Key Facts)

The `logs` collection is a perp-position event log, not a DEX swap log. Each document is one
lifecycle event (Open / Close / Deposit / Withdraw / Liquidate) for one perpetuals position:

```
ownerAccount   — wallet address
positionKey    — position identifier (wallet_asset_side)
action         — Open | Close | Deposit | Withdraw | (Liquidate in data, not in schema enum)
asset          — SOL, ETH, BTC, etc.
side           — Long | Short
price          — execution price at event time
sizeUsd        — notional position size
collateralUsd  — margin deposited
leverage       — sizeUsd / collateralUsd
timestamp      — epoch seconds
platform       — jupiter, hyperliquid, gmx-v2, myx-finance, apx-finance
chain          — solana, hyperliquid, arbitrum, ethereum, bsc
```

**Crucially**: the `closed_positions` collection has `realizedPnl` per position — actual closed
PnL without reconstruction. The `daily_trader_rankings` collection has daily snapshots of the
existing composite score (the baseline we need to beat).

The **existing baseline score** formula (from the code):
```
score = risk_reward_ratio * 0.25
      + win_loss_holding_time_ratio * 0.25
      + win_loss_roi_ratio * 0.25
      + winning_percentage * 0.25
```
This is a single composite with equal weights — precisely the design flaw the proposal targets.

---

## Research Proposal vs. Data Reality

| Proposal assumption | Data reality | Impact |
|---------------------|--------------|--------|
| "DEX swap data (Uniswap, Raydium, Jupiter)" | Perpetuals position logs — NOT spot swaps | Methodology pivots to perp-specific signals |
| "Entry timing = buy skill" | Entry = Open event with `price` + `side` | Direct operationalization ✓ |
| "Exit quality = sell skill" | Exit = Close event with `price` | Direct operationalization ✓ |
| "Crowd follower heuristic (same-block copy)" | No social graph in this DB — need external | Crowd-adjustment is harder, needs different data |
| "Multi-chain: Solana + Ethereum DEX" | Multi-chain perps: Jupiter + Hyperliquid + GMX | Scope narrows to perp traders (cleaner RQ) |
| "500K+ wallets" | Unknown until script 01 runs — likely fewer | Bayesian prior becomes more important |

---

## Idea 1 (Core): Side-Aware Perp Skill Score [ORIGINAL PROPOSAL]

**Status:** Still valid — data directly supports this.

**Operationalization with real data:**

- **Long skill (buy skill)**: For each `Open Long` event, compute forward price at matching
  `Close Long` event. `long_alpha = (close_price - open_price) / open_price - asset_benchmark_return`
- **Short skill (sell skill)**: For each `Open Short` event, compute `short_alpha = (open_price - close_price) / open_price - (- asset_benchmark_return)`
- **Benchmark**: Use same-period same-asset median return across all wallets in the DB

**New insight from data**: The `positionKey` directly links all events for one position, so
position lifecycle reconstruction is exact — no heuristic matching needed. This is cleaner than
the proposal assumed.

**Testable RQ from script 05**: If `pearson_r(long_win_rate, short_win_rate) < 0.3` across
wallets, Long and Short skill are empirically orthogonal → confirms decomposition is needed.

---

## Idea 2 (Novel): Leverage-Adjusted Skill Score

**Motivation from data**: The `leverage` field (range: 1x to 100x+) is available per event.
The current baseline score does not adjust for leverage. A wallet making 50% ROI at 20x
leverage has far less skill than one making 40% ROI at 3x leverage.

**Proposed metric:**

```
leverage_adjusted_roi = realized_pnl / (collateralUsd * sqrt(leverage))
```

The `sqrt(leverage)` penalty reflects that leverage amplifies both gains and losses; a skilled
trader uses leverage efficiently, not maximally.

**Alternative**: Sharpe-style adjustment:
```
risk_adjusted_alpha = mean(daily_roi) / std(daily_roi)
```
using the `accounts.roiLogs` daily time series.

**Novelty**: No existing perp wallet scoring uses leverage-normalized returns. The current
system rewards high-leverage gamblers equally with disciplined low-leverage traders.

**Script**: `scripts/06_leverage_sizing_skill.py` → compare raw WR vs leverage-adjusted WR rankings.

---

## Idea 3 (Novel): Sizing Skill from Position Event Sequences

**Motivation from Van Loon (2018)**: Timing skill (hit ratio) × sizing skill (win/loss ratio) = IR.
Sizing skill = does the wallet put more capital on larger expected-value trades?

**Data source**: `sizeUsd` at Open events per wallet. Within each wallet, large vs small trades.

**Operationalization (script 06)**:
```
per wallet:
  median_size = median(sizeUsd)
  large_trades = trades where sizeUsd >= median_size
  small_trades = trades where sizeUsd < median_size
  sizing_skill = win_rate(large_trades) - win_rate(small_trades)
```
Positive sizing_skill → wallet bets bigger on winning ideas (good sizing).
Negative sizing_skill → wallet bets bigger on losing ideas (martingale / averaging down).

**Secondary test**: Deposit events after an Open event = adding collateral to an open position.
If deposits happen after price moves against the position → averaging down (bad sizing).
If deposits happen after price moves in the wallet's favor → pyramiding (good sizing).

This cross-reference of Deposit timing with price direction is feasible with the `logs` data.

---

## Idea 4 (Novel): Cross-Asset Skill Transfer

**Motivation**: No published paper tests whether perp trading skill generalizes across assets.
The existing `tradedAssets` field in `accounts` and per-asset PnL in `closed_positions` enable this.

**Research question**: Is a wallet's win rate on SOL perps predictive of its win rate on ETH perps?

**Hypothesis A (skill is general)**: r(SOL_WR, ETH_WR) > 0.5 → single multi-asset score sufficient.  
**Hypothesis B (skill is asset-specific)**: r(SOL_WR, ETH_WR) < 0.3 → asset-conditional scores needed.

**Contribution**: If Hypothesis B holds, this motivates a matrix of skill scores `θ_{w,a}` (wallet × asset)
rather than a single `θ_w` — a structural extension of the proposal's Bayesian model.

**Script**: `scripts/07_asset_skill_transfer.py`

---

## Idea 5 (Novel): Liquidation Avoidance as Risk Intelligence Signal

**Motivation**: The `logs` data contains Liquidate events (even though the schema's `LogAction`
enum doesn't list it — the actual data does have liquidation records). Liquidation means the
protocol forcibly closed the position at a loss because collateral was exhausted.

**Proposed metric**:
```
liquidation_rate = n_liquidations / (n_closes + n_liquidations)
```

**Research angle**: A wallet that achieves high returns via extreme leverage but gets liquidated
frequently is fundamentally different from a wallet achieving similar returns through disciplined
risk management. The composite score currently treats both identically (both contribute
positively to win_loss_roi_ratio if their surviving trades are profitable).

**Bayesian model extension**: Include `liquidation_rate` as a negative evidence dimension:
```
θ_w^{risk} = base_skill - λ * liquidation_rate
```
where λ is a learned penalty coefficient.

---

## Idea 6: Temporal Skill Persistence (Bayesian Core — Refined)

**Motivation**: The `daily_trader_rankings` collection has one snapshot per day with
`total_traders_analyzed` and the ranked trader list. The `accounts.logs` dict has daily PnL.

**Data structure of `accounts.logs`**: Based on `DailyActiveAccountsConfig.dailyActivateAccountsLogs`
pattern and the schema `logs: dict[str, float]`, this is likely `{"2025-12-01": 150.5, ...}`.

**Persistence test (Fama-French 2010 bootstrap)**:
1. For each wallet, split its daily PnL series into first half / second half.
2. Test: does first-half Sharpe predict second-half Sharpe?
3. Bootstrap under null (shuffle daily returns) to get null distribution.
4. Wallets in top decile whose alpha exceeds 95th percentile of bootstrap null → "genuinely skilled."

**This is RQ2 of the proposal** — now directly operationalizable from `accounts.logs`.

**Script to add**: `scripts/08_skill_persistence.py` using the `accounts` collection's daily logs.

---

## Idea 7: Platform Migration and Regime-Conditional Skill

**Motivation**: Wallets active on multiple platforms (Jupiter + Hyperliquid + GMX-v2) allow
testing whether skill is platform-specific or universal. This is testable because `platform`
and `chain` fields exist per position.

**Observation**: Hyperliquid has ~29M perp events; Jupiter has ~16M; GMX-v2 and Myx are ~1.6M.
Some wallets appear on multiple chains via different wallet addresses (cross-chain traders).

**Research angle**: If a wallet scores highly on Jupiter (Solana) but poorly on Hyperliquid,
the platform's design (fee structure, liquidation mechanics, oracle speed) may explain the gap.
Platform-conditioned skill isolation is novel.

---

## Priority Matrix

| Idea | Novelty | Feasibility with data | Proposal alignment | Priority |
|------|---------|----------------------|-------------------|----------|
| 1. Side-aware decomposition | Medium | High (direct) | Core | **P1** |
| 2. Leverage-adjusted skill | High | High (direct) | Extension | **P1** |
| 3. Sizing skill from Deposit/Withdraw | High | Medium (complex) | Core dimension | **P2** |
| 4. Cross-asset transfer | Very high | High (direct) | New structural | **P2** |
| 5. Liquidation avoidance | Medium | High (direct) | Risk extension | **P2** |
| 6. Skill persistence (Bayesian) | Medium | High (logs field) | Core RQ2 | **P1** |
| 7. Platform migration | Medium | Medium | Regime extension | **P3** |

---

## Recommended Next Steps

### Immediate (run scripts, gather empirical facts)

```bash
# Requires MONGO_SOURCE_URL set
export MONGO_SOURCE_URL="mongodb://..."

uv run python scripts/01_accounts_overview.py      # population size, PnL stats
uv run python scripts/02_closed_positions_pnl.py   # Long vs Short PnL breakdown
uv run python scripts/03_rankings_baseline.py      # existing score analysis
uv run python scripts/04_trade_sufficiency.py      # Bayesian feasibility
uv run python scripts/05_side_asymmetry.py         # RQ1 empirical test
uv run python scripts/06_leverage_sizing_skill.py  # sizing skill (uses local logs.json)
uv run python scripts/07_asset_skill_transfer.py   # cross-asset correlation
```

### Key empirical facts needed before thesis commits to methodology

1. **How many wallets have ≥20 closed trades?** (script 04 answers this)
   - If <10K wallets → Bayesian hierarchical model is essential (limited data)
   - If >100K wallets → frequentist approaches are viable as well

2. **Is long_WR correlated with short_WR?** (script 05 answers this)
   - r < 0.3 → confirms side-aware decomposition hypothesis → proceed with Idea 1
   - r > 0.5 → revise hypothesis → focus on leverage/sizing instead

3. **Are score components already correlated?** (script 03 answers this)
   - If the 4 components of the baseline score are highly correlated → current system is
     even more redundant than claimed → stronger motivation for decomposition

4. **What does `accounts.logs` actually contain?** (needs a sample query)
   - If it's daily PnL series → Idea 6 (persistence) is directly feasible
   - If it's a different dict → adapt accordingly

### Structural revision to proposal

Given perp data (not DEX spot data), revise Section 4 (Data) of the proposal:
- Remove Dune Analytics / Flipside as data sources (already have the DB)
- Update "Chain" to list platforms: Jupiter, Hyperliquid, GMX-v2, Myx Finance
- Update "Scale" based on actual wallet count from script 01
- Add `accounts.logs` daily time series as the persistence validation signal
- Crowd-adjustment (RQ3) remains the hardest: no follower graph in DB → either use
  `daily_trader_rankings` appearance frequency as a crowd proxy, or scope out RQ3

---

## Notes on Data Constraints

- **No DEX swap data here**: The `logs` collection is perp events only. Spot DEX skill
  cannot be measured from this DB alone.
- **No social graph**: Crowd-follower relationships are not in the DB. RQ3 (crowd adjustment)
  would require external data (Nansen, GMGN follower API) or a proxy.
- **Cross-chain wallet identity**: The same physical trader may use different wallets on
  different chains. `accounts._id = {platform}_{chain}_{address}` — wallets are platform-scoped,
  not cross-platform unified. This fragmentation limits cross-platform analysis.
- **Liquidate not in schema enum**: The `LogAction` enum lists Open/Close/Deposit/Withdraw
  but the actual data may also contain Liquidate events. Verify in script 06 outputs.

# Database Schema Reference
## perpetuals_knowledge_graph — Research Data Source

**Connection:** env var `MONGO_SOURCE_URL`  
**Database:** `perpetuals_knowledge_graph`  
**Source system:** market-trading-tracker ETL pipeline  
**Last verified:** 2026-07-03  

---

## Collections Overview

| Collection | Role in Research | Est. Size |
|------------|-----------------|-----------|
| `logs` | Raw event log — primary data source | ~40M docs |
| `closed_positions` | Realized PnL per completed position | large |
| `opening_positions` | Currently open positions | medium |
| `accounts` | Per-wallet aggregated stats + daily PnL series | medium |
| `daily_trader_rankings` | Existing baseline composite score, daily snapshots | small |
| `trader_features` | Bot/human classification per wallet | medium |
| `signals` | Individual trade signals with position detail | large |
| `market_stats` | Chain-level daily market statistics | small |
| `markets` | Perpetual contract registry | small |
| `platforms` | Platform registry | tiny |
| `aggregated_assets` | Market-wide Long/Short breakdown per asset | tiny |

---

## `logs` Collection — PRIMARY RESEARCH DATA

**What it is:** Every lifecycle event for every perpetuals position. One document per on-chain transaction that modifies a position.

**`_id`:** transaction hash (string)

**Python Enum types** (defined in `database/mongo/schema.py`):

```python
class LogAction(str, Enum):
    OPEN     = "Open"
    CLOSE    = "Close"
    DEPOSIT  = "Deposit"
    WITHDRAW = "Withdraw"
    # NOTE: "Liquidate" appears in raw data but is NOT in the enum
    # verify with: db["logs"].distinct("action")

class PositionSide(str, Enum):
    LONG  = "Long"
    SHORT = "Short"

# Platform values (no enum in schema — treated as free str)
# Observed values: "jupiter" | "hyperliquid" | "gmx-v2" | "myx-finance" | "apx-finance"

# Chain values (no enum in schema — treated as free str)
# Observed values: "solana" | "hyperliquid" | "arbitrum" | "bsc" | "ethereum"
```

**Document fields:**

```
_id             : str         — transaction hash (unique per event)
action          : LogAction   — Open | Close | Deposit | Withdraw (+ possibly Liquidate)
asset           : str         — traded asset symbol, e.g. "SOL", "ETH", "BTC", "MATIC"
chain           : str         — "solana" | "hyperliquid" | "arbitrum" | "bsc" | "ethereum"
collateralUsd   : float       — margin deposited at this event (USD)
leverage        : float       — sizeUsd / collateralUsd at Open; 0.0 for Deposit/Withdraw
ownerAccount    : str         — trader wallet address
platform        : str         — "jupiter" | "hyperliquid" | "gmx-v2" | "myx-finance" | "apx-finance"
positionKey     : str         — unique position identifier (links all events for one position)
price           : float       — execution price in USD at this event
side            : PositionSide — Long | Short
sizeUsd         : float       — notional position size in USD (0.0 for Deposit/Withdraw)
timestamp       : int         — epoch seconds
transaction_hash: str         — same as _id
```

### Key Relationships

```
positionKey  →  groups all events for one position (Open, Deposits, Close)
ownerAccount →  groups all positions for one wallet
```

### Action Semantics

| Action | sizeUsd | collateralUsd | leverage | price |
|--------|---------|---------------|----------|-------|
| Open | notional size | initial margin | actual leverage used | entry price |
| Close | 0.0 or partial | 0.0 | 0.0 | exit price |
| Deposit | 0.0 | added collateral | 0.0 | current oracle price |
| Withdraw | 0.0 | removed collateral (negative) | 0.0 | current oracle price |
| Liquidate | remaining size | remaining collateral | prev leverage | liquidation price |

### Platform Coverage

| Platform | Chain | Architecture | Notes |
|----------|-------|-------------|-------|
| `jupiter` | `solana` | GLP-style vAMM | Solana-native, ~16M docs |
| `hyperliquid` | `hyperliquid` | CLOB on-chain | Fully on-chain orderbook, ~29M docs |
| `gmx-v2` | `arbitrum` | GM pool + oracle | Multi-chain, GLV/GM pools |
| `myx-finance` | `bsc` / `ethereum` | Oracle-based | ~1.6M docs |
| `apx-finance` | `bsc` | Oracle-based | Smaller volume |

### Research Mapping

| Research Dimension | Field(s) | Script |
|-------------------|----------|--------|
| Long-skill (buy-side) | `action=Open`, `side=Long`, `price`, → match `Close` `price` | `scripts/05_side_asymmetry.py` |
| Short-skill (sell-side) | `action=Open`, `side=Short`, `price`, → match `Close` `price` | `scripts/05_side_asymmetry.py` |
| Sizing skill (Van Loon) | `sizeUsd` at Open vs win/loss | `scripts/06_leverage_sizing_skill.py` |
| Leverage risk | `leverage` at Open | `scripts/06_leverage_sizing_skill.py` |
| Deposit behavior | `action=Deposit`, `collateralUsd`, timing vs price | `scripts/06_leverage_sizing_skill.py` |
| Liquidation rate | `action=Liquidate` count / total closes | future script |

### Example Document

```json
{
  "_id": "5qcUV97ADeA9...",
  "action": "Open",
  "asset": "SOL",
  "chain": "solana",
  "collateralUsd": 968.69,
  "leverage": 10.9,
  "ownerAccount": "2vYobaDn4U2RjgsktPmUEbvd1jEnt3jYHiBC1giH41bW",
  "platform": "jupiter",
  "positionKey": "EtSrjbUWq4NVG3ysQPbjRQM8dJqcMvH7TNqPo7ijzicq",
  "price": 165.59,
  "side": "Long",
  "sizeUsd": 10493.15,
  "timestamp": 1752242952,
  "transaction_hash": "5qcUV97ADeA9..."
}
```

---

## `closed_positions` Collection

**What it is:** One document per fully closed perpetuals position. Contains ground-truth realized PnL without event reconstruction.

**`_id`:** `{platform}_{chain}_{positionKey}`

```python
class ClosedPosition(Document):
    id             : str          — {platform}_{chain}_{positionKey}
    position_key   : str          — positionKey  (alias)
    owner_account  : str          — ownerAccount (alias)
    asset          : str          — traded asset symbol
    side           : PositionSide — Long | Short
    realized_pnl   : float        — realizedPnl (alias) — authoritative PnL in USD
    last_closed_at : int          — lastClosedAt (alias) — epoch seconds
    platform       : str          — platform identifier
    chain          : str          — chain identifier
```

**Use in research:** Direct source for win/loss classification, PnL by side (RQ1), PnL by asset (cross-asset analysis), PnL by platform. Preferred over PnL reconstruction from `logs`.

---

## `opening_positions` Collection

**What it is:** Currently open positions (not yet closed). Useful for understanding current capital deployment.

**`_id`:** `{platform}_{chain}_{positionKey}`

```python
class OpeningPosition(Document):
    id              : str          — {platform}_{chain}_{positionKey}
    position_key    : str          — positionKey  (alias)
    owner_account   : str          — ownerAccount (alias)
    asset           : str          — traded asset symbol
    side            : PositionSide — Long | Short
    size_usd        : float        — sizeUsd (alias) — current notional size
    entry_price     : float        — entryPrice (alias) — price at position open
    unrealized_pnl  : float        — unrealizedPnl (alias) — mark-to-market PnL
    first_opened_at : int          — firstOpenedAt (alias) — epoch seconds
    platform        : str
    chain           : str
```

**Use in research:** Excludes from closed-trade analysis (no realized PnL yet). Can be used to measure current market exposure per wallet.

---

## `accounts` Collection

**What it is:** Per-wallet aggregated statistics. One document per `{platform}_{chain}_{address}` combination.

**`_id`:** `{platform}_{chain}_{address}`

```
_id                   : str    — {platform}_{chain}_{address}
account               : str    — wallet address
positionKeys          : list[str] — all position keys for this account
openingSizeUsd        : float  — current total open notional (USD)
collateralUsd         : float  — current total collateral (USD)
realizedPnl           : float  — cumulative realized PnL (USD)
unrealizedPnl         : float  — current unrealized PnL (USD)
openingPositionCount  : int    — number of currently open positions
closedPositionCount   : int    — total number of closed positions ← KEY FIELD
profitedPositionCount : int    — number of profitable closed positions
profitableRatio       : float  — profitedPositionCount / closedPositionCount ← win rate
PNL                   : float  — total PnL (realized + unrealized)
ROI                   : float  — PNL / total collateral deposited
lastTradedAt          : int    — epoch seconds of most recent activity
tradedAssets          : list[str] — distinct assets ever traded ← cross-asset analysis
logs                  : dict[str, float] — {date_str: daily_pnl} ← VERIFY STRUCTURE
roiLogs               : dict   — {date_str: daily_roi} ← VERIFY STRUCTURE
platform              : str
chain                 : str
```

**Critical unknowns (verify before building on these):**
- `logs` field actual structure: expected `{"2025-12-01": 150.5, ...}` but unverified
- `roiLogs` field actual structure
- Run: `await db["accounts"].find_one({"logs": {"$exists": True, "$ne": {}}})` to inspect

**Use in research:**
- `closedPositionCount` → Bayesian feasibility (script 04)
- `profitableRatio` → Baseline B4 (win-rate ranking)
- `ROI` → Baseline B3
- `PNL` → Baseline B2
- `tradedAssets` → cross-asset diversification analysis (script 07)
- `logs` daily series → Baseline B5 (Sharpe), skill persistence test (RQ2)

---

## `daily_trader_rankings` Collection

**What it is:** Daily snapshot of the top-trader leaderboard. One document per day.

```
_id                   : ObjectId
date                  : datetime  — midnight UTC
job_run_timestamp     : datetime
total_traders_analyzed: int       — how many accounts were scored that day
top_traders_count     : int       — how many made the ranking
traders               : list[RankingEntry]
created_at            : datetime
timestamp             : int

RankingEntry:
  rank                     : int
  trader_address           : str    — wallet address
  score                    : float  — composite score (0-1)
  total_pnl                : float
  total_volume             : float
  risk_reward_ratio        : float  — component 1
  win_loss_holding_time_ratio: float — component 2
  win_loss_roi_ratio       : float  — component 3
  winning_percentage       : float  — component 4
  total_closed_trades      : int
  winning_trades_count     : int
  losing_trades_count      : int
  average_pnl_per_trade    : float
  average_trade_duration_seconds: float
  total_fees_paid          : float
  most_traded_coin         : str
```

**Composite score formula:**
```
score = risk_reward_ratio * 0.25
      + win_loss_holding_time_ratio * 0.25
      + win_loss_roi_ratio * 0.25
      + winning_percentage * 0.25
```

**Use in research:** Baseline B1. Source for component correlation analysis (script 03). Daily time series enables persistence testing: does a wallet ranked top-10 today remain top-10 in 30 days?

---

## `trader_features` Collection

**What it is:** Bot/human classification per wallet based on behavioral heuristics.

```python
class TradeFeature(Document):
    id                : str   — wallet address
    total_trades      : int
    median_time_delta : float — seconds between trades (-1 if filtered before compute)
    active_hours      : int   — distinct clock-hours (0–23) with any activity
    is_human          : bool  — classification result

# Classification rules (from IdentifyHumanTradersJob):
# is_human = False if ANY of:
#   total_trades < 10            → insufficient history
#   total_trades > 1500          → algorithmic volume
#   active_hours > 18            → 24/7 activity = bot
#   median_time_delta < 60.0     → sub-minute reaction = bot
```

**Use in research:** Filter or stratify wallet population. Skill estimates should be computed separately for human vs bot wallets (bots can game naive PnL-based scores).

---

## `market_stats` Collection

**What it is:** Chain-level aggregated market statistics per day.

```python
# RiskAppetite category labels (derived from token market cap)
class RiskAppetiteCategory(str, Enum):  # not in schema — inferred from data
    EXTREMELY_RISK = "Extremely Risk"   # marketCap < $1M
    HIGH_RISK      = "High Risk"        # $1M–$10M
    RISK           = "Risk"             # $10M–$100M
    MID_CAP        = "Mid Cap"          # $100M–$500M
    LARGE_CAP      = "Large Cap"        # > $500M

class MarketStat(Document):
    id                 : str   — {chainId}_{timeFrame}_{date}
    chain_id           : str   — chainId (alias)
    time_frame         : str   — timeFrame: "1D" | "1W"
    date               : str
    total_volume       : float — totalVolume (alias) — USD perp volume
    market_pnl         : float — marketPnl (alias) — net trader PnL (negative = house wins)
    active_traders     : int   — activeTraders (alias)
    total_trades       : int   — totalTrades (alias)
    token_distribution : list[TokenDistribution]
    whale_behavior     : WhaleBehavior
    updated_at         : int   — updatedAt (alias)
```

**Use in research:** Market regime identification. `marketPnl` as a macro signal: if all traders lose on net, it's a regime where skill is harder to identify. Rolling `marketPnl / totalVolume` as a regime variable for the HMM extension (Section 3.3 of proposal).

---

## `signals` Collection

**What it is:** Individual trade signals with detailed position action metadata.

```
_id               : str    — {chain}_{transactionHash}
wallet            : str
chain             : str
transactionHash   : str
timestamp         : int
detail            : {
  positionKey     : str
  asset           : str
  side            : str
  action          : str
  executionPrice  : float
  sizeDelta       : float
  pnlDelta        : float    ← partial PnL per action (useful for Deposit/Withdraw analysis)
  ...
}
```

**Use in research:** `pnlDelta` gives incremental PnL for each action, enabling more granular skill estimation than only using `realizedPnl` at close.

---

## Local Data Export

The `logs` collection is also exported locally as NDJSON for fast offline analysis:

| File | Contents |
|------|----------|
| `logs.json` | Full export (~40M lines, ~20GB) |
| `data/logs_001.json` ... `data/logs_NNN.json` | Sharded export, 100K records each |

Use `polars.scan_ndjson()` for lazy streaming of the full file. Existing EDA scripts (`eda/01_*.py` through `eda/10_*.py`) use `logs.json` for offline analysis.

---

## Query Patterns

### Get all positions for one wallet
```python
cursor = db["closed_positions"].find({"ownerAccount": wallet_address})
```

### Get wallet stats with sufficient trade history
```python
cursor = db["accounts"].find(
    {"closedPositionCount": {"$gte": 20}},
    {"account": 1, "PNL": 1, "ROI": 1, "profitableRatio": 1, "closedPositionCount": 1}
)
```

### Get Long vs Short PnL for all wallets
```python
pipeline = [
    {"$group": {
        "_id": {"wallet": "$ownerAccount", "side": "$side"},
        "n": {"$sum": 1},
        "total_pnl": {"$sum": "$realizedPnl"},
        "wins": {"$sum": {"$cond": [{"$gt": ["$realizedPnl", 0]}, 1, 0]}}
    }}
]
cursor = db["closed_positions"].aggregate(pipeline)
```

### Get latest ranking snapshot
```python
doc = await db["daily_trader_rankings"].find_one({}, sort=[("date", -1)])
traders = doc["traders"]
```

### Sample accounts for distribution analysis
```python
cursor = db["accounts"].aggregate([
    {"$sample": {"size": 50000}},
    {"$project": {"PNL": 1, "ROI": 1, "profitableRatio": 1, "closedPositionCount": 1}}
])
```

---

## Data Quality Notes

1. **No realized PnL in `logs`**: The `logs` collection does NOT have a PnL field. For accurate PnL, use `closed_positions.realizedPnl`. PnL reconstruction from price differences in `logs` is approximate.

2. **Liquidations in `logs`**: The `LogAction` enum in `database/mongo/schema.py` only lists Open/Close/Deposit/Withdraw. The actual data may contain Liquidate events — verify with `db["logs"].distinct("action")`.

3. **Platform-scoped wallet identity**: `accounts._id = {platform}_{chain}_{address}`. The same physical trader using Jupiter AND Hyperliquid appears as TWO separate accounts. Cross-platform identity linking is out of scope.

4. **Leverage = 0 for non-Open events**: Deposit/Withdraw events always have `leverage = 0.0`. Only Open events carry meaningful leverage values.

5. **`accounts.logs` unverified**: The daily PnL dict structure must be verified before building Baseline B5 (Sharpe ratio) or skill persistence models on it.

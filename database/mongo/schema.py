from datetime import datetime
from enum import Enum

from beanie import Document, Granularity, TimeSeriesConfig
from pydantic import BaseModel, Field

# NOTE: Beanie has a bug in `id` field type hinting
# pyright: reportIncompatibleVariableOverride = false, reportGeneralTypeIssues = false


# ── Enums ─────────────────────────────────────────────────────────────────────


class PositionSide(str, Enum):
    LONG = "Long"
    SHORT = "Short"


class TradeHistorySide(str, Enum):
    LONG = "long"
    SHORT = "short"


class LogAction(str, Enum):
    OPEN = "Open"
    CLOSE = "Close"
    DEPOSIT = "Deposit"
    WITHDRAW = "Withdraw"


class StopReason(str, Enum):
    SL = "sl"
    TP = "tp"
    TIME = "time"


# ── Nested models ─────────────────────────────────────────────────────────────


class SizeStats(BaseModel):
    long: float
    short: float
    long_percentage: float = Field(alias="longPercentage")
    short_percentage: float = Field(alias="shortPercentage")
    dominant_side: PositionSide = Field(alias="dominantSide")


class TierStats(BaseModel):
    long_count: int = Field(alias="longCount")
    short_count: int = Field(alias="shortCount")
    long_count_percentage: float = Field(alias="longCountPercentage")
    short_count_percentage: float = Field(alias="shortCountPercentage")
    long_size: float = Field(alias="longSize")
    short_size: float = Field(alias="shortSize")
    long_size_percentage: float = Field(alias="longSizePercentage")
    short_size_percentage: float = Field(alias="shortSizePercentage")
    dominant_side: PositionSide = Field(alias="dominantSide")


class AggregatedTiers(BaseModel):
    small: TierStats
    medium: TierStats
    large: TierStats


class AggregatedTraders(BaseModel):
    long: int
    short: int
    long_percentage: float = Field(alias="longPercentage")
    short_percentage: float = Field(alias="shortPercentage")


class RankingEntry(BaseModel):
    rank: int
    trader_address: str
    score: float
    total_pnl: float
    total_volume: float
    risk_reward_ratio: float
    win_loss_holding_time_ratio: float
    win_loss_roi_ratio: float
    winning_percentage: float
    total_closed_trades: int
    winning_trades_count: int
    losing_trades_count: int
    average_pnl_per_trade: float
    average_trade_duration_seconds: float
    total_fees_paid: float
    most_traded_coin: str


class TokenDistribution(BaseModel):
    address: str
    symbol: str
    volume: float


class RiskAppetiteCategory(BaseModel):
    extremely_risk: float = Field(alias="Extremely Risk", default=0.0)
    high_risk: float = Field(alias="High Risk", default=0.0)
    risk: float = Field(alias="Risk", default=0.0)
    mid_cap: float = Field(alias="Mid Cap", default=0.0)
    large_cap: float = Field(alias="Large Cap", default=0.0)


class RiskAppetiteFlow(BaseModel):
    whale: RiskAppetiteCategory
    retail: RiskAppetiteCategory


class WhaleBehavior(BaseModel):
    whale_dominance: float = Field(alias="whaleDominance")
    risk_appetite_flow: RiskAppetiteFlow = Field(alias="riskAppetiteFlow")


class TradeOpenAction(BaseModel):
    owner_account: str = Field(alias="ownerAccount")
    transaction_hash: str
    t_trade: int


class TraderDailyHistory(BaseModel):
    date: str
    timestamp: int
    pnl: float
    volume: float
    trades: int
    roi: float | None = None


class TokenPriceMetadata(BaseModel):
    chain_id: str = Field(alias="chainId")
    token_address: str = Field(alias="tokenAddress")


# ── Documents ─────────────────────────────────────────────────────────────────


class Account(Document):
    """Perp trading accounts across platforms. _id = {platform}_{chain}_{address}."""

    id: str
    account: str
    position_keys: list[str] = Field(alias="positionKeys")
    opening_size_usd: float = Field(alias="openingSizeUsd")
    collateral_usd: float = Field(alias="collateralUsd")
    realized_pnl: float = Field(alias="realizedPnl")
    unrealized_pnl: float = Field(alias="unrealizedPnl")
    opening_position_count: int = Field(alias="openingPositionCount")
    closed_position_count: int = Field(alias="closedPositionCount")
    profited_position_count: int = Field(alias="profitedPositionCount")
    profitable_ratio: float = Field(alias="profitableRatio")
    pnl: float = Field(alias="PNL")
    roi: float = Field(alias="ROI")
    traded_assets: list[str] = Field(alias="tradedAssets")
    logs: dict[str, float]

    class Settings:
        name: str = "accounts"


class AggregatedAsset(Document):
    """Market-wide long/short aggregation per asset."""

    id: str
    asset: str
    overall_dominant_side: PositionSide = Field(alias="overallDominantSide")
    size: SizeStats
    tiers: AggregatedTiers
    traders: AggregatedTraders

    class Settings:
        name: str = "aggregated_assets"


class AlphaTrade(Document):
    """Curated alpha trade signals."""

    id: int
    timestamp: int
    asset: str
    entry_price: float = Field(alias="entryPrice")
    leverage: int
    stop_loss: float = Field(alias="stopLoss")
    take_profit: list[float] = Field(alias="takeProfit", default_factory=list)
    side: PositionSide

    class Settings:
        name: str = "alpha_trades"


class ClosedPosition(Document):
    """Fully closed perp positions. _id = {platform}_{chain}_{positionKey}."""

    id: str
    position_key: str = Field(alias="positionKey")
    owner_account: str = Field(alias="ownerAccount")
    asset: str
    side: PositionSide
    realized_pnl: float = Field(alias="realizedPnl")
    last_closed_at: int = Field(alias="lastClosedAt")
    platform: str
    chain: str

    class Settings:
        name: str = "closed_positions"


class Collector(Document):
    """Block-level extraction progress per data collector."""

    id: str
    last_updated_at_block_number: int
    start_extracting_block_number: int

    class Settings:
        name: str = "collectors"


class PlatformListConfig(Document):
    """Config doc listing all active platforms (_id = 'list_platforms')."""

    id: str
    platforms: list[str]

    class Settings:
        name: str = "configs"


class DailyActiveAccountsConfig(Document):
    """Per-platform daily active account counts. _id = {platform}_{chain}_daily_active_accounts."""

    id: str
    platform: str
    chain: str
    daily_activate_accounts_logs: dict[str, int] = Field(
        alias="dailyActivateAccountsLogs"
    )

    class Settings:
        name: str = "configs"


class DailyTraderRanking(Document):
    """Daily top-trader leaderboard snapshot."""

    date: datetime
    job_run_timestamp: datetime
    total_traders_analyzed: int
    top_traders_count: int
    traders: list[RankingEntry]

    class Settings:
        name: str = "daily_trader_rankings"


class HyperliquidPair(Document):
    """Hyperliquid tradeable pairs with max leverage."""

    id: str
    symbol: str
    max_leverage: int = Field(alias="maxLeverage")

    class Settings:
        name: str = "hyperliquid_pairs"


class HyperliquidPriceCluster(Document):
    """Price clusters aggregated over time windows. _id = {symbol}_{cluster_id}."""

    id: str
    avg_price: float
    cluster_id: int
    num_mins: int
    symbol: str
    t_end: int
    t_start: int

    class Settings:
        name: str = "hyperliquid_price_clusters"


class HyperliquidPrice(Document):
    """Minute-level Hyperliquid prices. _id = {symbol}_{timestamp}."""

    id: str
    price: float | None = None
    symbol: str
    timestamp: int

    class Settings:
        name: str = "hyperliquid_prices"


class Log(Document):
    """On-chain perp position events (Open/Close/Deposit/Withdraw). _id = transaction hash."""

    id: str
    action: LogAction
    asset: str
    chain: str
    collateral_usd: float = Field(alias="collateralUsd")
    leverage: float
    owner_account: str = Field(alias="ownerAccount")
    platform: str
    position_key: str = Field(alias="positionKey")
    price: float
    side: PositionSide
    size_usd: float = Field(alias="sizeUsd")
    timestamp: int
    transaction_hash: str

    class Settings:
        name: str = "logs"


class MarketStat(Document):
    """Aggregated market statistics per chain per time frame. _id = {chainId}_{timeFrame}_{date}."""

    id: str
    active_traders: int = Field(alias="activeTraders")
    chain_id: str = Field(alias="chainId")
    date: str
    market_pnl: float = Field(alias="marketPnl")
    time_frame: str = Field(alias="timeFrame")
    token_distribution: list[TokenDistribution] = Field(alias="tokenDistribution")
    total_trades: int = Field(alias="totalTrades")
    total_volume: float = Field(alias="totalVolume")
    updated_at: int = Field(alias="updatedAt")
    whale_behavior: WhaleBehavior = Field(alias="whaleBehavior")

    class Settings:
        name: str = "market_stats"


class Market(Document):
    """Perp market contracts. _id = {platform}_{chain}_{contract_address}."""

    id: str
    chain: str
    contract_address: str
    decimals: int
    market: str
    name: str
    swap_only: int
    symbol_a: str
    symbol_b: str
    platform: str
    id_coingecko: str | None = Field(alias="idCoingecko", default=None)

    class Settings:
        name: str = "markets"


class OpeningPosition(Document):
    """Currently open perp positions. _id = {platform}_{chain}_{positionKey}."""

    id: str
    position_key: str = Field(alias="positionKey")
    owner_account: str = Field(alias="ownerAccount")
    asset: str
    side: PositionSide
    size_usd: float = Field(alias="sizeUsd")
    entry_price: float = Field(alias="entryPrice")
    unrealized_pnl: float = Field(alias="unrealizedPnl")
    first_opened_at: int = Field(alias="firstOpenedAt")
    platform: str
    chain: str

    class Settings:
        name: str = "opening_positions"


class Platform(Document):
    """Supported trading platforms. _id = {platform}_{chain}."""

    id: str
    platform: str
    chain: str
    chain_id: str | None = Field(alias="chainId", default=None)
    logo: str
    active: bool
    name: str
    explorer: str

    class Settings:
        name: str = "platforms"


class PotentialToken(Document):
    """Tokens flagged for potential tracking (collection currently empty)."""

    id: str

    class Settings:
        name: str = "potential_tokens"


class Token(Document):
    """Token registry (collection currently empty)."""

    id: str

    class Settings:
        name: str = "tokens"


class TokenPriceBySwapEvent(Document):
    """Per-token hourly prices derived from on-chain swap events (time series)."""

    timestamp: datetime
    metadata: TokenPriceMetadata
    price: float | None = None

    class Settings:
        name: str = "token_prices_by_swap_events"
        timeseries: TimeSeriesConfig = TimeSeriesConfig(
            time_field="timestamp",
            meta_field="metadata",
            granularity=Granularity.hours,
        )


class TradeFeature(Document):
    """Bot/human classification features per trader wallet."""

    id: str
    active_hours: int
    is_human: bool
    median_time_delta: float
    total_trades: int

    class Settings:
        name: str = "trade_features"


class TradeHistory(Document):
    """Backtested trade outcomes per price cluster. _id = {symbol}_{side}_{cluster_id}_{start_ts}_{end_ts}."""

    id: str
    analyze_end_ts: int
    analyze_start_ts: int
    best_price: float
    close_price: float
    cluster_id: int
    entry_price: float
    open_actions: list[TradeOpenAction]
    result: float
    side: TradeHistorySide
    stop_reason: StopReason
    symbol: str
    t_best_price: int
    t_close_price: int
    t_end_cluster: int

    class Settings:
        name: str = "trade_history"


class TraderHistory(Document):
    """Daily PnL/volume history per trader wallet. _id = {chainId}_{address}."""

    id: str
    chain_id: str = Field(alias="chainId")
    history: list[TraderDailyHistory]

    class Settings:
        name: str = "traders_history"

from enum import Enum

from pydantic import BaseModel


class LogAction(str, Enum):
    OPEN = "Open"
    CLOSE = "Close"
    DEPOSIT = "Deposit"
    WITHDRAW = "Withdraw"
    LIQUIDATE = "Liquidate"  # present in raw data; not in original schema enum


class PositionSide(str, Enum):
    LONG = "Long"
    SHORT = "Short"


class Position(BaseModel):
    """One reconstructed position: first Open event paired with last Close/Liquidate."""

    position_key: str
    wallet: str
    asset: str
    platform: str
    chain: str
    side: PositionSide
    entry_price: float
    exit_price: float
    entry_size_usd: float
    entry_collateral_usd: float
    entry_leverage: float
    open_ts: int
    close_ts: int
    close_action: str
    pnl: float
    roi: float
    duration_hours: float
    win: bool
    n_liquidations: int


class WalletFeatures(BaseModel):
    """Per-wallet skill feature vector for ML modeling and backtest evaluation."""

    wallet: str
    platform: str
    chain: str
    # Trade counts
    n_trades: int
    n_long_trades: int
    n_short_trades: int
    n_liquidations: int
    # Long skill — Lim et al. (2022) buy-side dimension
    long_win_rate: float | None
    long_avg_roi: float | None
    long_avg_pnl: float | None
    # Short skill — Lim et al. (2022) sell-side dimension
    short_win_rate: float | None
    short_avg_roi: float | None
    short_avg_pnl: float | None
    # Side asymmetry — RQ1 orthogonality test
    side_asymmetry: float | None  # long_win_rate - short_win_rate
    # Overall
    overall_win_rate: float
    avg_roi: float
    total_pnl: float
    # Leverage-adjusted skill — Idea 2
    mean_leverage: float
    max_leverage: float
    leverage_adj_roi: float  # avg_roi / sqrt(mean_leverage)
    # Sizing skill — Van Loon (2018)
    large_trade_win_rate: float | None
    small_trade_win_rate: float | None
    sizing_skill: float | None  # large_trade_win_rate - small_trade_win_rate
    # Liquidation avoidance — Idea 5
    liquidation_rate: float
    # Temporal features
    n_assets: int
    avg_duration_hours: float
    first_trade_ts: int
    last_trade_ts: int
    active_span_days: float
    trade_frequency_per_day: float

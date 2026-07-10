"""Fetch BTC/ETH daily OHLCV from Binance Futures and derive macro
market-regime labels (volatility / trend buckets).

This is exogenous regime labeling: perp-DEX assets in the panel (Hyperliquid,
Jupiter, GMX-v2, etc.) don't trade on Binance, but crypto alt/perp volatility
is macro-beta-driven, so BTC/ETH realized vol + trend is a standard proxy for
"market condition" (same logic as using VIX to regime-label an unrelated
equity). It labels test folds only -- never a model feature, so there is no
leakage or cross-venue-contamination concern.

For asset-native (idiosyncratic crowding) regime, see the endogenous
market_liq-based bucketing in b06_regime_robustness.py -- BTC/ETH regime
captures macro cycles, not single-token liquidity shocks.
"""

import json
import ssl
import urllib.request
from pathlib import Path

import certifi
import polars as pl
from pydantic import BaseModel, ConfigDict

_BINANCE_KLINES = "https://fapi.binance.com/fapi/v1/klines"
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class MarketRegimeConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    interval: str = "1d"
    vol_window_days: int = 7
    cache_path: Path = Path("data/processed/market_ohlcv.parquet")


class MarketRegimeService:
    """Fetches/caches daily close prices and labels each day's macro regime."""

    def __init__(self, config: MarketRegimeConfig | None = None) -> None:
        self._cfg = config or MarketRegimeConfig()

    def _fetch_symbol(self, symbol: str, start_ms: int, end_ms: int) -> pl.DataFrame:
        rows: list[list[str]] = []
        cursor = start_ms
        while cursor < end_ms:
            url = (
                f"{_BINANCE_KLINES}?symbol={symbol}&interval={self._cfg.interval}"
                f"&startTime={cursor}&endTime={end_ms}&limit=1500"
            )
            with urllib.request.urlopen(url, timeout=15, context=_SSL_CONTEXT) as resp:
                batch = json.loads(resp.read())
            if not batch:
                break
            rows.extend(batch)
            cursor = int(batch[-1][0]) + 1
            if len(batch) < 1500:
                break
        return pl.DataFrame(
            {
                "day_ts": [int(r[0]) // 1000 for r in rows],
                "symbol": [symbol] * len(rows),
                "close": [float(r[4]) for r in rows],
            }
        )

    def load(self, start_ts: int, end_ts: int) -> pl.DataFrame:
        """Cached or freshly fetched daily close prices for configured symbols."""
        cfg = self._cfg
        if cfg.cache_path.exists():
            cached = pl.read_parquet(cfg.cache_path)
            covers = (
                cached.height > 0
                and cached["day_ts"].min() <= start_ts
                and cached["day_ts"].max() >= end_ts
            )
            if covers:
                return cached
        # Pad the fetch window a bit before start_ts so the first rolling
        # window has history to compute over.
        pad_s = self._cfg.vol_window_days * 2 * 86400
        frames = [
            self._fetch_symbol(sym, (start_ts - pad_s) * 1000, end_ts * 1000)
            for sym in cfg.symbols
        ]
        ohlcv = pl.concat(frames, how="vertical")
        cfg.cache_path.parent.mkdir(parents=True, exist_ok=True)
        ohlcv.write_parquet(cfg.cache_path)
        return ohlcv

    def label_regime(self, start_ts: int, end_ts: int) -> pl.DataFrame:
        """Per-day macro regime: vol bucket (low/high) x trend bucket (bull/bear),
        averaged across configured symbols (BTC/ETH beta proxy)."""
        w = self._cfg.vol_window_days
        ohlcv = self.load(start_ts, end_ts).sort(["symbol", "day_ts"])
        ohlcv = ohlcv.with_columns(
            pl.col("close").log().diff().over("symbol").fill_null(0.0).alias("log_ret")
        )
        ohlcv = ohlcv.with_columns(
            pl.col("log_ret")
            .rolling_std(window_size=w, min_samples=1)
            .over("symbol")
            .fill_null(0.0)
            .alias("vol"),
            pl.col("log_ret")
            .rolling_sum(window_size=w, min_samples=1)
            .over("symbol")
            .alias("trend"),
        )
        daily = (
            ohlcv.group_by("day_ts")
            .agg(pl.col("vol").mean().alias("vol"), pl.col("trend").mean().alias("trend"))
            .sort("day_ts")
        )
        vol_med = daily.filter(pl.col("day_ts") >= start_ts)["vol"].median()
        daily = daily.with_columns(
            pl.when(pl.col("vol") >= vol_med)
            .then(pl.lit("high_vol"))
            .otherwise(pl.lit("low_vol"))
            .alias("vol_regime"),
            pl.when(pl.col("trend") >= 0)
            .then(pl.lit("bull"))
            .otherwise(pl.lit("bear"))
            .alias("trend_regime"),
        )
        return daily.select("day_ts", "vol_regime", "trend_regime")

    def label_bins(self, bin_ts: pl.Series) -> pl.DataFrame:
        """Maps each bin_ts (epoch seconds) to its day's macro regime labels."""
        start_ts = int(bin_ts.min())
        end_ts = int(bin_ts.max())
        regime = self.label_regime(start_ts, end_ts)
        return pl.DataFrame({"bin_ts": bin_ts}).with_columns(
            (pl.col("bin_ts") // 86400 * 86400).alias("day_ts")
        ).join(regime, on="day_ts", how="left")


__all__ = ["MarketRegimeConfig", "MarketRegimeService"]

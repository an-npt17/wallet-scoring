"""Build a leakage-safe per-asset, 5-min-binned feature+label panel for
liquidation-burst prediction.

Every feature at bin t is computed from information available at or before t
(open positions as of t, trailing liquidation intensity). The label uses only
the future window (t, t+horizon]. Tier thresholds are size-based (not
label-based) per asset, computed once from the position-size distribution.

Bins are placed on a single global epoch grid (floor(ts / bin_seconds)) so
that per-asset panels share bin boundaries. This lets each asset see
market-wide (cross-asset) liquidation intensity and volume at the same bin,
and the spillover from *other* assets (market minus self) — the multivariate
self-excitation signal. All cross-asset features use the same trailing window
[t-w, t] as the self features, so they stay leakage-safe.

Input : reconstructed positions DataFrame (data/processed/positions.parquet)
Output: one row per (asset, active bin) with baseline + crowding + cross-asset
        features and the binary burst label.
"""

import numpy as np
import polars as pl
from numpy.typing import NDArray

from src.burst.schemas import PanelConfig


class _MarketSeries:
    """Market-wide (all-asset) trailing liquidation series on the global grid.

    Indexed by global bin offset from `gmin`. Slice `[off:off+n]` for an asset
    whose first bin sits at global index `gmin + off`.
    """

    def __init__(
        self,
        gmin: int,
        liq_short: NDArray[np.float64],
        liq_long: NDArray[np.float64],
        notional_short: NDArray[np.float64],
    ) -> None:
        self.gmin = gmin
        self.liq_short = liq_short
        self.liq_long = liq_long
        self.notional_short = notional_short


class BurstPanelBuilderService:
    def __init__(self, config: PanelConfig | None = None) -> None:
        self._cfg = config or PanelConfig()

    def build(self, positions: pl.DataFrame) -> pl.DataFrame:
        cfg = self._cfg
        base = positions.filter(
            (pl.col("close_action").is_not_null())
            & (pl.col("entry_size_usd") > 0)
            & (pl.col("entry_leverage") > 0)
            & (pl.col("open_ts") > 0)
            & (pl.col("close_ts") > pl.col("open_ts"))
        ).select(
            ["asset", "side", "entry_size_usd", "entry_leverage",
             "open_ts", "close_ts", "close_action"]
        )
        liq_per_asset = (
            base.filter(pl.col("close_action") == "Liquidate")
            .group_by("asset")
            .len()
            .filter(pl.col("len") >= cfg.min_asset_liquidations)
        )
        assets: list[str] = liq_per_asset["asset"].to_list()

        market = self._build_market(base)

        frames: list[pl.DataFrame] = []
        for asset in assets:
            frame = self._build_asset(base.filter(pl.col("asset") == asset), asset, market)
            if frame is not None:
                frames.append(frame)
        if not frames:
            return pl.DataFrame()
        return pl.concat(frames, how="vertical")

    def _build_market(self, base: pl.DataFrame) -> _MarketSeries:
        """Precompute market-wide trailing liquidation count and notional on the
        global bin grid spanning every position's open..close range."""
        cfg = self._cfg
        bs = cfg.bin_seconds
        gmin = int(base["open_ts"].min()) // bs
        gmax = int(base["close_ts"].max()) // bs
        n = gmax - gmin + 1

        liq = base.filter(pl.col("close_action") == "Liquidate")
        gb = (liq["close_ts"].to_numpy() // bs - gmin).astype(np.int64)
        size = liq["entry_size_usd"].to_numpy()

        count = np.zeros(n)
        notional = np.zeros(n)
        np.add.at(count, gb, 1.0)
        np.add.at(notional, gb, size)

        cs_c = np.concatenate([[0.0], np.cumsum(count)])
        cs_n = np.concatenate([[0.0], np.cumsum(notional)])

        def gtrailing(cs: NDArray[np.float64], k: int) -> NDArray[np.float64]:
            idx = np.arange(n)
            lo = np.clip(idx - k, 0, None)
            return cs[idx + 1] - cs[lo]

        return _MarketSeries(
            gmin=gmin,
            liq_short=gtrailing(cs_c, cfg.past_short_bins),
            liq_long=gtrailing(cs_c, cfg.past_long_bins),
            notional_short=gtrailing(cs_n, cfg.past_short_bins),
        )

    def _build_asset(
        self, df: pl.DataFrame, asset: str, market: _MarketSeries
    ) -> pl.DataFrame | None:
        cfg = self._cfg
        if df.height < cfg.min_asset_liquidations:
            return None
        bs = cfg.bin_seconds

        size = df["entry_size_usd"].to_numpy()
        lev = df["entry_leverage"].to_numpy()
        is_long = (df["side"] == "Long").to_numpy()
        is_liq = (df["close_action"] == "Liquidate").to_numpy()
        open_ts = df["open_ts"].to_numpy()
        close_ts = df["close_ts"].to_numpy()

        # size-based tiers (terciles); not label-based, so leakage-safe.
        q1, q2 = np.quantile(size, [1 / 3, 2 / 3])
        is_large = size >= q2
        is_small = size < q1

        # Global epoch-aligned grid: first bin = floor(open_min / bs).
        g0 = int(open_ts.min()) // bs
        t0 = g0 * bs
        n_bins = int(close_ts.max()) // bs - g0 + 1
        if n_bins < cfg.horizon_bins + cfg.past_long_bins + 5:
            return None
        ob = (open_ts // bs - g0).astype(np.int64)
        cb = np.clip(close_ts // bs - g0, 0, n_bins - 1).astype(np.int64)

        # Open-interest step series via +size at open bin, -size at close bin.
        def open_series(weight: NDArray[np.float64], mask: NDArray[np.bool_]) -> NDArray[np.float64]:
            delta = np.zeros(n_bins + 1)
            np.add.at(delta, ob[mask], weight[mask])
            np.add.at(delta, cb[mask], -weight[mask])
            return np.cumsum(delta[:n_bins])

        both = np.ones(len(size), dtype=bool)
        oi_total = open_series(size, both)
        oi_long = open_series(size, is_long)
        oi_short = open_series(size, ~is_long)
        oi_large_long = open_series(size, is_large & is_long)
        oi_large_short = open_series(size, is_large & ~is_long)
        oi_small_long = open_series(size, is_small & is_long)
        oi_small_short = open_series(size, is_small & ~is_long)
        oi_large = open_series(size, is_large)
        oi_lev = open_series(lev * size, both)  # leverage*size open => mean leverage

        # Per-bin self liquidation count and notional (USD volume).
        liq = np.zeros(n_bins)
        liq_usd = np.zeros(n_bins)
        np.add.at(liq, cb[is_liq], 1.0)
        np.add.at(liq_usd, cb[is_liq], size[is_liq])

        cs = np.concatenate([[0.0], np.cumsum(liq)])
        cs_usd = np.concatenate([[0.0], np.cumsum(liq_usd)])

        def trailing(cumsum: NDArray[np.float64], k: int) -> NDArray[np.float64]:
            idx = np.arange(n_bins)
            lo = np.clip(idx - k, 0, None)
            return cumsum[idx + 1] - cumsum[lo]

        def forward(k: int) -> NDArray[np.float64]:
            idx = np.arange(n_bins)
            hi = np.clip(idx + 1 + k, 0, n_bins)
            return cs[hi] - cs[idx + 1]

        eps = cfg.eps
        past_short = trailing(cs, cfg.past_short_bins)
        past_long = trailing(cs, cfg.past_long_bins)
        past_notional_short = trailing(cs_usd, cfg.past_short_bins)
        past_notional_long = trailing(cs_usd, cfg.past_long_bins)
        future = forward(cfg.horizon_bins)
        label = (future >= cfg.threshold).astype(np.int8)

        # Cross-asset (market-wide) trailing signal on the same bins.
        off = g0 - market.gmin
        market_short = market.liq_short[off: off + n_bins]
        market_long = market.liq_long[off: off + n_bins]
        market_notional_short = market.notional_short[off: off + n_bins]
        # Spillover = other assets = market minus self (clip float noise).
        other_short = np.maximum(market_short - past_short, 0.0)
        other_notional_short = np.maximum(market_notional_short - past_notional_short, 0.0)

        oi_imbalance = (oi_long - oi_short) / (oi_long + oi_short + eps)
        large_imb = (oi_large_long - oi_large_short) / (oi_large_long + oi_large_short + eps)
        small_imb = (oi_small_long - oi_small_short) / (oi_small_long + oi_small_short + eps)
        oi_prev = np.concatenate([np.zeros(cfg.past_short_bins), oi_total[:-cfg.past_short_bins]])

        panel = pl.DataFrame(
            {
                "asset": [asset] * n_bins,
                "bin_ts": (t0 + np.arange(n_bins) * bs).astype(np.int64),
                "past_liq_short": past_short,
                "past_liq_long": past_long,
                "past_liq_notional_short": past_notional_short,
                "past_liq_notional_long": past_notional_long,
                "oi_imbalance": oi_imbalance,
                "large_tier_imbalance": large_imb,
                "small_tier_imbalance": small_imb,
                "tier_disagreement": large_imb - small_imb,
                "large_share": oi_large / (oi_total + eps),
                "mean_leverage": oi_lev / (oi_total + eps),
                "oi_velocity": oi_total - oi_prev,
                "liq_velocity": past_short - (past_long - past_short) / max(cfg.past_long_bins - cfg.past_short_bins, 1) * cfg.past_short_bins,
                "market_liq_short": market_short,
                "market_liq_long": market_long,
                "market_liq_notional_short": market_notional_short,
                "other_liq_short": other_short,
                "other_liq_notional_short": other_notional_short,
                "label": label,
            }
        )
        # Keep active bins with a valid future window (drop the tail horizon).
        valid = np.zeros(n_bins, dtype=bool)
        valid[: n_bins - cfg.horizon_bins] = True
        panel = panel.filter(pl.Series(valid) & (pl.col("large_share") > 0))
        return panel

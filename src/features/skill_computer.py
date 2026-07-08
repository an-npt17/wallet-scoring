"""
Compute per-wallet skill features from reconstructed positions DataFrame.

Dimensions implemented:
  - Long/Short win rate and ROI (Lim et al. 2022 — buy/sell skill)
  - Side asymmetry: long_win_rate - short_win_rate (RQ1 test)
  - Leverage-adjusted ROI: avg_roi / sqrt(mean_leverage) (Idea 2)
  - Sizing skill: large_trade_win_rate - small_trade_win_rate (Van Loon 2018)
  - Liquidation avoidance rate: n_liquidations / n_trades (Idea 5)
  - Temporal: active span, trade frequency, asset diversification
"""

import polars as pl


class SkillComputerService:
    # ROI winsorization bounds (fraction, not %). Perp ROI is |return| × leverage,
    # so legitimately large; but rows with entry_collateral_usd <= 0 produce
    # |roi| up to 1e14, poisoning every mean-based feature (avg_roi, sizing
    # log(W/L), leverage_adj_roi). We drop those rows and winsorize the residual
    # heavy tail to robust quantiles before any aggregation.
    _ROI_CLIP_LOW_Q: float = 0.001
    _ROI_CLIP_HIGH_Q: float = 0.999

    def compute(self, positions: pl.DataFrame) -> pl.DataFrame:
        positions = self._clean_positions(positions)
        base = self._base_aggregation(positions)
        sizing = self._sizing_skill(positions)
        wl = self._van_loon_wl_ratio(positions)
        return (
            base.join(sizing, on="wallet", how="left")
            .join(wl, on="wallet", how="left")
            .with_columns(
                [
                    (pl.col("long_win_rate") - pl.col("short_win_rate")).alias(
                        "side_asymmetry"
                    ),
                    (
                        pl.col("avg_roi")
                        / pl.col("mean_leverage").clip(lower_bound=0.1).sqrt()
                    ).alias("leverage_adj_roi"),
                    (
                        (pl.col("last_trade_ts") - pl.col("first_trade_ts")).cast(
                            pl.Float64
                        )
                        / 86400.0
                    ).alias("active_span_days"),
                ]
            )
            .with_columns(
                [
                    pl.when(pl.col("active_span_days") > 0)
                    .then(
                        pl.col("n_trades").cast(pl.Float64) / pl.col("active_span_days")
                    )
                    .otherwise(0.0)
                    .alias("trade_frequency_per_day"),
                    (
                        pl.col("n_liquidations").cast(pl.Float64)
                        / pl.col("n_trades").clip(lower_bound=1).cast(pl.Float64)
                    ).alias("liquidation_rate"),
                ]
            )
        )

    def _clean_positions(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop degenerate-collateral rows and winsorize the ROI heavy tail.

        Rows with entry_collateral_usd <= 0 yield |roi| up to ~1e14 and must be
        removed before any mean-based aggregation. The remaining ROI tail is
        winsorized to robust quantiles so that a single fat-tailed trade cannot
        dominate a wallet's mean win/loss ROI (Van Loon sizing ratio).
        """
        cleaned = df.filter(pl.col("entry_collateral_usd") > 0)
        low = cleaned["roi"].quantile(self._ROI_CLIP_LOW_Q)
        high = cleaned["roi"].quantile(self._ROI_CLIP_HIGH_Q)
        if low is None or high is None:
            return cleaned
        return cleaned.with_columns(
            pl.col("roi").clip(lower_bound=low, upper_bound=high).alias("roi")
        )

    def _base_aggregation(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.group_by("wallet").agg(
            [
                pl.len().alias("n_trades"),
                pl.col("win")
                .filter(pl.col("side") == "Long")
                .len()
                .alias("n_long_trades"),
                pl.col("win")
                .filter(pl.col("side") == "Short")
                .len()
                .alias("n_short_trades"),
                pl.col("n_liquidations").max().fill_null(0).alias("n_liquidations"),
                # Long skill
                pl.col("win")
                .filter(pl.col("side") == "Long")
                .mean()
                .alias("long_win_rate"),
                pl.col("roi")
                .filter(pl.col("side") == "Long")
                .mean()
                .alias("long_avg_roi"),
                pl.col("pnl")
                .filter(pl.col("side") == "Long")
                .mean()
                .alias("long_avg_pnl"),
                # Short skill
                pl.col("win")
                .filter(pl.col("side") == "Short")
                .mean()
                .alias("short_win_rate"),
                pl.col("roi")
                .filter(pl.col("side") == "Short")
                .mean()
                .alias("short_avg_roi"),
                pl.col("pnl")
                .filter(pl.col("side") == "Short")
                .mean()
                .alias("short_avg_pnl"),
                # Overall
                pl.col("win").mean().alias("overall_win_rate"),
                pl.col("roi").mean().alias("avg_roi"),
                pl.col("pnl").sum().alias("total_pnl"),
                # Leverage
                pl.col("entry_leverage")
                .filter(pl.col("entry_leverage") > 0)
                .mean()
                .alias("mean_leverage"),
                pl.col("entry_leverage").max().alias("max_leverage"),
                # Temporal
                pl.col("asset").n_unique().alias("n_assets"),
                pl.col("duration_hours").mean().alias("avg_duration_hours"),
                pl.col("open_ts").min().alias("first_trade_ts"),
                pl.col("open_ts").max().alias("last_trade_ts"),
                # Metadata
                pl.col("platform").first().alias("platform"),
                pl.col("chain").first().alias("chain"),
            ]
        )

    def _van_loon_wl_ratio(self, df: pl.DataFrame) -> pl.DataFrame:
        """Van Loon (2018) win/loss ratio with delta-method sampling variance.

        Returns wallet-level log(W/L) estimate and sigma2 for the
        Normal-Normal shrinkage model.
        """
        _EPS = 1e-8
        grouped = df.group_by("wallet").agg(
            [
                pl.col("roi").filter(pl.col("win")).mean().alias("mean_win_roi"),
                pl.col("roi").filter(pl.col("win")).count().alias("n_win"),
                pl.col("roi")
                .filter(pl.col("win"))
                .var(ddof=1)
                .fill_null(0.0)
                .alias("var_win_roi"),
                pl.col("roi")
                .filter(~pl.col("win"))
                .abs()
                .mean()
                .alias("mean_loss_roi"),
                pl.col("roi").filter(~pl.col("win")).count().alias("n_loss"),
                pl.col("roi")
                .filter(~pl.col("win"))
                .abs()
                .var(ddof=1)
                .fill_null(0.0)
                .alias("var_loss_roi"),
            ]
        )
        return grouped.with_columns(
            [
                pl.when(
                    (pl.col("mean_loss_roi") > _EPS)
                    & (pl.col("mean_win_roi") > 0)
                )
                .then((pl.col("mean_win_roi") / pl.col("mean_loss_roi")).log())
                .otherwise(None)
                .alias("log_wl_ratio"),
                # delta-method sampling variance of log(W/L):
                # var(log(WL)) ≈ var_win / (n_win * μ_win²) + var_loss / (n_loss * μ_loss²)
                pl.when(
                    (pl.col("mean_loss_roi") > _EPS)
                    & (pl.col("mean_win_roi") > 0)
                    & (pl.col("n_win") > 1)
                    & (pl.col("n_loss") > 1)
                )
                .then(
                    pl.col("var_win_roi")
                    / (pl.col("n_win") * pl.col("mean_win_roi").pow(2) + _EPS)
                    + pl.col("var_loss_roi")
                    / (pl.col("n_loss") * pl.col("mean_loss_roi").pow(2) + _EPS)
                )
                .otherwise(None)
                .alias("sigma2_log_wl"),
            ]
        )

    def _sizing_skill(self, df: pl.DataFrame) -> pl.DataFrame:
        """Van Loon (2018): win_rate(large_trades) - win_rate(small_trades)."""
        median_size = df.group_by("wallet").agg(
            pl.col("entry_size_usd").median().alias("median_size")
        )
        labeled = df.join(median_size, on="wallet").with_columns(
            (pl.col("entry_size_usd") >= pl.col("median_size")).alias("is_large")
        )
        return (
            labeled.group_by("wallet")
            .agg(
                [
                    pl.col("win")
                    .filter(pl.col("is_large"))
                    .mean()
                    .alias("large_trade_win_rate"),
                    pl.col("win")
                    .filter(~pl.col("is_large"))
                    .mean()
                    .alias("small_trade_win_rate"),
                ]
            )
            .with_columns(
                (pl.col("large_trade_win_rate") - pl.col("small_trade_win_rate")).alias(
                    "sizing_skill"
                )
            )
        )

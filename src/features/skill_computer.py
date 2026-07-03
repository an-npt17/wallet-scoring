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
    def compute(self, positions: pl.DataFrame) -> pl.DataFrame:
        base = self._base_aggregation(positions)
        sizing = self._sizing_skill(positions)
        return (
            base.join(sizing, on="wallet", how="left")
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

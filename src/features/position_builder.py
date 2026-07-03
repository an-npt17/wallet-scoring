"""
Reconstruct completed position lifecycle from raw log events (logs.json).

Strategy:
  - First Open event per positionKey → entry fields
  - Last Close/Liquidate event per positionKey → exit fields
  - Liquidate events counted per wallet; excluded from PnL reconstruction
  - Positions without a matching Close/Liquidate are dropped (still open)

PnL approximation (entry-only):
  Long:  pnl = (exit_price - entry_price) / entry_price * entry_size_usd
  Short: pnl = (entry_price - exit_price) / entry_price * entry_size_usd

Use closed_positions.realizedPnl for authoritative values (Stage 3).
"""

from pathlib import Path

import polars as pl

from src.features.schemas import LogAction

_CLOSE_ACTIONS = [LogAction.CLOSE.value, LogAction.LIQUIDATE.value]


class PositionBuilderService:
    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path

    def build(self) -> pl.DataFrame:
        """Return DataFrame with one row per matched Open→Close position."""
        scan = pl.scan_ndjson(str(self._data_path))
        opens = self._first_opens(scan)
        closes = self._last_closes(scan)
        liq_counts = self._liquidation_counts(scan)

        return (
            opens.join(closes, on="positionKey", how="inner")
            .join(liq_counts, on="wallet", how="left")
            .with_columns(pl.col("n_liquidations").fill_null(0))
            .pipe(self._compute_derived)
            .collect()
        )

    def _first_opens(self, scan: pl.LazyFrame) -> pl.LazyFrame:
        return (
            scan.filter(pl.col("action") == LogAction.OPEN.value)
            .sort("timestamp")
            .group_by("positionKey")
            .agg(
                [
                    pl.first("ownerAccount").alias("wallet"),
                    pl.first("side"),
                    pl.first("asset"),
                    pl.first("platform"),
                    pl.first("chain"),
                    pl.first("price").alias("entry_price"),
                    pl.first("sizeUsd").alias("entry_size_usd"),
                    pl.first("collateralUsd").alias("entry_collateral_usd"),
                    pl.first("leverage").alias("entry_leverage"),
                    pl.first("timestamp").alias("open_ts"),
                ]
            )
        )

    def _last_closes(self, scan: pl.LazyFrame) -> pl.LazyFrame:
        return (
            scan.filter(pl.col("action").is_in(_CLOSE_ACTIONS))
            .sort("timestamp")
            .group_by("positionKey")
            .agg(
                [
                    pl.last("price").alias("exit_price"),
                    pl.last("timestamp").alias("close_ts"),
                    pl.last("action").alias("close_action"),
                ]
            )
        )

    def _liquidation_counts(self, scan: pl.LazyFrame) -> pl.LazyFrame:
        return (
            scan.filter(pl.col("action") == LogAction.LIQUIDATE.value)
            .group_by("ownerAccount")
            .agg(pl.len().alias("n_liquidations"))
            .rename({"ownerAccount": "wallet"})
        )

    def _compute_derived(self, df: pl.LazyFrame) -> pl.LazyFrame:
        return df.with_columns(
            [
                pl.when(pl.col("side") == "Long")
                .then(
                    (pl.col("exit_price") - pl.col("entry_price"))
                    / pl.col("entry_price")
                    * pl.col("entry_size_usd")
                )
                .otherwise(
                    (pl.col("entry_price") - pl.col("exit_price"))
                    / pl.col("entry_price")
                    * pl.col("entry_size_usd")
                )
                .alias("pnl"),
                (
                    (pl.col("close_ts") - pl.col("open_ts")).cast(pl.Float64) / 3600.0
                ).alias("duration_hours"),
            ]
        ).with_columns(
            [
                (
                    pl.col("pnl")
                    / pl.col("entry_collateral_usd").clip(lower_bound=1e-9)
                ).alias("roi"),
                (pl.col("pnl") > 0).alias("win"),
            ]
        )

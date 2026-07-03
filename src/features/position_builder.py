"""
Reconstruct completed position lifecycle via beanie/MongoDB server-side aggregation.

Three parallel $group pipelines on the logs collection:
  1. First Open event per positionKey → entry fields
  2. Last Close/Liquidate event per positionKey → exit fields
  3. Liquidate count per ownerAccount → liquidation_rate denominator

All heavy sorting/grouping runs on MongoDB; only aggregated rows transferred.
PnL derived locally in polars after join.

Requires beanie initialized before use (call src.db.init_db() first).

PnL approximation (entry-only):
  Long:  pnl = (exit_price - entry_price) / entry_price * entry_size_usd
  Short: pnl = (entry_price - exit_price) / entry_price * entry_size_usd

Use closed_positions.realizedPnl for authoritative values (Stage 3).
"""
import asyncio

import polars as pl

from database.mongo.schema import Log
from src.features.schemas import LogAction

_CLOSE_ACTIONS = [LogAction.CLOSE.value, LogAction.LIQUIDATE.value]


class PositionBuilderService:
    async def build(self) -> pl.DataFrame:
        """Return DataFrame with one row per matched Open→Close position."""
        opens_docs, closes_docs, liq_docs = await asyncio.gather(
            self._fetch_first_opens(),
            self._fetch_last_closes(),
            self._fetch_liquidation_counts(),
        )

        opens = pl.from_dicts(opens_docs, infer_schema_length=500).rename({"_id": "positionKey"})
        closes = pl.from_dicts(closes_docs, infer_schema_length=500).rename({"_id": "positionKey"})
        liqs = pl.from_dicts(liq_docs, infer_schema_length=500).rename({"_id": "wallet"})

        return (
            opens
            .join(closes, on="positionKey", how="inner")
            .join(liqs, on="wallet", how="left")
            .with_columns(pl.col("n_liquidations").fill_null(0))
            .pipe(self._compute_derived)
        )

    async def _fetch_first_opens(self) -> list[dict]:
        return await Log.aggregate([
            {"$match": {"action": LogAction.OPEN.value}},
            {"$sort": {"timestamp": 1}},
            {
                "$group": {
                    "_id": "$positionKey",
                    "wallet": {"$first": "$ownerAccount"},
                    "side": {"$first": "$side"},
                    "asset": {"$first": "$asset"},
                    "platform": {"$first": "$platform"},
                    "chain": {"$first": "$chain"},
                    "entry_price": {"$first": "$price"},
                    "entry_size_usd": {"$first": "$sizeUsd"},
                    "entry_collateral_usd": {"$first": "$collateralUsd"},
                    "entry_leverage": {"$first": "$leverage"},
                    "open_ts": {"$first": "$timestamp"},
                }
            },
        ]).to_list()

    async def _fetch_last_closes(self) -> list[dict]:
        return await Log.aggregate([
            {"$match": {"action": {"$in": _CLOSE_ACTIONS}}},
            {"$sort": {"timestamp": 1}},
            {
                "$group": {
                    "_id": "$positionKey",
                    "exit_price": {"$last": "$price"},
                    "close_ts": {"$last": "$timestamp"},
                    "close_action": {"$last": "$action"},
                }
            },
        ]).to_list()

    async def _fetch_liquidation_counts(self) -> list[dict]:
        return await Log.aggregate([
            {"$match": {"action": LogAction.LIQUIDATE.value}},
            {
                "$group": {
                    "_id": "$ownerAccount",
                    "n_liquidations": {"$sum": 1},
                }
            },
        ]).to_list()

    def _compute_derived(self, df: pl.DataFrame) -> pl.DataFrame:
        return (
            df
            .with_columns([
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
                ((pl.col("close_ts") - pl.col("open_ts")).cast(pl.Float64) / 3600.0)
                .alias("duration_hours"),
            ])
            .with_columns([
                (pl.col("pnl") / pl.col("entry_collateral_usd").clip(lower_bound=1e-9))
                .alias("roi"),
                (pl.col("pnl") > 0).alias("win"),
            ])
        )

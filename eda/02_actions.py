"""
Deep dive into action types and their semantics.
Understands what each action means in a position lifecycle.
"""

import polars as pl
from config import DATA_PATH, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)

    # ── Action sequences per position ──────────────────────────────
    print("╔══════════════════════════════════════════════╗")
    print("║         ACTION LIFECYCLE ANALYSIS           ║")
    print("╚══════════════════════════════════════════════╝")

    # For each position: what actions happen, in what order?
    # Sample 2M entries to keep this tractable
    sample = (
        scan.with_columns(pl.col("timestamp").cast(pl.Datetime).alias("ts"))
        .head(2_000_000)
        .collect()
    )

    # Action sequences per position
    sequences = (
        sample.sort("timestamp")
        .group_by("positionKey", maintain_order=True)
        .agg(
            [
                pl.col("action").alias("action_seq"),
                pl.col("asset").first().alias("asset"),
                pl.col("ownerAccount").first().alias("wallet"),
                pl.col("platform").first().alias("platform"),
                (pl.col("timestamp").last() - pl.col("timestamp").first()).alias(
                    "duration_s"
                ),
            ]
        )
        .with_columns(
            [
                pl.col("action_seq").list.join(" → ").alias("sequence_str"),
                pl.col("action_seq").list.len().alias("n_actions"),
                (pl.col("action_seq").list.first() == "Open").alias("starts_with_open"),
                (pl.col("action_seq").list.last().is_in(["Close", "Liquidate"])).alias(
                    "ends_with_close_or_liq"
                ),
                pl.col("action_seq")
                .list.eval(pl.element().is_in(["Close", "Liquidate"]).any())
                .alias("has_close_or_liq"),
            ]
        )
    )

    total_positions = len(sequences)
    starts_open = sequences["starts_with_open"].sum()
    ends_closed = sequences["ends_with_close_or_liq"].sum()
    has_close = sequences["has_close_or_liq"].sum()

    print(f"  Total positions sampled:           {total_positions:>8,}")
    print(
        f"  Start with Open:                   {starts_open:>8,}  ({starts_open / total_positions * 100:5.1f}%)"
    )
    print(
        f"  End with Close/Liquidate:          {ends_closed:>8,}  ({ends_closed / total_positions * 100:5.1f}%)"
    )
    print(
        f"  Have Close or Liquidate anywhere:  {has_close:>8,}  ({has_close / total_positions * 100:5.1f}%)"
    )
    print()

    # Most common action sequences
    top_seqs = (
        sequences.group_by("sequence_str")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
        .head(15)
    )
    print("╔══════════════════════════════════════════════╗")
    print("║         TOP 15 ACTION SEQUENCES             ║")
    print("╚══════════════════════════════════════════════╝")
    for row in top_seqs.iter_rows():
        print(f"  [{row[1]:>6,}]  {row[0]}")

    # ── Action context: what happens around each action ────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         ACTIONS BY PLATFORM                 ║")
    print("╚══════════════════════════════════════════════╝")
    cross = (
        sample.group_by(["platform", "action"])
        .agg(pl.len().alias("count"))
        .sort(["platform", "count"])
    )
    for row in cross.iter_rows():
        print(f"  {row[0]:<15s}  {row[1]:<12s}  {row[2]:>10,}")

    # ── Liquidations ───────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         LIQUIDATION ANALYSIS                ║")
    print("╚══════════════════════════════════════════════╝")
    liq = sample.filter(pl.col("action") == "Liquidate")
    print(f"  Total liquidations in sample:  {len(liq):>8,}")
    if len(liq) > 0:
        print(f"  Unique wallets liquidated:      {liq['ownerAccount'].n_unique():>8,}")
        print(f"  Unique positions liquidated:    {liq['positionKey'].n_unique():>8,}")
        print(
            f"  Avg collateral at liquidation:  ${liq['collateralUsd'].mean():>10,.2f}"
        )
        print(f"  Avg leverage at liquidation:    {liq['leverage'].mean():>8.1f}x")
        print(f"  Top assets liquidated:")
        for row in (
            liq.group_by("asset")
            .agg(pl.len().alias("count"))
            .sort("count", descending=True)
            .head(10)
            .iter_rows()
        ):
            print(f"    {row[0]:<12s}  {row[1]:>8,}")

    # ── Withdrawals ────────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         WITHDRAWAL ANALYSIS                  ║")
    print("╚══════════════════════════════════════════════╝")
    wd = sample.filter(pl.col("action") == "Withdraw")
    print(f"  Total withdrawals in sample:  {len(wd):>8,}")
    if len(wd) > 0:
        print(f"  Avg withdrawal amount:         ${wd['collateralUsd'].mean():>10,.2f}")
        print(
            f"  Median withdrawal amount:      ${wd['collateralUsd'].median():>10,.2f}"
        )


if __name__ == "__main__":
    main()

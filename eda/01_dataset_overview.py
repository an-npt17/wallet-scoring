"""
Dataset overview: size, schema, time range, unique entities.
Answers: What is this dataset? How big is it? What's the scope?
"""

import polars as pl


def main():
    DATA_PATH = "logs.json"
    scan = pl.scan_ndjson(DATA_PATH)

    # ── Full-dataset aggregations ──────────────────────────────────
    # These run on the full 20GB via streaming
    full_stats = scan.select(
        [
            pl.len().alias("total_entries"),
            pl.col("ownerAccount").n_unique().alias("unique_wallets"),
            pl.col("positionKey").n_unique().alias("unique_positions"),
            pl.col("asset").n_unique().alias("unique_assets"),
            pl.col("platform").n_unique().alias("unique_platforms"),
            pl.col("chain").n_unique().alias("unique_chains"),
            pl.col("action").n_unique().alias("unique_actions"),
            pl.col("timestamp").min().alias("ts_min"),
            pl.col("timestamp").max().alias("ts_max"),
            pl.col("transaction_hash").n_unique().alias("unique_tx_hashes"),
        ]
    ).collect()

    ts_min = full_stats["ts_min"][0]
    ts_max = full_stats["ts_max"][0]
    date_min = pl.from_epoch(ts_min, time_unit="s").dt.date().item()
    date_max = pl.from_epoch(ts_max, time_unit="s").dt.date().item()
    span_days = (ts_max - ts_min) / 86400

    print("╔══════════════════════════════════════════════╗")
    print("║         DATASET OVERVIEW (FULL)              ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"  Total entries:       {full_stats['total_entries'][0]:>14,}")
    print(f"  Unique wallets:      {full_stats['unique_wallets'][0]:>14,}")
    print(f"  Unique positions:    {full_stats['unique_positions'][0]:>14,}")
    print(f"  Unique tx hashes:    {full_stats['unique_tx_hashes'][0]:>14,}")
    print(f"  Unique assets:       {full_stats['unique_assets'][0]:>14,}")
    print(f"  Unique platforms:    {full_stats['unique_platforms'][0]:>14,}")
    print(f"  Unique chains:       {full_stats['unique_chains'][0]:>14,}")
    print(f"  Unique actions:      {full_stats['unique_actions'][0]:>14,}")
    print(f"  Time range:          {date_min}  →  {date_max}")
    print(f"  Timespan:            {span_days:.1f} days")
    print()

    # ── Detailed schema ────────────────────────────────────────────
    SMALL_SAMPLE_ROWS = 1000
    sample = scan.head(SMALL_SAMPLE_ROWS).collect()
    print("╔══════════════════════════════════════════════╗")
    print("║         SCHEMA                              ║")
    print("╚══════════════════════════════════════════════╝")
    for col_name, dtype in zip(sample.columns, sample.dtypes):
        print(f"  {col_name:<20s}  {dtype}")

    # ── Action types (full) ────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         ACTION DISTRIBUTION (FULL)          ║")
    print("╚══════════════════════════════════════════════╝")
    actions = scan.group_by("action").agg(pl.len().alias("count")).collect()
    total = actions["count"].sum()
    for row in actions.sort("count", descending=True).iter_rows():
        pct = row[1] / total * 100
        print(f"  {row[0]:<12s}  {row[1]:>12,}  ({pct:5.2f}%)")

    # ── Missing values ─────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         MISSING VALUES (sample)             ║")
    print("╚══════════════════════════════════════════════╝")
    nulls = sample.select([pl.all().name.suffix("_null")]).null_count()
    for col in sample.columns:
        n = nulls[f"{col}_null"][0]
        if n > 0:
            print(
                f"  {col:<20s}  {n:>8,} missing  ({n / SMALL_SAMPLE_ROWS * 100:.2f}%)"
            )
    if nulls.select(pl.all().sum()).item() == 0:
        print("  (no missing values in sample)")

    # ── Chains (full) ──────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         CHAIN DISTRIBUTION (FULL)           ║")
    print("╚══════════════════════════════════════════════╝")
    chains = scan.group_by("chain").agg(pl.len().alias("count")).collect()
    total = chains["count"].sum()
    for row in chains.sort("count", descending=True).iter_rows():
        pct = row[1] / total * 100
        print(f"  {row[0]:<15s}  {row[1]:>12,}  ({pct:5.2f}%)")


if __name__ == "__main__":
    main()

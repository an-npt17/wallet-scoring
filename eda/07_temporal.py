"""
Temporal patterns: when does trading happen?
"""

import polars as pl
from config import DATA_PATH, LARGE_SAMPLE_ROWS, OUTPUT_DIR


def main():
    scan = pl.scan_ndjson(DATA_PATH)
    sample = (
        scan.with_columns(pl.col("timestamp").cast(pl.Datetime).alias("ts"))
        .head(LARGE_SAMPLE_ROWS)
        .collect()
    )

    print("╔══════════════════════════════════════════════╗")
    print("║         TEMPORAL PATTERNS                    ║")
    print("╚══════════════════════════════════════════════╝")

    # ── Daily activity ─────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         DAILY TRADING VOLUME                 ║")
    print("╚══════════════════════════════════════════════╝")
    daily = (
        sample.filter(pl.col("action") == "Open")
        .with_columns(pl.col("ts").dt.date().alias("date"))
        .group_by("date")
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("sizeUsd").sum().alias("volume"),
                pl.col("ownerAccount").n_unique().alias("active_wallets"),
            ]
        )
        .sort("date")
    )
    print(f"  Date range: {daily['date'].min()}  →  {daily['date'].max()}")
    print(f"  Avg daily trades:   {daily['n_trades'].mean():>10,.0f}")
    print(f"  Max daily trades:   {daily['n_trades'].max():>10,}")
    print(f"  Avg daily volume:   ${daily['volume'].mean():>12,.0f}")
    print(f"  Max daily volume:   ${daily['volume'].max():>12,.0f}")
    print(f"  Avg daily wallets:  {daily['active_wallets'].mean():>10,.0f}")

    # ── Hourly activity ────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         HOURLY TRADING PATTERN               ║")
    print("╚══════════════════════════════════════════════╝")
    hourly = (
        sample.filter(pl.col("action") == "Open")
        .with_columns(pl.col("ts").dt.hour().alias("hour"))
        .group_by("hour")
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("sizeUsd").sum().alias("volume"),
            ]
        )
        .sort("hour")
    )
    max_hour = hourly.filter(pl.col("n_trades") == hourly["n_trades"].max())["hour"][0]
    min_hour = hourly.filter(pl.col("n_trades") == hourly["n_trades"].min())["hour"][0]
    print(
        f"  Peak hour:          {max_hour}:00 UTC  ({hourly.filter(pl.col('hour') == max_hour)['n_trades'].item():,} trades)"
    )
    print(
        f"  Slowest hour:       {min_hour}:00 UTC  ({hourly.filter(pl.col('hour') == min_hour)['n_trades'].item():,} trades)"
    )
    print()
    for row in hourly.iter_rows():
        bar = "█" * int(row[1] / hourly["n_trades"].max() * 40)
        print(f"  {row[0]:>2}h  {bar}  {row[1]:>8,} trades")

    # ── Day of week ────────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         DAY-OF-WEEK PATTERN                  ║")
    print("╚══════════════════════════════════════════════╝")
    dow = (
        sample.filter(pl.col("action") == "Open")
        .with_columns(pl.col("ts").dt.weekday().alias("dow"))
        .group_by("dow")
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("sizeUsd").sum().alias("volume"),
            ]
        )
        .sort("dow")
    )
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for row in dow.iter_rows():
        bar = "█" * int(row[1] / dow["n_trades"].max() * 40)
        print(f"  {days[row[0] - 1]:<4s}  {bar}  {row[1]:>8,} trades")

    # ── Weekly trend ───────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         WEEKLY VOLUME TREND                  ║")
    print("╚══════════════════════════════════════════════╝")
    weekly = (
        sample.filter(pl.col("action") == "Open")
        .with_columns(
            pl.col("ts").dt.week().alias("week"), pl.col("ts").dt.year().alias("year")
        )
        .group_by(["year", "week"])
        .agg(
            [
                pl.len().alias("n_trades"),
                pl.col("sizeUsd").sum().alias("volume"),
            ]
        )
        .sort(["year", "week"])
    )
    for row in weekly.iter_rows():
        label = f"{row[0]}-W{row[1]:02d}"
        print(f"  {label:<10s}  {row[2]:>8,} trades  ${row[3]:>12,.0f} vol")

    # ── Liquidation timing ─────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║         LIQUIDATION TIMING                    ║")
    print("╚══════════════════════════════════════════════╝")
    liq = sample.filter(pl.col("action") == "Liquidate")
    if len(liq) > 0:
        liq_hourly = (
            liq.with_columns(pl.col("ts").dt.hour().alias("hour"))
            .group_by("hour")
            .agg(pl.len().alias("n_liq"))
            .sort("hour")
        )
        for row in liq_hourly.iter_rows():
            bar = "█" * int(row[1] / liq_hourly["n_liq"].max() * 40)
            print(f"  {row[0]:>2}h  {bar}  {row[1]:>6,} liquidations")


if __name__ == "__main__":
    main()

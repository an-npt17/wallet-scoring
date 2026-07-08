# M0 Feasibility Probe: Liquidation-Wall "Magnet" Effect — NEGATIVE

**Branch:** `liquidation-burst` · **Date:** July 2026 · Status: **magnet effect not supported → drop as standalone claim**

## Question
Is perp price *attracted* toward dense liquidation-price clusters ("walls" / stop-hunt / liquidity magnet)?

## Method
- Walls reconstructed from `positions.parquet`: per open position, liquidation price ≈ `entry × (1 ∓ 1/leverage)` (Long −, Short +); active interval `[open_ts, close_ts)`; weight = `entry_size_usd`.
- Price path from `hyperliquid_prices` (minute-level; BTC 529,741 rows / 368 days).
- Two tests, ~2.5–4k sampled timestamps each:
  1. **Directional:** Spearman/Pearson of size-weighted wall imbalance `w=(size_above−size_below)/total` (within ±15% of price) vs forward return over H∈{60,240,360} min.
  2. **Attraction (touch-rate):** does price *reach* the nearest dominant wall within H more than an **equidistant mirror level** (same distance, opposite side)? Isolates attraction from trend.

## Results (all null)

| Asset | n positions | Directional Spearman(w, ret) | p |
|-------|------------:|------------------------------:|---|
| BTC | 399,044 | +0.017 (60m) / +0.029 (240m) | 0.58 / 0.99 |
| SOL | 297,685 | +0.021 (240m) | 0.97 |
| ETH | 201,350 | −0.001 (240m) | 0.32 |

- BTC touch-rate: wall touched 2.4%/6.0% vs mirror 2.7%/6.1% (H=120/360m), z≈−0.66/−0.22 — **walls if anything touched slightly *less* than mirror**.
- Toward-wall directional hit rate 0.496 / 0.509 (chance 0.5). Bootstrap 95% CI on Pearson straddles 0.

## Verdict
Across the three most-liquid assets (~900k positions) and two independent test forms, **no liquidation-magnet signal**. The "price is drawn to liquidation walls" mechanism is **not demonstrable** on this data → **do not build a thesis headline on it.**

## Caveats (honest)
- Approximate liq-price (ignores maintenance margin, cross-margin, add/reduce). A *strong* magnet would still leave a directional trace, so this is unlikely to fully mask a real effect, but it blurs walls.
- Reconstructed (not exchange-native) open interest.
- Horizons 1–6h; sub-minute stop-hunts not testable at minute resolution (and not the claimed mechanism).
- Thinnest alts (where the effect is theorized strongest) lack the price/position density to test rigorously — so the precise claim is "**no magnet on liquid majors**," not "impossible on every token."

## Implication for the research direction
- **Drop the magnet as a standalone / headline claim.** Fusing it into the burst paper (as originally proposed) is not justified by the data.
- The liquidation-**wall map remains useful as a covariate/feature for burst prediction** — walls mark where cascades can *ignite* (a statement about liquidation-event clustering, not price attraction), which the burst label tests directly.
- **Robust fallbacks unaffected by this null:** (C) liquidation-burst early warning [[project-liquidation-burst-research]] and (B) competing-risks position survival — both use dense, self-supervised event labels and do not depend on any magnet effect.

# M0 Feasibility Probe: Liquidation-Burst Label — PASS (green light)

**Branch:** `liquidation-burst` · **Date:** July 2026 · Status: **label is dense, balanced, and strongly learnable → proceed.**

## Question
Is a synchronized-liquidation-burst label (a) balanced enough to train and (b) actually predictable?

## Method
- Source: `positions.parquet`, `close_action == "Liquidate"` → **190,573 liquidation events**, 249 assets (BTC 78k, SOL 67k, ETH 28k dominate; then XRP/BNB/DOGE tails).
- 5-min bins per asset (top-12 by liquidation volume, pooled).
- Label: burst at horizon `h` if liquidation count in `(t, t+h]` ≥ `thr`.
- Learnability proxy: AUC of a **single trivial feature** — past-15-min liquidation count — predicting the future burst (self-excitation / Hawkes premise test).

## Results

| h (min) | thr | pooled base rate | n positives | AUC(past-15m → burst) |
|--------:|----:|-----------------:|------------:|----------------------:|
| 5  | ≥3 | 1.23% | 17,029 | 0.873 |
| 5  | ≥5 | 0.54% | 7,522 | 0.893 |
| 15 | ≥3 | **3.77%** | **52,182** | 0.831 |
| 15 | ≥5 | 2.02% | 27,994 | 0.862 |
| 60 | ≥3 | 11.9% | 164,938 | 0.755 |
| 60 | ≥5 | **7.85%** | **108,807** | 0.788 |

## Verdict — PASS
1. **Balanced + huge positive class.** Sweet-spot operating points: **h=15, thr≥3** (3.8% base, 52k positives) or **h=60, thr≥5** (7.9% base, 109k positives). No small-sample / imbalance blocker.
2. **Strongly learnable.** A single trivial feature (recent liquidation intensity) gives **AUC 0.75–0.91**. Self-excitation is real and strong — the Hawkes premise is confirmed empirically.
3. This is the **inverse of the wallet-scoring failure**: there the label was ~99% noise (ρ=0.013); here the label is dense and predictable.

## Honest framing for the paper (important)
Because trivial self-history already yields **AUC ≈ 0.87**, the research contribution is **not** "can bursts be predicted" (yes, almost trivially, from autocorrelation). The bar is the **self-exciting baseline**. The thesis must show that **tier-crowding + cross-venue + graph features and calibrated conformal warning beat a plain Hawkes / past-intensity baseline out-of-sample, and by how much.** That is a well-posed, defensible contribution — and, unlike the wallet work, the reliable label makes the lift measurable.

## Recommended lock
- Primary label: **h = 15 min, thr ≥ 3** (balanced, 52k positives). Secondary: h = 60 min, thr ≥ 5.
- Strongest baseline to beat: **past-intensity / univariate Hawkes (AUC ≈ 0.83–0.87)**.
- Next step: leakage-safe feature pipeline on the Stage-15 rolling walk-forward; measure lift over the self-exciting baseline. See [[project-liquidation-burst-research]].

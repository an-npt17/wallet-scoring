"""Config for the liquidation-burst feature panel (M0-locked defaults)."""

from pydantic import BaseModel


class PanelConfig(BaseModel):
    """Panel construction parameters. Defaults are the M0-locked operating point.

    m0-burst-findings.md: primary label h=15min (horizon_bins=3 at 5-min bins),
    threshold=3 liquidations; past-intensity baseline reaches AUC ~0.83-0.87.
    """

    bin_seconds: int = 300  # 5-min bins
    horizon_bins: int = 3  # 15-min future window for the label
    threshold: int = 3  # >=3 liquidations in the future window => burst
    past_short_bins: int = 3  # 15-min trailing intensity feature
    past_long_bins: int = 12  # 60-min trailing intensity feature
    min_asset_liquidations: int = 100  # skip assets with too few liquidations
    eps: float = 1e-9

    # Feature column groups (used by the pipeline to split baseline vs full,
    # and for ablation over each incremental signal source).
    baseline_features: list[str] = ["past_liq_short", "past_liq_long"]
    crowding_features: list[str] = [
        "oi_imbalance",
        "large_tier_imbalance",
        "small_tier_imbalance",
        "tier_disagreement",
        "large_share",
        "mean_leverage",
        "oi_velocity",
        "liq_velocity",
    ]
    # Self liquidation notional (USD volume), not just count.
    volume_features: list[str] = [
        "past_liq_notional_short",
        "past_liq_notional_long",
    ]
    # Market-wide (all-asset) intensity/volume and other-asset spillover.
    cross_asset_features: list[str] = [
        "market_liq_short",
        "market_liq_long",
        "market_liq_notional_short",
        "other_liq_short",
        "other_liq_notional_short",
    ]

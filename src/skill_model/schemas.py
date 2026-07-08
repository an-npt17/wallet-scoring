from enum import Enum

from pydantic import BaseModel


class SkillDimension(str, Enum):
    """Skill dimensions decomposed from the single baseline composite score.

    Maps to research-proposal.md §3.1: buy = Lim et al. (2022) entry skill,
    sell = Lim et al. (2022) exit skill, timing = Van Loon (2018) hit ratio,
    sizing = Van Loon (2018) win/loss ratio, liquidation = avoidance rate.
    """

    BUY = "buy"
    SELL = "sell"
    TIMING = "timing"
    SIZING = "sizing"
    LIQUIDATION = "liquidation"


class DimensionHyperparameters(BaseModel):
    """Population-level empirical-Bayes hyperparameters for one skill dimension.

    theta_w ~ N(mu, tau2); s_hat_w | theta_w ~ N(theta_w, sigma2_w).
    """

    dimension: SkillDimension
    n_wallets: int
    mu: float
    tau2: float
    mean_shrinkage: float


class WalletSkillPosterior(BaseModel):
    """Posterior skill estimate for one wallet on one dimension."""

    wallet: str
    dimension: SkillDimension
    n_trades: int
    raw_estimate: float
    posterior_mean: float
    posterior_sd: float
    ci_low: float
    ci_high: float
    shrinkage: float

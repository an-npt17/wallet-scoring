"""Empirical-Bayes hierarchical shrinkage for wallet skill dimensions.

Implements the Normal-Normal hierarchical model from research-proposal.md §3.2:

    theta_w ~ N(mu, tau2)
    s_hat_w | theta_w ~ N(theta_w, sigma2_w)

For a per-trade win-rate estimate s_hat_w = k_w / n_w (k_w wins out of n_w
trades), the sampling variance sigma2_w is approximated by the binomial
variance s_hat_w(1 - s_hat_w) / n_w.

This is the closed-form posterior of the conjugate Normal-Normal model
(equivalent, at the posterior-mean level, to the MCMC treatment the proposal
describes for the full model — Kosowski et al. 2006 / Berk & van Binsbergen
2015 use the same shrinkage identity). It is used here instead of PyMC/NumPyro
because the posterior mean and 95% credible interval have an exact closed
form for this model; sampling would only be needed for a non-conjugate
extension, which is future work.

Population hyperparameters (mu, tau2) are estimated by method of moments
(Morris, 1983): mu is the unweighted mean of the raw estimates, and tau2 is
the between-wallet variance in excess of the average sampling variance.
"""

import typing

import polars as pl

from src.skill_model.schemas import DimensionHyperparameters, SkillDimension

_MIN_SIGMA2 = 1e-6
_MIN_TAU2 = 1e-6


def _as_float(value: object, default: float) -> float:
    """Narrows a Float64 Series.mean()/var() result to a concrete float.

    polars types Series.mean()/var() as a broad PythonLiteral union (it also
    covers date/Decimal/timedelta columns for other dtypes), but every
    column this is called on is Float64, so the runtime value is always a
    plain float or None.
    """
    if value is None:
        return default
    return float(typing.cast(float, value))
_Z_95 = 1.959964


class EmpiricalBayesSkillService:
    """Fits the hierarchical shrinkage model to one win-rate-style dimension."""

    def fit_rate_dimension(
        self,
        df: pl.DataFrame,
        dimension: SkillDimension,
        wallet_col: str,
        rate_col: str,
        n_col: str,
        min_trades: int,
    ) -> tuple[pl.DataFrame, DimensionHyperparameters]:
        sub = (
            df.select([wallet_col, rate_col, n_col])
            .rename({wallet_col: "wallet", rate_col: "raw_estimate", n_col: "n_trades"})
            .drop_nulls()
            .filter(pl.col("n_trades") >= min_trades)
            .with_columns(
                (
                    pl.col("raw_estimate")
                    * (1.0 - pl.col("raw_estimate"))
                    / pl.col("n_trades")
                )
                .clip(lower_bound=_MIN_SIGMA2)
                .alias("sigma2")
            )
        )

        mu = _as_float(sub["raw_estimate"].mean(), default=0.0)
        raw_var = _as_float(sub["raw_estimate"].var(), default=0.0)
        mean_sigma2 = _as_float(sub["sigma2"].mean(), default=_MIN_SIGMA2)
        tau2 = max(raw_var - mean_sigma2, _MIN_TAU2)

        posterior = sub.with_columns(
            [
                (pl.col("sigma2") / (pl.col("sigma2") + tau2)).alias("shrinkage"),
                pl.lit(mu).alias("_mu"),
            ]
        ).with_columns(
            [
                (
                    (1.0 - pl.col("shrinkage")) * pl.col("raw_estimate")
                    + pl.col("shrinkage") * pl.col("_mu")
                ).alias("posterior_mean"),
                ((pl.col("sigma2") * tau2) / (pl.col("sigma2") + tau2))
                .sqrt()
                .alias("posterior_sd"),
            ]
        ).with_columns(
            [
                (pl.col("posterior_mean") - _Z_95 * pl.col("posterior_sd")).alias(
                    "ci_low"
                ),
                (pl.col("posterior_mean") + _Z_95 * pl.col("posterior_sd")).alias(
                    "ci_high"
                ),
                pl.lit(dimension.value).alias("dimension"),
            ]
        ).select(
            [
                "wallet",
                "dimension",
                "n_trades",
                "raw_estimate",
                "posterior_mean",
                "posterior_sd",
                "ci_low",
                "ci_high",
                "shrinkage",
            ]
        )

        hyperparams = DimensionHyperparameters(
            dimension=dimension,
            n_wallets=len(posterior),
            mu=mu,
            tau2=tau2,
            mean_shrinkage=_as_float(posterior["shrinkage"].mean(), default=0.0),
        )
        return posterior, hyperparams

    def fit_continuous_dimension(
        self,
        df: pl.DataFrame,
        dimension: SkillDimension,
        wallet_col: str,
        estimate_col: str,
        sigma2_col: str,
        n_col: str,
        min_trades: int,
    ) -> tuple[pl.DataFrame, DimensionHyperparameters]:
        sub = (
            df.select([wallet_col, estimate_col, sigma2_col, n_col])
            .rename({
                wallet_col: "wallet",
                estimate_col: "raw_estimate",
                sigma2_col: "sigma2",
                n_col: "n_trades",
            })
            .drop_nulls()
            .filter(pl.col("sigma2") > 0)
            .filter(pl.col("n_trades") >= min_trades)
        )

        mu = _as_float(sub["raw_estimate"].mean(), default=0.0)
        raw_var = _as_float(sub["raw_estimate"].var(), default=0.0)
        mean_sigma2 = _as_float(sub["sigma2"].mean(), default=_MIN_SIGMA2)
        tau2 = max(raw_var - mean_sigma2, _MIN_TAU2)

        posterior = sub.with_columns(
            [
                (pl.col("sigma2") / (pl.col("sigma2") + tau2)).alias("shrinkage"),
                pl.lit(mu).alias("_mu"),
            ]
        ).with_columns(
            [
                (
                    (1.0 - pl.col("shrinkage")) * pl.col("raw_estimate")
                    + pl.col("shrinkage") * pl.col("_mu")
                ).alias("posterior_mean"),
                ((pl.col("sigma2") * tau2) / (pl.col("sigma2") + tau2))
                .sqrt()
                .alias("posterior_sd"),
            ]
        ).with_columns(
            [
                (pl.col("posterior_mean") - _Z_95 * pl.col("posterior_sd")).alias(
                    "ci_low"
                ),
                (pl.col("posterior_mean") + _Z_95 * pl.col("posterior_sd")).alias(
                    "ci_high"
                ),
                pl.lit(dimension.value).alias("dimension"),
            ]
        ).select(
            [
                "wallet",
                "dimension",
                "n_trades",
                "raw_estimate",
                "posterior_mean",
                "posterior_sd",
                "ci_low",
                "ci_high",
                "shrinkage",
            ]
        )

        hyperparams = DimensionHyperparameters(
            dimension=dimension,
            n_wallets=len(posterior),
            mu=mu,
            tau2=tau2,
            mean_shrinkage=_as_float(posterior["shrinkage"].mean(), default=0.0),
        )
        return posterior, hyperparams

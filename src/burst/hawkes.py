"""
Exponential-kernel Hawkes baselines for liquidation-burst prediction.

Two published-method baselines, fit by maximum likelihood:

  * Univariate self-exciting Hawkes per asset (the classical self-exciting
    liquidation model; cf. crypto-endogeneity Hawkes literature). This is the
    named-method version of M1's "past-intensity" proxy.
  * Market-augmented Hawkes: self-excitation plus an all-asset (market) exciting
    term with a shared decay — a tractable stand-in for the multivariate
    cross-asset Hawkes of Cao & Palaash (DeFi liquidations cluster across venues).

Kernel g(tau) = alpha * beta * exp(-beta * tau), so the branching ratio is alpha
(stationary for alpha < 1). Parameters are fit on the training period only; the
per-bin score is the conditional intensity lambda(t) evaluated from the causal
event history up to the bin start, giving a ranking directly comparable to the
LightGBM PR-AUC on the same test bins.
"""

import numpy as np
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel
from scipy.optimize import minimize


class HawkesParams(BaseModel):
    mu: float
    alpha_self: float
    alpha_market: float
    beta: float


class AssetScores(BaseModel):
    asset: str
    # per test-bin arrays are returned separately (numpy); this holds fit info.
    params: HawkesParams
    train_events: int


def _excitation(
    events: NDArray[np.float64], query: NDArray[np.float64], beta: float
) -> NDArray[np.float64]:
    """
    A(q) = sum_{e < q} exp(-beta * (q - e)) for each query time q.

    Events strictly before the query (no same-instant leakage). Both inputs are
    assumed sorted ascending; result is aligned to `query`.
    """
    n_e = len(events)
    out = np.zeros(len(query))
    acc = 0.0
    prev = 0.0
    ei = 0
    for qi in range(len(query)):
        q = query[qi]
        while ei < n_e and events[ei] < q:
            acc = acc * np.exp(-beta * (events[ei] - prev)) + 1.0
            prev = events[ei]
            ei += 1
        out[qi] = acc * np.exp(-beta * (q - prev))
    return out


class HawkesBaselineService:
    """Fit and score exponential Hawkes burst baselines on the b01 panel split."""

    def __init__(self, seconds_scale: float = 300.0) -> None:
        # Scale time to bin units for numerical conditioning of beta.
        self._scale: float = seconds_scale

    def _nll(
        self,
        theta: NDArray[np.float64],
        a_self: NDArray[np.float64],
        a_mkt: NDArray[np.float64],
        comp_self: NDArray[np.float64],
        comp_mkt: NDArray[np.float64],
        span: float,
        use_market: bool,
    ) -> float:
        """
        Function to minimize for MLE of Hawkes params (log-likelihood).
        Args:
            theta: Log-transformed parameters [log(mu), log(alpha_self), log(alpha_market), log(beta)].
            a_self: Self-excitation terms for each event.
            a_mkt: Market-excitation terms for each event (if use_market is True).
            comp_self: Compensator terms for self-excitation.
            comp_mkt: Compensator terms for market-excitation (if use_market is True).
            span: Time span of the observation window.
            use_market: Whether to include market excitation in the likelihood.
        """
        mu = np.exp(theta[0])
        alpha_s = np.exp(theta[1])
        alpha_m = np.exp(theta[2]) if use_market else 0.0
        beta = np.exp(theta[3])
        lam = (
            mu
            + alpha_s * beta * a_self
            + (alpha_m * beta * a_mkt if use_market else 0.0)
        )
        lam = np.maximum(lam, 1e-12)
        ll = np.sum(np.log(lam))
        ll -= mu * span
        ll -= alpha_s * np.sum(comp_self)
        if use_market:
            ll -= alpha_m * np.sum(comp_mkt)
        return -float(ll)

    def _fit_asset(
        self,
        self_events: NDArray[np.float64],
        market_events: NDArray[np.float64],
        t0: float,
        t1: float,
        use_market: bool,
    ) -> HawkesParams:
        # Recompute excitation at each self event given a trial beta -> refit beta
        # via a small grid, optimizing (mu, alpha_s, alpha_m) analytically-ish by
        # numerical minimization for each beta, then keep the best.
        best: tuple[float, HawkesParams] | None = None
        for beta0 in (0.1, 0.3, 1.0, 3.0, 10.0):
            a_self = _excitation(self_events, self_events, beta0)
            a_mkt = (
                _excitation(market_events, self_events, beta0)
                if use_market
                else np.zeros_like(a_self)
            )
            comp_self = 1.0 - np.exp(-beta0 * (t1 - self_events))
            comp_mkt = (
                1.0 - np.exp(-beta0 * (t1 - market_events[market_events < t1]))
                if use_market
                else np.zeros(0)
            )
            span = t1 - t0

            def obj(theta: NDArray[np.float64]) -> float:
                # Fix beta to beta0 (theta[3] ignored via override).
                th = np.array([theta[0], theta[1], theta[2], np.log(beta0)])
                return self._nll(
                    th, a_self, a_mkt, comp_self, comp_mkt, span, use_market
                )

            x0 = np.log(
                np.array([max(len(self_events) / max(span, 1.0), 1e-6), 0.3, 0.3])
            )
            res = minimize(
                obj, x0, method="Nelder-Mead", options={"maxiter": 400, "xatol": 1e-3}
            )
            nll = float(res.fun)
            mu, alpha_s, alpha_m = np.exp(res.x[0]), np.exp(res.x[1]), np.exp(res.x[2])
            params = HawkesParams(
                mu=float(mu),
                alpha_self=float(min(alpha_s, 0.999)),
                alpha_market=float(min(alpha_m, 0.999)) if use_market else 0.0,
                beta=float(beta0),
            )
            if best is None or nll < best[0]:
                best = (nll, params)
        assert best is not None
        return best[1]

    def score(
        self,
        positions: pl.DataFrame,
        panel: pl.DataFrame,
        cutoff_ts: int,
        use_market: bool,
    ) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
        """
        Fit on events before `cutoff_ts`, score panel test bins (bin_ts >= cutoff).

        Returns pooled (scores, labels) over all assets' test bins.
        """
        s = self._scale
        liq = positions.filter(
            (pl.col("close_action") == "Liquidate") & (pl.col("close_ts") > 0)
        ).select(["asset", "close_ts"])
        market_all = np.sort(liq["close_ts"].to_numpy().astype(np.float64)) / s
        market_train = market_all[market_all < cutoff_ts / s]

        assets: list[str] = panel["asset"].unique().to_list()
        scores: list[NDArray[np.float64]] = []
        labels: list[NDArray[np.int8]] = []

        try:
            from tqdm import tqdm

            iterator = tqdm(assets, desc="Hawkes fit/score", unit="asset")
        except ImportError:
            iterator = assets

        for asset in iterator:
            ev = (
                np.sort(
                    liq.filter(pl.col("asset") == asset)["close_ts"]
                    .to_numpy()
                    .astype(np.float64)
                )
                / s
            )
            ev_train = ev[ev < cutoff_ts / s]
            if len(ev_train) < 20:
                continue
            t0, t1 = float(ev_train[0]), float(cutoff_ts / s)
            params = self._fit_asset(ev_train, market_train, t0, t1, use_market)

            test = panel.filter(
                (pl.col("asset") == asset) & (pl.col("bin_ts") >= cutoff_ts)
            )
            if test.height == 0:
                continue
            q = test["bin_ts"].to_numpy().astype(np.float64) / s
            a_self = _excitation(ev, q, params.beta)
            a_mkt = (
                _excitation(market_all, q, params.beta)
                if use_market
                else np.zeros_like(a_self)
            )
            lam = (
                params.mu
                + params.alpha_self * params.beta * a_self
                + params.alpha_market * params.beta * a_mkt
            )
            scores.append(lam)
            labels.append(test["label"].to_numpy().astype(np.int8))

        if not scores:
            return np.zeros(0), np.zeros(0, dtype=np.int8)
        return np.concatenate(scores), np.concatenate(labels)

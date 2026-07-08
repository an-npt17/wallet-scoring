"""Shared ranking / evaluation utilities for pipeline scoring stages.

Used by stage 14 (learned ranker) and stage 15 (rolling walk-forward). Kept
separate so both stages share one implementation of label reliability, graded
relevance, NDCG, Spearman, and the cross-validated LambdaMART ranker.
"""

import typing

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray
from scipy import stats
from sklearn.model_selection import KFold

N_RELEVANCE_GRADES = 5
DEFAULT_N_FOLDS = 5
DEFAULT_SEED = 42


def spearman(x: NDArray[np.float64], y: NDArray[np.float64], omit: bool = False) -> float:
    """scipy spearmanr with a concrete float return (scipy ships no usable stubs)."""
    policy = "omit" if omit else "propagate"
    result = typing.cast(typing.Any, stats.spearmanr(x, y, nan_policy=policy))
    value = float(result.statistic)
    return value if value == value else 0.0


def label_reliability(
    future_wr: NDArray[np.float64], n_future: NDArray[np.float64]
) -> float:
    """Fraction of future_win_rate variance that is NOT binomial sampling noise.

    rho = max(Var(future_wr) - E[p(1-p)/n], 0) / Var(future_wr). rho -> 0 means
    the label is indistinguishable from coin-flipping (nothing to rank on).
    """
    p_bar = float(np.nanmean(future_wr))
    noise = float(np.nanmean(p_bar * (1.0 - p_bar) / n_future))
    total = float(np.nanvar(future_wr))
    if total <= 0.0:
        return 0.0
    return max(total - noise, 0.0) / total


def grade_labels(future_wr: NDArray[np.float64]) -> NDArray[np.int32]:
    """Bin a continuous target into integer relevance grades for lambdarank."""
    ranks = stats.rankdata(future_wr, method="average") / len(future_wr)
    grades = np.floor(ranks * N_RELEVANCE_GRADES).astype(np.int32)
    return np.clip(grades, 0, N_RELEVANCE_GRADES - 1)


def ndcg_at_k(
    scores: NDArray[np.float64], relevance: NDArray[np.int32], k: int
) -> float:
    order = np.argsort(-scores)
    gains = 2.0 ** relevance[order] - 1.0
    discounts = 1.0 / np.log2(np.arange(2, len(scores) + 2))
    dcg = float(np.sum(gains[:k] * discounts[:k]))
    ideal = relevance[np.argsort(-relevance)]
    idcg = float(np.sum((2.0 ** ideal[:k] - 1.0) * discounts[:k]))
    return dcg / idcg if idcg > 0 else 0.0


def cv_learned_ranker(
    features: NDArray[np.float64],
    future_wr: NDArray[np.float64],
    relevance: NDArray[np.int32],
    k: int,
    n_folds: int = DEFAULT_N_FOLDS,
    seed: int = DEFAULT_SEED,
) -> tuple[NDArray[np.float64], list[float], list[float]]:
    """k-fold CV LambdaMART. Returns OOS predictions + per-fold NDCG@k / Spearman."""
    oos_pred = np.full(len(features), np.nan, dtype=np.float64)
    fold_ndcg: list[float] = []
    fold_spearman: list[float] = []
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    for train_idx, val_idx in kf.split(features):
        model = lgb.LGBMRanker(
            objective="lambdarank",
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=15,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            verbose=-1,
        )
        model.fit(features[train_idx], relevance[train_idx], group=[len(train_idx)])
        pred = np.asarray(model.predict(features[val_idx]), dtype=np.float64)
        oos_pred[val_idx] = pred
        fold_ndcg.append(ndcg_at_k(pred, relevance[val_idx], k))
        fold_spearman.append(spearman(pred, future_wr[val_idx]))
    return oos_pred, fold_ndcg, fold_spearman

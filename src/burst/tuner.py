"""
Optuna hyperparameter tuning for the burst LightGBM, optimizing
average-precision (PR-AUC) on a leakage-safe, time-ordered inner validation
slice carved from the training period. The held-out test period is never seen
during tuning.
"""

import logging

import lightgbm as lgb
import numpy as np
import optuna
import polars as pl
from numpy.typing import NDArray
from pydantic import BaseModel
from sklearn.metrics import average_precision_score

logger = logging.getLogger(__name__)


class TunerConfig(BaseModel):
    n_trials: int = 40
    inner_val_frac: float = 0.20  # last 20% of train (by time) = inner val
    max_estimators: int = 2000
    early_stopping_rounds: int = 50
    seed: int = 42


class BestParams(BaseModel):
    learning_rate: float
    num_leaves: int
    min_child_samples: int
    subsample: float
    colsample_bytree: float
    reg_alpha: float
    reg_lambda: float
    scale_pos_weight: float
    n_estimators: int


class BurstTunerService:
    def __init__(self, config: TunerConfig | None = None) -> None:
        self._cfg: TunerConfig = config or TunerConfig()

    def tune(self, train: pl.DataFrame, features: list[str]) -> BestParams:
        cfg = self._cfg
        inner = train.sort("bin_ts")
        cut = int(inner.height * (1.0 - cfg.inner_val_frac))
        tr, val = inner[:cut], inner[cut:]
        x_tr = tr.select(features).to_numpy()
        y_tr = tr["label"].to_numpy().astype(np.int8)
        x_val = val.select(features).to_numpy()
        y_val = val["label"].to_numpy().astype(np.int8)

        def objective(trial: optuna.Trial) -> float:
            params = {
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.15, log=True
                ),
                "num_leaves": trial.suggest_int("num_leaves", 15, 255),
                "min_child_samples": trial.suggest_int("min_child_samples", 20, 300),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
                "scale_pos_weight": trial.suggest_float(
                    "scale_pos_weight", 1.0, 200.0, log=True
                ),
            }
            model = lgb.LGBMClassifier(
                n_estimators=cfg.max_estimators,
                subsample_freq=1,
                random_state=cfg.seed,
                verbose=-1,
                **params,
            )
            model.fit(
                x_tr,
                y_tr,
                eval_set=[(x_val, y_val)],
                eval_metric="average_precision",
                callbacks=[
                    lgb.early_stopping(cfg.early_stopping_rounds, verbose=False)
                ],
            )
            p_val = np.asarray(model.predict_proba(x_val), dtype=np.float64)[:, 1]
            ap = float(average_precision_score(y_val, p_val))
            trial.set_user_attr(
                "best_iteration", int(model.best_iteration_ or cfg.max_estimators)
            )
            return ap

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=cfg.seed),
        )
        study.optimize(objective, n_trials=cfg.n_trials, show_progress_bar=True)

        best = study.best_trial
        logger.info("Best inner-val AP: %.4f", best.value)
        return BestParams(
            n_estimators=int(best.user_attrs["best_iteration"]),
            **{k: best.params[k] for k in best.params},
        )

    def build_model(self, params: BestParams) -> lgb.LGBMClassifier:
        return lgb.LGBMClassifier(
            n_estimators=params.n_estimators,
            learning_rate=params.learning_rate,
            num_leaves=params.num_leaves,
            min_child_samples=params.min_child_samples,
            subsample=params.subsample,
            subsample_freq=1,
            colsample_bytree=params.colsample_bytree,
            reg_alpha=params.reg_alpha,
            reg_lambda=params.reg_lambda,
            scale_pos_weight=params.scale_pos_weight,
            random_state=self._cfg.seed,
            verbose=-1,
        )

    @staticmethod
    def eval_scores(
        model: lgb.LGBMClassifier, test: pl.DataFrame, features: list[str]
    ) -> NDArray[np.float64]:
        x_te = test.select(features).to_numpy()
        return np.asarray(model.predict_proba(x_te), dtype=np.float64)[:, 1]

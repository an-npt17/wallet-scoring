"""Covariate-conditioned neural temporal point process for liquidation-burst
prediction.

The classical/neural Hawkes baselines (b02/b03) use only event *times*, ignoring
the crowding covariates; that is why they trail the feature classifier on PR-AUC.
This model closes that gap: a GRU runs causally over each asset's 5-minute bin
sequence of the 17 leakage-safe features, producing a hidden history state h_t.
The conditional burst intensity is lambda_t = softplus(w . h_t + b), and the
probability of at least one burst in the bin's horizon uses the point-process
hazard link P(burst) = 1 - exp(-lambda_t). Training maximises the Bernoulli
point-process likelihood of the burst label on the training period only; scoring
reads the hazard at each test bin from a single causal pass, so it is directly
comparable to the LightGBM / Hawkes / THP PR-AUC on the same test bins.
"""

import numpy as np
import polars as pl
import torch
from numpy.typing import NDArray
from pydantic import BaseModel
from torch import Tensor, nn

from src.burst.schemas import PanelConfig


class CovTPPConfig(BaseModel):
    hidden: int = 64
    n_layers: int = 1
    window: int = 256
    stride: int = 128
    epochs: int = 4
    batch_size: int = 128
    lr: float = 1e-3
    seed: int = 42
    min_asset_bins: int = 300


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


class CovTPPModel(nn.Module):
    def __init__(self, cfg: CovTPPConfig, n_features: int) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=n_features + 1,  # +1 for log inter-bin gap
            hidden_size=cfg.hidden,
            num_layers=cfg.n_layers,
            batch_first=True,
        )
        self.head = nn.Linear(cfg.hidden, 1)

    def intensity(self, x: Tensor, h0: Tensor | None = None) -> tuple[Tensor, Tensor]:
        # x: (B, T, F+1) -> lambda: (B, T); returns final hidden for carry.
        out, hn = self.gru(x, h0)
        lam = torch.nn.functional.softplus(self.head(out).squeeze(-1))
        return lam, hn


class CovTPPBaselineService:
    def __init__(self, config: CovTPPConfig | None = None) -> None:
        self._cfg = config or CovTPPConfig()
        pc = PanelConfig()
        self._features: list[str] = (
            pc.baseline_features
            + pc.crowding_features
            + pc.volume_features
            + pc.cross_asset_features
        )

    def _hazard_nll(self, lam: Tensor, y: Tensor, mask: Tensor) -> Tensor:
        # P = 1 - exp(-lam); NLL = -[ y*log(1-exp(-lam)) + (1-y)*(-lam) ].
        lam = lam.clamp(min=1e-6, max=30.0)
        log_p = torch.log(-torch.expm1(-lam) + 1e-8)  # log P(event)
        log_1mp = -lam  # log P(no event)
        nll = -(y * log_p + (1.0 - y) * log_1mp) * mask
        return nll.sum() / mask.sum().clamp(min=1.0)

    def fit_score(
        self, panel: pl.DataFrame, cutoff_ts: int
    ) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
        cfg = self._cfg
        _set_seed(cfg.seed)
        feats = self._features
        panel = panel.sort(["asset", "bin_ts"])

        # Standardize features on training rows only.
        train_rows = panel.filter(pl.col("bin_ts") < cutoff_ts)
        mean = train_rows.select(feats).mean().to_numpy().reshape(-1)
        std = train_rows.select(feats).std().to_numpy().reshape(-1)
        std = np.where(std < 1e-8, 1.0, std)

        assets: list[str] = panel["asset"].unique().to_list()
        # Per-asset arrays: standardized features, dt, label, ts.
        seqs: dict[str, tuple[NDArray[np.float32], NDArray[np.float64], NDArray[np.int8], NDArray[np.int64]]] = {}
        for a in assets:
            sub = panel.filter(pl.col("asset") == a)
            if sub.height < cfg.min_asset_bins:
                continue
            x = (sub.select(feats).to_numpy() - mean) / std
            ts = sub["bin_ts"].to_numpy().astype(np.int64)
            dt = np.zeros(len(ts))
            dt[1:] = np.log1p(np.diff(ts) / 300.0)
            xd = np.concatenate([x, dt[:, None]], axis=1).astype(np.float32)
            y = sub["label"].to_numpy().astype(np.int8)
            seqs[a] = (xd, dt, y, ts)

        model = CovTPPModel(cfg, n_features=len(feats))
        opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)

        # Training windows from TRAIN bins only (causal target = burst label).
        windows: list[tuple[NDArray[np.float32], NDArray[np.int8]]] = []
        for a, (xd, _dt, y, ts) in seqs.items():
            tr = ts < cutoff_ts
            xt, yt = xd[tr], y[tr]
            for start in range(0, max(len(xt) - 1, 1), cfg.stride):
                xs, ys = xt[start: start + cfg.window], yt[start: start + cfg.window]
                if len(xs) >= 16:
                    windows.append((xs, ys))

        try:
            from tqdm import tqdm
            epoch_iter = tqdm(range(cfg.epochs), desc="CovTPP train", unit="epoch")
        except ImportError:
            epoch_iter = range(cfg.epochs)

        model.train()
        for _ in epoch_iter:
            perm = np.random.permutation(len(windows))
            for i in range(0, len(perm), cfg.batch_size):
                idx = perm[i: i + cfg.batch_size]
                lens = [len(windows[j][0]) for j in idx]
                mx = max(lens)
                bx = torch.zeros(len(idx), mx, len(feats) + 1)
                by = torch.zeros(len(idx), mx)
                bm = torch.zeros(len(idx), mx)
                for r, j in enumerate(idx):
                    xs, ys = windows[j]
                    n = len(xs)
                    bx[r, :n] = torch.from_numpy(xs)
                    by[r, :n] = torch.from_numpy(ys.astype(np.float32))
                    bm[r, :n] = 1.0
                lam, _ = model.intensity(bx)
                loss = self._hazard_nll(lam, by, bm)
                opt.zero_grad()
                loss.backward()
                opt.step()

        # Score: one causal pass over each asset's full sequence, read test bins.
        model.eval()
        scores: list[NDArray[np.float64]] = []
        labels: list[NDArray[np.int8]] = []
        with torch.no_grad():
            for a, (xd, _dt, y, ts) in seqs.items():
                test_mask = ts >= cutoff_ts
                if not test_mask.any():
                    continue
                bx = torch.from_numpy(xd).unsqueeze(0)
                lam, _ = model.intensity(bx)
                p = (1.0 - torch.exp(-lam.squeeze(0))).cpu().numpy()
                scores.append(p[test_mask])
                labels.append(y[test_mask])

        if not scores:
            return np.zeros(0), np.zeros(0, dtype=np.int8)
        return np.concatenate(scores), np.concatenate(labels)

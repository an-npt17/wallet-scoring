"""Spatio-temporal GNN for liquidation-burst prediction.

Liquidation cascades spill across assets; the LightGBM only sees this through
hand-built market/spillover scalars, and the Hawkes market term could not exploit
it. This model treats the 40 assets as nodes on the shared global 5-minute grid.
At each time step a graph layer mixes every active asset's 17-feature vector with
a market-aggregate message (a fully-connected / mean-field cross-asset graph), and
a per-node GRU carries temporal state. The burst hazard per node/bin is
P = 1 - exp(-softplus(w . h + b)), trained by point-process likelihood on the
training period and scored on the SAME test bins as b01-b04.

Implementation note: the panel is dense in time but sparse per asset (assets have
different active spans). We build fixed-length time windows on the global grid;
within a window each row is (n_assets x features) with a presence mask, so absent
assets neither send nor receive messages and contribute no loss.
"""

import numpy as np
import polars as pl
import torch
from numpy.typing import NDArray
from pydantic import BaseModel
from torch import Tensor, nn

from src.burst.schemas import PanelConfig


class STGNNConfig(BaseModel):
    hidden: int = 48
    window: int = 64  # global-grid time steps per training window
    stride: int = 32
    epochs: int = 4
    batch_size: int = 16  # windows per batch
    lr: float = 1e-3
    seed: int = 42


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


class STGNNModel(nn.Module):
    """One mean-field graph mix per step + GRUCell temporal recurrence per node."""

    def __init__(self, cfg: STGNNConfig, n_features: int) -> None:
        super().__init__()
        self.encode = nn.Linear(n_features, cfg.hidden)
        # graph message: combine self embedding with market-mean of neighbours.
        self.graph = nn.Linear(cfg.hidden * 2, cfg.hidden)
        self.cell = nn.GRUCell(cfg.hidden, cfg.hidden)
        self.head = nn.Linear(cfg.hidden, 1)
        self.hidden = cfg.hidden

    def forward(self, x: Tensor, present: Tensor) -> Tensor:
        # x: (B, T, N, F); present: (B, T, N) in {0,1}. Returns lambda (B,T,N).
        b, t, n, _ = x.shape
        h = torch.zeros(b, n, self.hidden, device=x.device)
        lams: list[Tensor] = []
        for step in range(t):
            xt = x[:, step]  # (B,N,F)
            m = present[:, step].unsqueeze(-1)  # (B,N,1)
            e = torch.relu(self.encode(xt)) * m  # node embeddings, zeroed if absent
            # mean-field neighbour message = mean over present nodes.
            denom = m.sum(dim=1, keepdim=True).clamp(min=1.0)
            market = (e.sum(dim=1, keepdim=True) / denom).expand(-1, n, -1)
            g = torch.relu(self.graph(torch.cat([e, market], dim=-1)))  # (B,N,H)
            h_new = self.cell(g.reshape(b * n, -1), h.reshape(b * n, -1)).reshape(b, n, -1)
            h = torch.where(m > 0, h_new, h)  # carry state only for present nodes
            lams.append(torch.nn.functional.softplus(self.head(h).squeeze(-1)))
        return torch.stack(lams, dim=1)  # (B,T,N)


class STGNNBaselineService:
    def __init__(self, config: STGNNConfig | None = None) -> None:
        self._cfg = config or STGNNConfig()
        pc = PanelConfig()
        self._features: list[str] = (
            pc.baseline_features
            + pc.crowding_features
            + pc.volume_features
            + pc.cross_asset_features
        )
        self._bin_seconds = pc.bin_seconds

    def _hazard_nll(self, lam: Tensor, y: Tensor, mask: Tensor) -> Tensor:
        lam = lam.clamp(min=1e-6, max=30.0)
        log_p = torch.log(-torch.expm1(-lam) + 1e-8)
        nll = -(y * log_p + (1.0 - y) * (-lam)) * mask
        return nll.sum() / mask.sum().clamp(min=1.0)

    def fit_score(
        self, panel: pl.DataFrame, cutoff_ts: int
    ) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
        cfg = self._cfg
        _set_seed(cfg.seed)
        feats = self._features
        bs = self._bin_seconds

        assets: list[str] = sorted(panel["asset"].unique().to_list())
        aidx = {a: i for i, a in enumerate(assets)}
        n = len(assets)

        # Standardize on train rows.
        train_rows = panel.filter(pl.col("bin_ts") < cutoff_ts)
        mean = train_rows.select(feats).mean().to_numpy().reshape(-1)
        std = train_rows.select(feats).std().to_numpy().reshape(-1)
        std = np.where(std < 1e-8, 1.0, std)

        # Global grid index for every row.
        p = panel.with_columns(
            (pl.col("bin_ts") // bs).alias("gbin"),
            pl.col("asset").replace_strict(aidx, return_dtype=pl.Int64).alias("aid"),
        ).sort("gbin")
        gmin, gmax = p["gbin"].min(), p["gbin"].max()
        assert isinstance(gmin, int) and isinstance(gmax, int)
        g0 = gmin
        g_cut = cutoff_ts // bs
        n_steps = gmax - g0 + 1

        # Dense tensors over the full global grid.
        F = len(feats)
        X = np.zeros((n_steps, n, F), dtype=np.float32)
        Y = np.zeros((n_steps, n), dtype=np.float32)
        P = np.zeros((n_steps, n), dtype=np.float32)  # presence
        gb = p["gbin"].to_numpy().astype(np.int64) - g0
        ai = p["aid"].to_numpy().astype(np.int64)
        xz = (p.select(feats).to_numpy() - mean) / std
        yz = p["label"].to_numpy().astype(np.float32)
        X[gb, ai] = xz.astype(np.float32)
        Y[gb, ai] = yz
        P[gb, ai] = 1.0
        is_test = (np.arange(n_steps) + g0) >= g_cut  # per-step test flag

        model = STGNNModel(cfg, n_features=F)
        opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)

        # Training windows over the TRAIN portion of the grid.
        train_steps = int((np.arange(n_steps) + g0 < g_cut).sum())
        starts = list(range(0, max(train_steps - cfg.window, 1), cfg.stride))

        try:
            from tqdm import tqdm
            epoch_iter = tqdm(range(cfg.epochs), desc="STGNN train", unit="epoch")
        except ImportError:
            epoch_iter = range(cfg.epochs)

        model.train()
        for _ in epoch_iter:
            np.random.shuffle(starts)
            for i in range(0, len(starts), cfg.batch_size):
                chunk = starts[i: i + cfg.batch_size]
                bx = torch.from_numpy(np.stack([X[s: s + cfg.window] for s in chunk]))
                by = torch.from_numpy(np.stack([Y[s: s + cfg.window] for s in chunk]))
                bp = torch.from_numpy(np.stack([P[s: s + cfg.window] for s in chunk]))
                lam = model(bx, bp)
                loss = self._hazard_nll(lam, by, bp)
                opt.zero_grad()
                loss.backward()
                opt.step()

        # Score: causal sweep over the full grid in windows, keep test steps.
        model.eval()
        scores: list[NDArray[np.float64]] = []
        labels: list[NDArray[np.int8]] = []
        with torch.no_grad():
            W = cfg.window
            for s in range(0, n_steps, W):
                sl = slice(s, min(s + W, n_steps))
                bx = torch.from_numpy(X[sl]).unsqueeze(0)
                bp = torch.from_numpy(P[sl]).unsqueeze(0)
                lam = model(bx, bp).squeeze(0).cpu().numpy()  # (T',N)
                prob = 1.0 - np.exp(-lam)
                steps = np.arange(sl.start, sl.stop)
                for local, step in enumerate(steps):
                    if not is_test[step]:
                        continue
                    present = P[step] > 0
                    if present.any():
                        scores.append(prob[local][present].astype(np.float64))
                        labels.append(Y[step][present].astype(np.int8))

        if not scores:
            return np.zeros(0), np.zeros(0, dtype=np.int8)
        return np.concatenate(scores), np.concatenate(labels)

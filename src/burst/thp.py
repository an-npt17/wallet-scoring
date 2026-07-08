"""
Compact Transformer Hawkes Process (THP) baseline for liquidation-burst
prediction (Zuo et al., ICML 2020, arXiv:2002.09291).

A self-attention encoder over each asset's liquidation event stream produces a
causal history embedding; the conditional intensity on the interval after event
i is lambda(t) = softplus(v . h_i + b + a * (t - t_i)). The model is trained by
temporal-point-process maximum likelihood (event log-intensity minus the
Monte-Carlo compensator). For scoring, lambda is evaluated at each panel bin
start from the last L events before it, giving a per-bin ranking directly
comparable to the LightGBM / classical-Hawkes PR-AUC on the same test bins.

Long streams are handled with a fixed context window of L events (sliding for
training, last-L lookup for scoring) so attention stays O(L^2).
"""

import numpy as np
import polars as pl
import torch
from numpy.typing import NDArray
from pydantic import BaseModel
from torch import Tensor, nn


class THPConfig(BaseModel):
    d_model: int = 32
    n_heads: int = 2
    n_layers: int = 2
    context_len: int = 64
    train_stride: int = 32
    mc_samples: int = 8
    epochs: int = 3
    batch_size: int = 256
    lr: float = 1e-3
    seed: int = 42
    time_scale: float = 300.0  # seconds per unit (5-min bins)
    min_asset_events: int = 20


def _set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)


class _TemporalEncoding(nn.Module):
    def __init__(self, d_model: int) -> None:
        super().__init__()
        div = torch.exp(
            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
        )
        self.register_buffer("div", div)
        self.d_model = d_model

    def forward(self, t: Tensor) -> Tensor:
        # t: (B, L) -> (B, L, d_model)
        ang = t.unsqueeze(-1) * self.get_buffer("div")
        return torch.cat([torch.sin(ang), torch.cos(ang)], dim=-1)


class THPModel(nn.Module):
    def __init__(self, cfg: THPConfig, n_assets: int) -> None:
        super().__init__()
        self.cfg = cfg
        self.temporal = _TemporalEncoding(cfg.d_model)
        self.asset_emb = nn.Embedding(n_assets, cfg.d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.d_model * 4,
            batch_first=True,
            dropout=0.0,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=cfg.n_layers)
        self.intensity_w = nn.Linear(cfg.d_model, 1)
        self.decay = nn.Parameter(torch.tensor(0.0))
        self.base = nn.Parameter(torch.tensor(0.0))

    def encode(self, t: Tensor, asset_id: Tensor, pad_mask: Tensor) -> Tensor:
        # t: (B,L) relative times; asset_id: (B,); pad_mask: (B,L) True=pad.
        h = self.temporal(t) + self.asset_emb(asset_id).unsqueeze(1)
        causal = torch.triu(
            torch.ones(t.size(1), t.size(1), dtype=torch.bool, device=t.device), 1
        )
        return self.encoder(h, mask=causal, src_key_padding_mask=pad_mask)

    def intensity(self, h_prev: Tensor, dt: Tensor) -> Tensor:
        return torch.nn.functional.softplus(
            self.intensity_w(h_prev).squeeze(-1) + self.base + self.decay * dt
        )

    def loglik(self, t: Tensor, asset_id: Tensor, pad_mask: Tensor) -> Tensor:
        h = self.encode(t, asset_id, pad_mask)  # (B,L,d)
        dt = (t[:, 1:] - t[:, :-1]).clamp(min=0.0)  # (B,L-1)
        valid = ~pad_mask[:, 1:]  # event i>=1 present
        h_prev = h[:, :-1, :]  # (B,L-1,d)

        lam_ev = self.intensity(h_prev, dt)  # intensity at event t_i
        event_term = torch.log(lam_ev.clamp(min=1e-8)) * valid

        u = torch.rand(self.cfg.mc_samples, *dt.shape, device=t.device)  # (S,B,L-1)
        comp = torch.zeros_like(dt)
        for s in range(self.cfg.mc_samples):
            comp = comp + self.intensity(h_prev, dt * u[s])
        comp = comp / self.cfg.mc_samples * dt * valid  # integral estimate per interval

        n = valid.sum().clamp(min=1.0)
        return (event_term.sum() - comp.sum()) / n


class THPBaselineService:
    def __init__(self, config: THPConfig | None = None) -> None:
        self._cfg = config or THPConfig()

    def _windows(
        self, ev: NDArray[np.float64], aid: int, cfg: THPConfig
    ) -> list[tuple[NDArray[np.float64], int]]:
        out: list[tuple[NDArray[np.float64], int]] = []
        L = cfg.context_len
        if len(ev) < 2:
            return out
        for start in range(0, max(len(ev) - 1, 1), cfg.train_stride):
            win = ev[start : start + L]
            if len(win) >= 2:
                out.append((win, aid))
        return out

    def _collate(
        self, batch: list[tuple[NDArray[np.float64], int]], L: int
    ) -> tuple[Tensor, Tensor, Tensor]:
        b = len(batch)
        t = torch.zeros(b, L)
        pad = torch.ones(b, L, dtype=torch.bool)
        aid = torch.zeros(b, dtype=torch.long)
        for i, (win, a) in enumerate(batch):
            n = len(win)
            t[i, :n] = torch.from_numpy((win - win[0]).astype(np.float32))
            pad[i, :n] = False
            aid[i] = a
        return t, aid, pad

    def fit_score(
        self, positions: pl.DataFrame, panel: pl.DataFrame, cutoff_ts: int
    ) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
        cfg = self._cfg
        _set_seed(cfg.seed)
        s = cfg.time_scale

        liq = positions.filter(
            (pl.col("close_action") == "Liquidate") & (pl.col("close_ts") > 0)
        ).select(["asset", "close_ts"])
        assets: list[str] = panel["asset"].unique().to_list()
        aid_map = {a: i for i, a in enumerate(assets)}

        ev_by_asset: dict[str, NDArray[np.float64]] = {}
        for a in assets:
            e = (
                np.sort(
                    liq.filter(pl.col("asset") == a)["close_ts"]
                    .to_numpy()
                    .astype(np.float64)
                )
                / s
            )
            ev_by_asset[a] = e

        # Training windows from train-period events only.
        train_windows: list[tuple[NDArray[np.float64], int]] = []
        for a in assets:
            e_tr = ev_by_asset[a][ev_by_asset[a] < cutoff_ts / s]
            if len(e_tr) < cfg.min_asset_events:
                continue
            train_windows.extend(self._windows(e_tr, aid_map[a], cfg))

        model = THPModel(cfg, n_assets=len(assets))
        opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)

        try:
            from tqdm import tqdm

            epoch_iter = tqdm(range(cfg.epochs), desc="THP train", unit="epoch")
        except ImportError:
            epoch_iter = range(cfg.epochs)

        model.train()
        for _ in epoch_iter:
            perm = np.random.permutation(len(train_windows))
            for i in range(0, len(perm), cfg.batch_size):
                idx = perm[i : i + cfg.batch_size]
                batch = [train_windows[j] for j in idx]
                t, aid, pad = self._collate(batch, cfg.context_len)
                loss = -model.loglik(t, aid, pad)
                opt.zero_grad()
                loss.backward()
                opt.step()

        return self._score(model, panel, ev_by_asset, aid_map, cutoff_ts, cfg)

    def _score(
        self,
        model: THPModel,
        panel: pl.DataFrame,
        ev_by_asset: dict[str, NDArray[np.float64]],
        aid_map: dict[str, int],
        cutoff_ts: int,
        cfg: THPConfig,
    ) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
        s = cfg.time_scale
        L = cfg.context_len
        model.eval()
        scores: list[NDArray[np.float64]] = []
        labels: list[NDArray[np.int8]] = []

        for a in aid_map:
            test = panel.filter(
                (pl.col("asset") == a) & (pl.col("bin_ts") >= cutoff_ts)
            )
            if test.height == 0:
                continue
            ev = ev_by_asset[a]
            if len(ev) < 2:
                scores.append(np.full(test.height, -1e9))
                labels.append(test["label"].to_numpy().astype(np.int8))
                continue
            q = test["bin_ts"].to_numpy().astype(np.float64) / s
            # last event index strictly before each query
            j = np.searchsorted(ev, q, side="left") - 1
            lam = np.zeros(len(q))
            valid = j >= 0
            qi = np.where(valid)[0]
            with torch.no_grad():
                for c in range(0, len(qi), cfg.batch_size):
                    sel = qi[c : c + cfg.batch_size]
                    ctx_list: list[tuple[NDArray[np.float64], int]] = []
                    dts: list[float] = []
                    for k in sel:
                        end = j[k] + 1
                        win = ev[max(0, end - L) : end]
                        ctx_list.append((win, aid_map[a]))
                        dts.append(float(q[k] - win[-1]))
                    t, aid, pad = self._collate(ctx_list, L)
                    h = model.encode(t, aid, pad)
                    # hidden at the last real event of each row
                    lengths = (~pad).sum(dim=1) - 1
                    h_last = h[torch.arange(h.size(0)), lengths, :]
                    dt_t = torch.tensor(dts, dtype=torch.float32)
                    lam_b = model.intensity(h_last, dt_t).cpu().numpy()
                    lam[sel] = lam_b
            scores.append(lam)
            labels.append(test["label"].to_numpy().astype(np.int8))

        if not scores:
            return np.zeros(0), np.zeros(0, dtype=np.int8)
        return np.concatenate(scores), np.concatenate(labels)

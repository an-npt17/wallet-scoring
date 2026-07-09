"""Generate the worked Hawkes-process example figure (EN + VI) for the EDA report."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ORANGE = "#b5651d"
PURPLE = "#5b3a8e"
BLUE = "#2b5b84"
GREY = "#444444"

RNG = np.random.default_rng(3)


def simulate_hawkes(mu: float, alpha: float, beta: float, t_max: float) -> np.ndarray:
    """Thinning simulation of a 1-D exponential-kernel Hawkes process."""
    events: list[float] = []
    t = 0.0
    while t < t_max:
        lam_upper = mu + sum(
            alpha * np.exp(-beta * (t - te)) for te in events if te < t
        ) + alpha * 5.0
        t += RNG.exponential(1.0 / max(lam_upper, 1e-6))
        if t >= t_max:
            break
        lam_t = mu + sum(alpha * np.exp(-beta * (t - te)) for te in events if te < t)
        if RNG.uniform(0, lam_upper) <= lam_t:
            events.append(t)
    return np.array(events)


def intensity_path(
    grid: np.ndarray, events: np.ndarray, mu: float, alpha: float, beta: float
) -> np.ndarray:
    lam = np.full_like(grid, mu)
    for te in events:
        lam += np.where(grid >= te, alpha * np.exp(-beta * (grid - te)), 0.0)
    return lam


def make_figure(lang: str, out_path: Path) -> None:
    mu, alpha, beta = 0.3, 0.55, 0.9
    t_max = 25.0
    events = simulate_hawkes(mu, alpha, beta, t_max)
    grid = np.linspace(0, t_max, 2000)
    lam = intensity_path(grid, events, mu, alpha, beta)

    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.plot(grid, lam, color=ORANGE, lw=1.8, zorder=3)
    ax.fill_between(grid, 0, lam, color=ORANGE, alpha=0.12, zorder=1)
    ax.axhline(mu, color=BLUE, lw=1.2, ls="--", zorder=2)
    ax.scatter(
        events, np.zeros_like(events), marker="|", s=260, color=GREY, lw=1.6, zorder=4
    )

    if lang == "en":
        mu_label = r"baseline $\mu$"
        ev_label = "liquidation events $t_j$"
        title = (
            r"Self-exciting intensity $\lambda(t)=\mu+\sum_j \alpha e^{-\beta(t-t_j)}$"
            f"  ($\\mu$={mu}, $\\alpha$={alpha}, $\\beta$={beta})"
        )
        xlabel = "time (bins)"
        ylabel = r"$\lambda(t)$"
        burst_txt = "cluster $\\rightarrow$ burst"
    else:
        mu_label = r"nền $\mu$"
        ev_label = "sự kiện thanh lý $t_j$"
        title = (
            r"Cường độ tự kích thích $\lambda(t)=\mu+\sum_j \alpha e^{-\beta(t-t_j)}$"
            f"  ($\\mu$={mu}, $\\alpha$={alpha}, $\\beta$={beta})"
        )
        xlabel = "thời gian (bin)"
        ylabel = r"$\lambda(t)$"
        burst_txt = "cụm sự kiện $\\rightarrow$ bùng phát"

    ax.set_title(title, fontsize=10)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xlim(0, t_max)
    top = float(lam.max()) * 1.25
    ax.set_ylim(-0.55, top)
    ax.tick_params(labelsize=8)

    # annotate baseline (upper-right, clear of the event ticks) and one event cluster
    ax.text(
        t_max * 0.99, mu + top * 0.05, mu_label, color=BLUE, fontsize=8, ha="right", va="bottom"
    )

    # find a cluster of >=3 close events to annotate as a "burst"
    cluster_idx = None
    for i in range(len(events) - 2):
        if events[i + 2] - events[i] < 2.0:
            cluster_idx = i
            break
    if cluster_idx is not None:
        cx = events[cluster_idx : cluster_idx + 3].mean()
        cy = lam[np.searchsorted(grid, cx)]
        ax.annotate(
            burst_txt,
            xy=(cx, cy),
            xytext=(cx + t_max * 0.18, cy + top * 0.15),
            fontsize=8,
            color=PURPLE,
            arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.0),
        )

    ax.text(
        t_max * 0.01,
        -0.5,
        ev_label,
        color=GREY,
        fontsize=8,
        ha="left",
        va="top",
    )

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    make_figure("en", root / "docs" / "figs" / "hawkes_example.pdf")
    make_figure("vi", root / "docs" / "figs_vi" / "hawkes_example.pdf")
    print("wrote hawkes_example.pdf (en + vi)")

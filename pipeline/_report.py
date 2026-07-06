"""Shared output-saving utilities for scripts/ and pipeline/ analysis scripts.

Every script's printed report + matplotlib figures get saved under
pipeline/outputs/<script_name>/ so results survive after the terminal closes.
"""

import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

OUTPUTS_ROOT = Path("pipeline/outputs")


def get_output_dir(script_name: str) -> Path:
    out_dir = OUTPUTS_ROOT / script_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


class _Tee:
    def __init__(self, *streams: TextIO) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        for s in self._streams:
            s.write(data)
        return len(data)

    def flush(self) -> None:
        for s in self._streams:
            s.flush()


@contextmanager
def tee_stdout(out_dir: Path, filename: str = "results.txt") -> Generator[None]:
    """Duplicates everything printed to stdout into out_dir/filename as well."""
    real_stdout = sys.stdout
    with open(out_dir / filename, "w") as f:
        sys.stdout = _Tee(real_stdout, f)  # type: ignore[assignment]
        try:
            yield
        finally:
            sys.stdout = real_stdout


def save_fig(fig: Figure, out_dir: Path, filename: str) -> None:
    fig.savefig(out_dir / filename, dpi=150, bbox_inches="tight")
    plt.close(fig)

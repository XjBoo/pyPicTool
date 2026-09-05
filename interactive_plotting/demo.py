"""Artificial data used only for manual interaction checks."""

import numpy as np
import matplotlib.pyplot as plt

from .core import PlotSession, create_interactive_plot
from .model import SeriesData


def make_demo_series(seed=None) -> list[SeriesData]:
    """Build the six-panel, two-series artificial demo without showing a GUI."""

    rng = np.random.default_rng(seed)
    frames = np.arange(100)
    series_list = []

    for index in range(6):
        panel = divmod(index, 2)
        signal_number = index + 1
        sine_values = np.sin(frames * (0.05 * signal_number))
        sine_values += rng.normal(0, 0.1, frames.size)
        cosine_values = np.cos(frames * (0.03 * signal_number))
        cosine_values += rng.normal(0, 0.15, frames.size)

        series_list.extend(
            [
                SeriesData(
                    frames=frames,
                    values=sine_values,
                    label="Sine signal",
                    panel=panel,
                    color="#3478A8",
                    panel_title=f"{signal_number:02d}   Signal comparison",
                ),
                SeriesData(
                    frames=frames,
                    values=cosine_values,
                    label="Cosine signal",
                    panel=panel,
                    color="#D58945",
                    panel_title=f"{signal_number:02d}   Signal comparison",
                ),
            ]
        )

    return series_list


def show_demo() -> PlotSession:
    """Build and show the artificial six-panel demo for manual testing."""

    session = create_interactive_plot(make_demo_series())
    plt.show()
    return session

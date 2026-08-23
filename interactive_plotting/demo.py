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
        red_values = np.sin(frames * (0.05 * signal_number))
        red_values += rng.normal(0, 0.1, frames.size)
        blue_values = np.cos(frames * (0.03 * signal_number))
        blue_values += rng.normal(0, 0.15, frames.size)

        series_list.extend(
            [
                SeriesData(
                    frames=frames,
                    values=red_values,
                    label=f"Signal {signal_number} (red)",
                    panel=panel,
                    color="red",
                    panel_title=f"Interactive Plot {signal_number}",
                ),
                SeriesData(
                    frames=frames,
                    values=blue_values,
                    label=f"Signal {signal_number} (blue)",
                    panel=panel,
                    color="blue",
                    panel_title=f"Interactive Plot {signal_number}",
                    line_color="blue",
                    line_alpha=0.5,
                ),
            ]
        )

    return series_list


def show_demo() -> PlotSession:
    """Build and show the artificial six-panel demo for manual testing."""

    session = create_interactive_plot(make_demo_series())
    session.figure.set_size_inches(12, 10, forward=True)
    session.figure.tight_layout()
    plt.show()
    return session

"""Public interfaces for reusable interactive plotting and its demo."""

from .core import PlotSession, create_interactive_plot
from .demo import make_demo_series, show_demo
from .model import SeriesData

__all__ = [
    "PlotSession",
    "SeriesData",
    "create_interactive_plot",
    "make_demo_series",
    "show_demo",
]

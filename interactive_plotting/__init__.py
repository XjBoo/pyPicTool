"""Public interfaces for reusable interactive plotting and its demo."""

from .core import PlotSession, SeriesHandle, create_interactive_plot
from .api import figure, build_figure
from .demo import make_demo_series, show_demo
from .model import SeriesData, FigureSpec, PanelSpec, TooltipContext, SuptitleStyle

__all__ = [
    "figure",
    "build_figure",
    "FigureSpec",
    "PanelSpec",
    "TooltipContext",
    "SuptitleStyle",
    "SeriesHandle",
    "PlotSession",
    "SeriesData",
    "create_interactive_plot",
    "make_demo_series",
    "show_demo",
]

"""Explicit figure/subplot/plot descriptions, rendered once by build()."""

from __future__ import annotations

from dataclasses import replace
from math import isfinite
from numbers import Integral, Real

from matplotlib.colors import to_rgba
from matplotlib.typing import ColorType
from numpy.typing import ArrayLike

from .core import PlotSession, _build_figure
from .model import FigureSpec, PanelSpec, SeriesData


_COLORS = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")
# Same symbols as the README listing, grouped for readability.
_MARKERS = frozenset("os^v<>Ddp" "hH*+x.,|_" "12348PX")
_LINESTYLES = {"-": "-", "--": "--", "-.": "-.", ":": ":",
               "solid": "-", "dashed": "--", "dashdot": "-.",
               "dotted": ":", "None": "None", "none": "None", "": "None"}


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _positive_size(value: float, name: str) -> float:
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or value <= 0):
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


def _text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value


class Subplot:
    """A figure-owned subplot. plot() appends data until its figure is built."""

    __slots__ = ("_owner", "_spec")

    def __init__(self, owner: FigureBuilder, spec: PanelSpec) -> None:
        self._owner = owner
        self._spec = spec

    def plot(
        self, x: ArrayLike, y: ArrayLike, *, label: str | None = None,
        color: ColorType | None = None, marker: str | None = "o",
        linestyle: str = "-", linewidth: float = 1.35,
        markersize: float = 10 ** 0.5,
    ) -> Subplot:
        """Append one series, copying its data; return this subplot for chaining.

        Use marker=None for a line alone, linestyle="None" for points alone.
        Sizes are in points; the default √10 keeps the marker area at 10 pt².
        Missing y values break the line and skip points.
        Invalid data/styles raise ValueError without appending a partial series.
        """
        self._owner._require_mutable()
        label = "" if label is None else _text(label, "label")
        if color is None:
            color = _COLORS[len(self._spec.series) % len(_COLORS)]
        try:
            # Resolve colors now so later global style changes cannot alter them.
            rgba = to_rgba(color)
        except (TypeError, ValueError) as error:
            raise ValueError("color must be a valid Matplotlib color") from error
        if marker is not None and (not isinstance(marker, str) or marker not in _MARKERS):
            raise ValueError("marker must be a supported point symbol or None")
        if not isinstance(linestyle, str) or linestyle not in _LINESTYLES:
            raise ValueError("linestyle must be '-', '--', '-.', ':', 'None', "
                             "or a solid/dashed/dashdot/dotted alias")
        linestyle = _LINESTYLES[linestyle]
        if marker is None and linestyle == "None":
            raise ValueError("marker and linestyle cannot both be disabled")
        linewidth = _positive_size(linewidth, "linewidth")
        markersize = _positive_size(markersize, "markersize")
        item = SeriesData(
            x, y, label, panel=self._spec.panel, color=rgba,
            marker=marker, linestyle=linestyle,
            linewidth=linewidth, markersize=markersize,
        )
        self._spec = replace(self._spec, series=(*self._spec.series, item))
        return self


class FigureBuilder:
    """A window-free figure description, frozen after successful build()."""

    __slots__ = ("_spec", "_panels", "_session")

    def __init__(self, spec: FigureSpec) -> None:
        self._spec = spec
        self._panels: dict[int, Subplot] = {}
        self._session: PlotSession | None = None

    def _require_mutable(self) -> None:
        if self._session is not None:
            raise RuntimeError("figure is already built; create a new figure to modify it")

    def subplot(
        self, index: int, *, title: str | None = None,
        xlabel: str | None = None, ylabel: str | None = None,
    ) -> Subplot:
        """Get/create a 1-based, row-major subplot and update supplied text.

        Omitted/None text stays unchanged; an empty string clears it.
        Explicitly created empty panels remain visible after build().
        """
        index = _positive_integer(index, "index")
        if index > self._spec.rows * self._spec.cols:
            raise ValueError("index is outside the figure's subplot grid")
        updates = {name: value for name, value in
                   (("title", title), ("xlabel", xlabel), ("ylabel", ylabel))
                   if value is not None}
        if updates or index not in self._panels:
            self._require_mutable()
        updates = {name: _text(value, name) for name, value in updates.items()}
        if index not in self._panels:
            self._panels[index] = Subplot(
                self, PanelSpec(panel=divmod(index - 1, self._spec.cols)),
            )
        panel = self._panels[index]
        if updates:
            panel._spec = replace(panel._spec, **updates)
        return panel

    def build(self) -> PlotSession:
        """Render once without showing; repeated calls return the same session.

        Retain the session while its window is used, and call session.close()
        to release it. A closed session is never reopened by build(). Failed
        construction leaves this description editable and safe to retry.
        """
        if self._session is None:
            spec = replace(self._spec, panels=tuple(
                panel._spec for _, panel in sorted(self._panels.items())
            ))
            self._session = _build_figure(spec)
        return self._session


def figure(
    *, rows: int = 1, cols: int = 1, title: str = "",
    figsize: tuple[float, float] | None = None,
) -> FigureBuilder:
    """Describe an independent figure. This function never opens a window.

    rows/cols are positive integers; figsize is (width, height) in inches.
    Configure subplots and curves, then call build() before displaying/saving.
    """
    rows = _positive_integer(rows, "rows")
    cols = _positive_integer(cols, "cols")
    title = _text(title, "title")
    if figsize is not None:
        try:
            width, height = figsize
        except (TypeError, ValueError) as error:
            raise ValueError("figsize must contain width and height") from error
        figsize = (_positive_size(width, "figsize width"),
                   _positive_size(height, "figsize height"))
    return FigureBuilder(FigureSpec(rows, cols, (), title, figsize))

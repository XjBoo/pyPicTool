"""Explicit figure/subplot/plot descriptions, rendered once by build()."""

from __future__ import annotations

from dataclasses import replace
from collections.abc import Callable, Mapping
from types import MappingProxyType
from math import isfinite
from numbers import Integral, Real

from matplotlib.colors import to_rgba
from matplotlib.typing import ColorType
from numpy.typing import ArrayLike

from .core import PlotSession, _build_figure
from .model import FigureSpec, PanelSpec, SeriesData, TooltipContext, SuptitleStyle
from .style import get_theme


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
        yaxis: str = "left", tooltip: Callable[[TooltipContext], str] | None = None,
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
            colors = get_theme(self._owner._spec.theme).colors
            color = colors[len(self._spec.series) % len(colors)]
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
        if yaxis not in ("left", "right"):
            raise ValueError("yaxis must be left or right")
        if tooltip is not None and not callable(tooltip):
            raise ValueError("tooltip must be callable or None")
        item = SeriesData(
            x, y, label, panel=self._spec.panel, color=rgba,
            marker=marker, linestyle=linestyle,
            linewidth=linewidth, markersize=markersize, yaxis=yaxis, tooltip=tooltip,
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
        right_ylabel: str | None = None,
        y_enum: Mapping[float, str] | None = None,
        right_y_enum: Mapping[float, str] | None = None,
        legend_loc: str | None = None,
        legend_frame_alpha: float | None = None,
    ) -> Subplot:
        """Get/create a 1-based, row-major subplot and update supplied options.

        Omitted/None text stays unchanged; an empty string clears it.
        Explicitly created empty panels remain visible after build().
        legend_loc='best_corner' avoids data using only the four corners.
        legend_frame_alpha (0..1, default .95) affects the frame, not labels.
        """
        index = _positive_integer(index, "index")
        if index > self._spec.rows * self._spec.cols:
            raise ValueError("index is outside the figure's subplot grid")
        updates = {name: value for name, value in
                   (("title", title), ("xlabel", xlabel), ("ylabel", ylabel),
                    ("right_ylabel", right_ylabel), ("legend_loc", legend_loc))
                   if value is not None}
        if (updates or legend_frame_alpha is not None or y_enum is not None
                or right_y_enum is not None or index not in self._panels):
            self._require_mutable()
        updates = {name: _text(value, name) for name, value in updates.items()}
        if legend_loc is not None:
            _legend_location(legend_loc)
        if legend_frame_alpha is not None:
            updates["legend_frame_alpha"] = _legend_alpha(legend_frame_alpha)
        for name, values in (("y_enum", y_enum), ("right_y_enum", right_y_enum)):
            if values is not None:
                updates[name] = _enum_values(values, name)
        if index not in self._panels:
            self._panels[index] = Subplot(
                self, PanelSpec(panel=divmod(index - 1, self._spec.cols)),
            )
        panel = self._panels[index]
        if updates:
            panel._spec = replace(panel._spec, **updates)
        return panel

    def to_spec(self) -> FigureSpec:
        """Return an immutable description snapshot without creating a window."""
        return replace(self._spec, panels=tuple(
            panel._spec for _, panel in sorted(self._panels.items())
        ))

    def build(self) -> PlotSession:
        """Render once without showing; repeated calls return the same session.

        Retain the session while its window is used, and call session.close()
        to release it. A closed session is never reopened by build(). Failed
        construction leaves this description editable and safe to retry.
        """
        if self._session is None:
            self._session = _build_figure(self.to_spec())
        return self._session


def figure(
    *, rows: int = 1, cols: int = 1, title: str = "",
    figsize: tuple[float, float] | None = None,
    theme: str = "default", window_title: str | None = None,
    suptitle_style: SuptitleStyle | None = None,
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
    get_theme(theme)
    if window_title is not None:
        _text(window_title, "window_title")
    style = SuptitleStyle() if suptitle_style is None else suptitle_style
    if not isinstance(style, SuptitleStyle):
        raise ValueError("suptitle_style must be SuptitleStyle")
    _positive_size(style.fontsize, "suptitle fontsize")
    _positive_size(style.linespacing, "suptitle linespacing")
    if style.horizontalalignment not in ("left", "center", "right"):
        raise ValueError("invalid suptitle horizontalalignment")
    from matplotlib.font_manager import FontProperties
    try:
        FontProperties(weight=style.fontweight)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid suptitle fontweight") from error
    return FigureBuilder(FigureSpec(rows, cols, (), title, figsize,
                                   theme, window_title, style))


def _legend_location(value: str) -> None:
    from matplotlib.legend import Legend
    if not isinstance(value, str) or (value != "best_corner" and value not in Legend.codes):
        raise ValueError("legend_loc must be a named Matplotlib legend location")


def _legend_alpha(value):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or not 0 <= value <= 1):
        raise ValueError("legend_frame_alpha must be a finite number between 0 and 1")
    return float(value)


def _enum_values(values: Mapping[float, str], name: str):
    if not isinstance(values, Mapping):
        raise ValueError(f"{name} must map finite numeric values to strings")
    result = {}
    for key, label in values.items():
        if isinstance(key, bool) or not isinstance(key, Real) or not isfinite(key):
            raise ValueError(f"{name} keys must be finite numbers")
        result[float(key)] = _text(label, name)
    return MappingProxyType(dict(sorted(result.items())))


def build_figure(spec: FigureSpec) -> PlotSession:
    """Validate and render a public FigureSpec; every call creates a new session.

    Panel coordinates are zero-based, unlike FigureBuilder.subplot indices.
    Validation finishes before allocating any Matplotlib figure.
    """
    if not isinstance(spec, FigureSpec):
        raise ValueError("spec must be FigureSpec")
    builder = figure(rows=spec.rows, cols=spec.cols, title=spec.title,
                     figsize=spec.figsize, theme=spec.theme,
                     window_title=spec.window_title, suptitle_style=spec.suptitle_style)
    occupied = set()
    try:
        panels = tuple(spec.panels)
    except TypeError as error:
        raise ValueError("panels must contain PanelSpec instances") from error
    for panel in panels:
        if not isinstance(panel, PanelSpec):
            raise ValueError("panels must contain PanelSpec instances")
        pos = panel.panel
        if (not isinstance(pos, tuple) or len(pos) != 2
                or any(isinstance(n, bool) or not isinstance(n, Integral) or n < 0 for n in pos)
                or pos[0] >= spec.rows or pos[1] >= spec.cols):
            raise ValueError("panel must be a zero-based position inside the grid")
        if pos in occupied:
            raise ValueError("duplicate panel position")
        occupied.add(pos)
        for name in ("title", "xlabel", "ylabel"):
            _text(getattr(panel, name), name)
        _legend_location(panel.legend_loc)
        _legend_alpha(panel.legend_frame_alpha)
        subplot = builder.subplot(pos[0] * spec.cols + pos[1] + 1,
            title=panel.title, xlabel=panel.xlabel, ylabel=panel.ylabel,
            right_ylabel=panel.right_ylabel, y_enum=panel.y_enum,
            right_y_enum=panel.right_y_enum, legend_loc=panel.legend_loc,
            legend_frame_alpha=panel.legend_frame_alpha)
        try:
            items = tuple(panel.series)
        except TypeError as error:
            raise ValueError("series must contain SeriesData instances") from error
        for item in items:
            if not isinstance(item, SeriesData) or item.panel != pos:
                raise ValueError("series must be SeriesData with the containing panel position")
            subplot.plot(item.frames, item.values, label=item.label, color=item.color,
                marker=item.marker, linestyle=item.linestyle, linewidth=item.linewidth,
                markersize=item.markersize, yaxis=item.yaxis, tooltip=item.tooltip)
            try:
                line_color = None if item.line_color is None else to_rgba(item.line_color)
            except (TypeError, ValueError) as error:
                raise ValueError("invalid line_color") from error
            if (isinstance(item.line_alpha, bool) or not isinstance(item.line_alpha, Real)
                    or not isfinite(item.line_alpha) or not 0 <= item.line_alpha <= 1):
                raise ValueError("line_alpha must be between 0 and 1")
            normalized = replace(subplot._spec.series[-1],
                                 line_color=line_color, line_alpha=item.line_alpha)
            subplot._spec = replace(subplot._spec,
                                   series=(*subplot._spec.series[:-1], normalized))
    return builder.build()

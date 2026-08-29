"""Matplotlib + mplcursors + QtAgg throwaway candidate.

PROTOTYPE / THROWAWAY.  This is deliberately independent from the production
``interactive_plotting`` package.  The small amount of glue is here to expose
the requested click tooltip, focus toggle, and legend dragging behavior.
"""

from __future__ import annotations

from typing import Any

from .data import Curve, grouped_data


def build_figure(seed: int = 7, *, backend: str = "QtAgg") -> tuple[Any, Any]:
    """Build the candidate figure; ``backend='Agg'`` is for offscreen smoke."""

    import matplotlib

    matplotlib.use(backend, force=True)
    import matplotlib.pyplot as plt
    import mplcursors

    figure, axes_grid = plt.subplots(3, 2, figsize=(12, 10), squeeze=False)
    artists: list[Any] = []
    for panel, curves in grouped_data(seed).items():
        axis = axes_grid[panel]
        for curve in curves:
            (line,) = axis.plot(
                curve.frames,
                curve.values,
                color=curve.color,
                label=curve.label,
                picker=5,
            )
            artists.append(line)
        axis.set_title(f"Interactive Plot {panel[0] * 2 + panel[1] + 1}")
        axis.set_xlabel("Frame")
        axis.set_ylabel("Value")
        legend = axis.legend(loc="upper right")
        legend.set_draggable(True)
        axis.grid(True, linestyle="--", alpha=0.6)

    cursor = mplcursors.cursor(artists, hover=False, multiple=False)

    @cursor.connect("add")
    def _on_add(selection: Any) -> None:
        x_value, y_value = selection.target
        axis = selection.artist.axes
        selection.annotation.set_text(
            f"Frame: {axis.xaxis.get_major_formatter().format_data_short(x_value)}\n"
            f"Value: {axis.yaxis.get_major_formatter().format_data_short(y_value)}"
        )
        selection.annotation.get_bbox_patch().set_facecolor("white")

    # The focus behavior is intentionally a tiny prototype-level callback.
    focused: dict[str, Any] = {"axis": None, "positions": None}

    def toggle_focus(axis: Any) -> None:
        if focused["axis"] is axis:
            for candidate, position in focused["positions"]:
                candidate.set_visible(True)
                candidate.set_position(position)
            focused["axis"] = None
            focused["positions"] = None
            figure.canvas.draw_idle()
            return
        if focused["axis"] is not None:
            toggle_focus(focused["axis"])
        focused["axis"] = axis
        focused["positions"] = [
            (candidate, candidate.get_position().frozen()) for candidate in figure.axes
        ]
        for candidate in figure.axes:
            candidate.set_visible(candidate is axis)
        axis.set_position((0.05, 0.05, 0.9, 0.9))
        figure.canvas.draw_idle()

    def _on_press(event: Any) -> None:
        if event.button == 1 and event.dblclick and event.inaxes is not None:
            toggle_focus(event.inaxes)

    def _on_key(event: Any) -> None:
        if event.key in ("escape", "esc") and focused["axis"] is not None:
            toggle_focus(focused["axis"])

    figure.canvas.mpl_connect("button_press_event", _on_press)
    figure.canvas.mpl_connect("key_press_event", _on_key)
    figure.tight_layout()
    return figure, cursor


def show(seed: int = 7) -> None:
    """Show the QtAgg candidate in a real GUI process."""

    import matplotlib.pyplot as plt

    build_figure(seed, backend="QtAgg")
    plt.show()

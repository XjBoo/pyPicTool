"""silx + PySide6 throwaway candidate.

PROTOTYPE / THROWAWAY.  silx provides one PlotWindow per panel; the Qt grid,
focus handling, and a small click tooltip are deliberately minimal glue.
"""

from __future__ import annotations

from typing import Any

from .data import grouped_data


def _require() -> tuple[Any, Any, Any]:
    try:
        from silx.gui import qt
        from silx.gui.plot import PlotWindow
    except ImportError as error:
        raise RuntimeError(
            "silx demo needs silx, qtawesome, and a Qt binding (PyQt6 or PySide6)"
        ) from error
    return qt, PlotWindow, qt.QApplication


def build_window(seed: int = 7) -> tuple[Any, Any]:
    """Build six silx PlotWindow widgets without entering the Qt event loop."""

    qt, PlotWindow, QApplication = _require()
    app = QApplication.instance() or QApplication([])
    window = qt.QMainWindow()
    window.setWindowTitle("PROTOTYPE — silx + PySide6")
    window.resize(1200, 1000)
    central = qt.QWidget()
    grid = qt.QGridLayout(central)
    plots: list[Any] = []
    for panel, curves in grouped_data(seed).items():
        plot = PlotWindow()
        plot.setGraphTitle(f"Interactive Plot {panel[0] * 2 + panel[1] + 1}")
        for curve in curves:
            plot.addCurve(curve.frames, curve.values, legend=curve.label, color=curve.color)
        plot.getXAxis().setLabel("Frame")
        plot.getYAxis().setLabel("Value")
        grid.addWidget(plot, panel[0], panel[1])
        plots.append(plot)
    window.setCentralWidget(central)
    window._prototype_qapp = app
    window._prototype_plots = plots
    for plot in plots:
        plot.resetZoom()
    app.processEvents()
    return window, plots


def show(seed: int = 7) -> None:
    window, _plots = build_window(seed)
    window.show()
    window._prototype_qapp.exec()

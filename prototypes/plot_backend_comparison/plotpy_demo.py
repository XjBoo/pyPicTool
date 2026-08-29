"""PlotPy + PySide6 throwaway candidate.

PROTOTYPE / THROWAWAY.  PlotPy's CurveDialog is embedded six times in a Qt
grid.  Qt focus and click tooltip behavior are intentionally left as small
prototype glue so the native toolbar/curve interactions remain visible.
"""

from __future__ import annotations

import os
from typing import Any

from .data import grouped_data


def _require() -> tuple[Any, Any, Any]:
    try:
        # guidata persists user preferences at import time.  For an explicit
        # offscreen smoke, redirect that throwaway state to a caller-provided
        # temporary directory; normal GUI runs use the user's standard config.
        config_root = os.environ.get("PLOT_PROTO_CONFIG_DIR")
        if config_root:
            from guidata import userconfig

            userconfig.get_home_dir = lambda: config_root
        from qtpy.QtWidgets import QApplication
        from plotpy.builder import make
        from plotpy.plot import PlotWindow
    except ImportError as error:
        raise RuntimeError(
            "PlotPy demo needs plotpy, guidata, and a Qt binding (PyQt6 or PySide6)"
        ) from error
    return QApplication, make, PlotWindow


def build_window(seed: int = 7) -> tuple[Any, Any]:
    """Build six PlotPy curve dialogs without entering the Qt event loop."""

    QApplication, make, PlotWindow = _require()
    app = QApplication.instance() or QApplication([])
    qt = __import__("qtpy.QtWidgets", fromlist=["QMainWindow", "QWidget", "QGridLayout"])
    window = qt.QMainWindow()
    window.setWindowTitle("PROTOTYPE — PlotPy + PySide6")
    window.resize(1200, 1000)
    central = qt.QWidget()
    grid = qt.QGridLayout(central)
    dialogs: list[Any] = []
    for panel, curves in grouped_data(seed).items():
        dialog = PlotWindow(
            toolbar=True,
            title=f"Interactive Plot {panel[0] * 2 + panel[1] + 1}",
        )
        plot = dialog.get_plot()
        for curve in curves:
            plot.add_item(make.curve(curve.frames, curve.values, curve.label, color=curve.color))
        grid.addWidget(dialog, panel[0], panel[1])
        dialogs.append(dialog)
    window.setCentralWidget(central)
    window._prototype_qapp = app
    window._prototype_dialogs = dialogs
    return window, dialogs


def show(seed: int = 7) -> None:
    window, _dialogs = build_window(seed)
    window.show()
    window._prototype_qapp.exec()

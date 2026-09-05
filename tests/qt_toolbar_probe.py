"""Qt integration probe, run in an isolated offscreen process."""
import io
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backend_bases import MouseEvent, KeyEvent
from interactive_plotting import SeriesData, create_interactive_plot


def main():
    session = create_interactive_plot([
        SeriesData([0, 1, 2], [0, 1, 0], "sample", panel_title="Sample")
    ])
    app = QtWidgets.QApplication.instance()
    canvas = session.figure.canvas
    manager = canvas.manager
    toolbar = manager.toolbar
    button = canvas.findChild(QtWidgets.QToolButton, "plotToolbarToggle")
    assert button is not None
    assert toolbar.isHidden() and not button.isChecked()
    manager.show()
    app.processEvents()
    assert toolbar.isHidden() and button.isVisible()
    assert button.focusPolicy() == QtCore.Qt.FocusPolicy.NoFocus
    canvas.draw()
    axis = session.axes[0]
    x, y = axis.transData.transform((1, 1))
    canvas.callbacks.process("button_press_event", MouseEvent(
        "button_press_event", canvas, x, y, button=1))
    selected = session.controllers[0].active_selection
    assert selected is not None
    limits = (axis.get_xlim(), axis.get_ylim())
    for mode in ("pan", "zoom"):
        button.click()
        app.processEvents()
        assert toolbar.isVisible() and button.isChecked()
        getattr(toolbar, mode)()
        assert toolbar.mode
        button.click()
        app.processEvents()
        assert toolbar.isHidden() and not toolbar.mode
        assert not canvas.widgetlock.locked()
        assert (axis.get_xlim(), axis.get_ylim()) == limits
        assert session.controllers[0].active_selection is selected
    canvas.callbacks.process("key_press_event", KeyEvent(
        "key_press_event", canvas, key="right"))
    assert selected.current_index == 2
    session.toggle_axes_maximized(axis)
    button.click()
    button.click()
    assert session._dispatcher.layout.maximized_axes is axis
    session.restore_layout()
    manager.window.resize(820, 560)
    app.processEvents()
    assert button.x() + button.width() <= canvas.width()
    assert button.y() + button.height() <= canvas.height()
    # Widgets must not become exported plot artists.
    assert all(text.get_text() != "工具栏" for text in session.figure.texts)
    output = io.BytesIO()
    session.figure.savefig(output, format="png")
    assert output.getvalue().startswith(b"\x89PNG")
    session.close()
    session.close()
    app.processEvents()
    assert not plt.get_fignums()
    print("Qt toolbar probe: passed")


if __name__ == "__main__":
    main()

"""Qt integration probe, run in an isolated offscreen process."""
import io
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.qt_compat import QtCore, QtGui, QtWidgets
from matplotlib.backend_bases import MouseEvent, KeyEvent
from interactive_plotting import SeriesData, create_interactive_plot
from interactive_plotting import series_clipboard


def send_qt_key(widget, key, modifiers=QtCore.Qt.KeyboardModifier.NoModifier):
    event = QtGui.QKeyEvent(
        QtCore.QEvent.Type.KeyPress, key, modifiers,
    )
    QtWidgets.QApplication.sendEvent(widget, event)
    QtWidgets.QApplication.instance().processEvents()


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
        assert canvas.hasFocus()
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
    # Shift+click pins a selection that must survive toolbar toggles.
    canvas.callbacks.process("button_press_event", MouseEvent(
        "button_press_event", canvas, *axis.transData.transform((2, 0)),
        button=1, key="shift"))
    controller = session.controllers[0]
    pins_before = tuple(controller.pinned_selections)
    assert pins_before, "shift+click must create a pinned selection"
    # Collapse without ever enabling pan/zoom: the most common direct path.
    button.click()
    app.processEvents()
    assert toolbar.isVisible() and button.isChecked()
    button.click()
    app.processEvents()
    assert toolbar.isHidden() and not toolbar.mode, "toolbar must hide again"
    assert canvas.hasFocus(), "collapse must return focus to the canvas"
    assert not canvas.widgetlock.locked(), "collapse must release the widget lock"
    assert (axis.get_xlim(), axis.get_ylim()) == limits, "view must be preserved"
    assert controller.active_selection is selected, "selection must be preserved"
    assert controller.pinned_selections == pins_before, "pins must be preserved"
    assert all(pin.tooltip.get_visible() for pin in pins_before)
    manager.window.resize(820, 560)
    app.processEvents()
    assert button.x() + button.width() <= canvas.width()
    assert button.y() + button.height() <= canvas.height()
    # Widgets must not become exported plot artists.
    assert all(text.get_text() != "工具栏" for text in session.figure.texts)
    output = io.BytesIO()
    session.figure.savefig(output, format="png")
    assert output.getvalue().startswith(b"\x89PNG")
    selector = canvas.findChild(QtWidgets.QToolButton, "plotSeriesSelector")
    assert selector is not None and not selector.isChecked()
    for navigation in ("pan", "zoom"):
        getattr(toolbar, navigation)()
        assert toolbar.mode
        selector.click()
        app.processEvents()
        assert not toolbar.mode and not canvas.widgetlock.locked()
        assert session.series_selection_mode and canvas.hasFocus()
        selector.click()
        assert not session.series_selection_mode
    selector.click()
    app.processEvents()
    assert session.series_selection_mode and selector.isChecked()
    assert canvas.hasFocus()
    canvas.callbacks.process("button_press_event", MouseEvent(
        "button_press_event", canvas, *axis.transData.transform((.5, .5)), button=1))
    assert session.selected_series is session.series[0]
    canvas.callbacks.process("key_press_event", KeyEvent(
        "key_press_event", canvas, key="delete"))
    assert session.series[0].removed
    assert axis.get_xlim() == (0, 1) and axis.get_ylim() == (0, 1)
    canvas.callbacks.process("key_press_event", KeyEvent(
        "key_press_event", canvas, key="escape"))
    assert not session.series_selection_mode and not selector.isChecked()
    assert selector.x() + selector.width() < button.x()

    series_clipboard.clear()
    source = create_interactive_plot([
        SeriesData([0, 1, 2], [10, 20, 30], "Copied", marker=None),
    ])
    source_manager = source.figure.canvas.manager
    source_manager.show()
    source_canvas = source.figure.canvas
    source_axis = source.axes[0]
    source_selector = source_canvas.findChild(
        QtWidgets.QToolButton, "plotSeriesSelector",
    )
    assert source_selector is not None
    source_selector.click()
    source_canvas.draw()
    source_canvas.callbacks.process("button_press_event", MouseEvent(
        "button_press_event", source_canvas,
        *source_axis.transData.transform((0, 10)), button=1,
    ))
    assert source.selected_series is source.series[0]
    source_manager.window.activateWindow()
    source_canvas.setFocus()
    app.processEvents()
    assert source_canvas.hasFocus()
    system_clipboard = QtWidgets.QApplication.clipboard()
    system_clipboard_before = (
        system_clipboard.text(), system_clipboard.image().cacheKey(),
    )
    send_qt_key(
        source_canvas, QtCore.Qt.Key.Key_C,
        QtCore.Qt.KeyboardModifier.ControlModifier,
    )
    assert series_clipboard.get_series().label == "Copied"
    assert (
        system_clipboard.text(), system_clipboard.image().cacheKey(),
    ) == system_clipboard_before
    assert source.series_selection_mode and source_selector.isChecked()
    assert source.selected_series is source.series[0]

    manager.window.activateWindow()
    canvas.setFocus()
    app.processEvents()
    assert canvas.hasFocus()
    baseline_series = len(session.series)
    canvas.draw()
    panel_x, panel_y = axis.transData.transform((.5, .5))
    canvas.callbacks.process("motion_notify_event", MouseEvent(
        "motion_notify_event", canvas, panel_x, panel_y,
    ))
    assert session._paste_preview_axis is axis
    assert session._paste_preview_outlines[axis].get_visible()
    for name in ("button_press_event", "button_release_event"):
        canvas.callbacks.process(name, MouseEvent(
            name, canvas, panel_x, panel_y, button=1,
        ))
    assert session._paste_target_axis is axis
    assert session._paste_target_outlines[axis].get_visible()
    canvas.setFocus()
    send_qt_key(
        canvas, QtCore.Qt.Key.Key_V,
        QtCore.Qt.KeyboardModifier.ControlModifier,
    )
    assert len(session.series) == baseline_series + 1
    assert session.series[-1].data.label == "Copied"
    send_qt_key(
        canvas, QtCore.Qt.Key.Key_V,
        QtCore.Qt.KeyboardModifier.MetaModifier,
    )
    assert len(session.series) == baseline_series + 2
    assert [text.get_text() for text in axis.get_legend().texts] == [
        "Copied", "Copied",
    ]
    assert session._paste_target_axis is axis
    send_qt_key(canvas, QtCore.Qt.Key.Key_Escape)
    assert session._paste_target_axis is None
    assert not session._paste_target_outlines[axis].get_visible()
    assert series_clipboard.get_series() is not None
    assert not source.series_selection_mode
    assert not source_selector.isChecked()
    assert not series_clipboard.is_active()

    # The target-window Esc exited every mode; re-entering L in that window
    # reactivates the retained snapshot.
    manager.window.activateWindow()
    canvas.setFocus()
    app.processEvents()
    blank_x, blank_y = axis.transData.transform((.1, 29))
    before_disarmed = len(session.series)
    canvas.callbacks.process("motion_notify_event", MouseEvent(
        "motion_notify_event", canvas, blank_x, blank_y,
    ))
    assert session._paste_preview_axis is None
    for name in ("button_press_event", "button_release_event"):
        canvas.callbacks.process(name, MouseEvent(
            name, canvas, blank_x, blank_y, button=1,
        ))
    assert session._paste_target_axis is None
    send_qt_key(
        canvas, QtCore.Qt.Key.Key_V,
        QtCore.Qt.KeyboardModifier.ControlModifier,
    )
    assert len(session.series) == before_disarmed
    send_qt_key(canvas, QtCore.Qt.Key.Key_L)
    assert session.series_selection_mode
    assert series_clipboard.is_active()
    canvas.callbacks.process("motion_notify_event", MouseEvent(
        "motion_notify_event", canvas, blank_x, blank_y,
    ))
    assert session._paste_preview_axis is axis
    for name in ("button_press_event", "button_release_event"):
        canvas.callbacks.process(name, MouseEvent(
            name, canvas, blank_x, blank_y, button=1,
        ))
    assert session._paste_target_axis is axis
    send_qt_key(
        canvas, QtCore.Qt.Key.Key_V,
        QtCore.Qt.KeyboardModifier.ControlModifier,
    )
    assert len(session.series) == before_disarmed + 1

    source.close()
    assert not plt.fignum_exists(source.figure.number)
    assert series_clipboard.get_series().label == "Copied"
    assert series_clipboard.is_active()
    series_clipboard.clear()

    session.disconnect()
    assert not selector.isEnabled()
    session.close()
    session.close()
    app.processEvents()
    assert not plt.get_fignums()
    print("Qt toolbar probe: passed")


if __name__ == "__main__":
    main()

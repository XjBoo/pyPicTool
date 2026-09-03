import unittest
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import CloseEvent, KeyEvent, MouseEvent
from matplotlib.ticker import FuncFormatter


def send_mouse_event(session, name, axis, x_value, y_value, **kwargs):
    session.figure.canvas.draw()
    x_pixel, y_pixel = axis.transData.transform((x_value, y_value))
    event = MouseEvent(name, session.figure.canvas, x_pixel, y_pixel, **kwargs)
    session.figure.canvas.callbacks.process(name, event)


def send_canvas_mouse_event(session, name, x_pixel, y_pixel, **kwargs):
    event = MouseEvent(
        name, session.figure.canvas, x_pixel, y_pixel, **kwargs
    )
    session.figure.canvas.callbacks.process(name, event)


def send_key_event(session, key):
    event = KeyEvent("key_press_event", session.figure.canvas, key=key)
    session.figure.canvas.callbacks.process("key_press_event", event)


def cursor_highlights(axis):
    return {
        line.get_color(): line
        for line in axis.lines
        if line.get_marker() not in (None, "None", "")
    }


def cursor_highlight_lines(axis):
    return [
        line
        for line in axis.lines
        if line.get_marker() not in (None, "None", "")
    ]


def axes_layout_snapshot(session):
    return [
        (
            axis.get_visible(),
            axis.get_in_layout(),
            tuple(axis.get_position(original=True).bounds),
            tuple(axis.get_position().bounds),
        )
        for axis in session.axes
    ]

from interactive_plotting import SeriesData, make_demo_series


class DemoSeriesTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_seeded_demo_series_is_reproducible_without_creating_a_figure(self):
        figures_before = tuple(plt.get_fignums())

        first = make_demo_series(seed=2026)
        second = make_demo_series(seed=2026)

        self.assertEqual(len(first), 12)
        self.assertTrue(all(isinstance(series, SeriesData) for series in first))
        self.assertEqual(
            [series.panel for series in first],
            [
                (row, column)
                for row in range(3)
                for column in range(2)
                for _ in range(2)
            ],
        )
        self.assertTrue(all(series.frames.shape == (100,) for series in first))
        self.assertTrue(all(series.values.shape == (100,) for series in first))
        for actual, expected in zip(first, second):
            np.testing.assert_array_equal(actual.frames, expected.frames)
            np.testing.assert_array_equal(actual.values, expected.values)
        self.assertEqual(tuple(plt.get_fignums()), figures_before)


class InteractivePlotTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_create_returns_session_with_figure_and_controller_without_showing(self):
        from interactive_plotting import PlotSession, create_interactive_plot

        series = [
            SeriesData(
                frames=[0, 1, 2],
                values=[0.0, 1.0, 0.0],
                label="sample",
            )
        ]

        with patch("matplotlib.pyplot.show") as show:
            session = create_interactive_plot(series)

        self.assertIsInstance(session, PlotSession)
        self.assertEqual(len(session.figure.axes), 1)
        self.assertEqual(len(session.controllers), 1)
        show.assert_not_called()

    def test_failed_plot_construction_does_not_leak_a_figure(self):
        from interactive_plotting import create_interactive_plot

        figures_before = tuple(plt.get_fignums())
        invalid_style = SeriesData(
            [0, 1], [0.0, 1.0], "invalid-style", color="not-a-color"
        )

        with self.assertRaises(ValueError):
            create_interactive_plot([invalid_style])

        self.assertEqual(tuple(plt.get_fignums()), figures_before)

    def test_show_demo_builds_six_panels_and_calls_show(self):
        from interactive_plotting import PlotSession, show_demo

        with patch("matplotlib.pyplot.show") as show:
            session = show_demo()

        self.assertIsInstance(session, PlotSession)
        self.assertEqual(len(session.figure.axes), 6)
        self.assertEqual(len(session.controllers), 6)
        np.testing.assert_array_equal(session.figure.get_size_inches(), [12.0, 10.0])
        show.assert_called_once_with()

    def test_axes_can_fill_the_figure_then_restore_or_switch_exactly(self):
        from interactive_plotting import create_interactive_plot, make_demo_series

        session = create_interactive_plot(make_demo_series(seed=7))
        original_layout = axes_layout_snapshot(session)
        first, second = session.axes[:2]

        self.assertTrue(session.toggle_axes_maximized(first))
        self.assertEqual(
            [axis.get_visible() for axis in session.axes],
            [True, False, False, False, False, False],
        )
        maximized_bounds = tuple(first.get_position().bounds)
        self.assertGreater(maximized_bounds[2], 0.8)
        self.assertGreater(maximized_bounds[3], 0.8)
        session.figure.canvas.draw()
        np.testing.assert_allclose(first.get_position().bounds, maximized_bounds)
        self.assertTrue(first.get_title())
        self.assertTrue(first.get_legend().get_visible())
        data_line = first.lines[0]
        frame = data_line.get_xdata()[0]
        value = data_line.get_ydata()[0]
        send_mouse_event(session, "motion_notify_event", first, frame, value)
        marker = next(
            line
            for line in cursor_highlight_lines(first)
            if line.get_markeredgecolor() == "gold"
        )
        self.assertEqual(marker.get_markeredgecolor(), "gold")
        self.assertFalse(any(text.get_visible() for text in first.texts))
        send_mouse_event(
            session, "button_press_event", first, frame, value, button=1
        )
        active_marker = session.controllers[0].active_selection.highlight
        self.assertEqual(active_marker.get_marker(), "o")
        self.assertEqual(active_marker.get_markeredgecolor(), "gold")
        self.assertEqual(
            sum(text.get_visible() for axis in session.axes for text in axis.texts),
            1,
        )

        self.assertFalse(session.toggle_axes_maximized(first))
        self.assertEqual(axes_layout_snapshot(session), original_layout)
        self.assertFalse(session.restore_layout())

        self.assertTrue(session.toggle_axes_maximized(first))
        self.assertTrue(session.toggle_axes_maximized(second))
        self.assertEqual(
            [axis.get_visible() for axis in session.axes],
            [False, True, False, False, False, False],
        )
        self.assertTrue(session.restore_layout())
        self.assertEqual(axes_layout_snapshot(session), original_layout)

    def test_layout_restores_after_external_resize_and_tight_layout_repeatedly(self):
        from interactive_plotting import create_interactive_plot, make_demo_series

        session = create_interactive_plot(make_demo_series(seed=7))
        session.figure.set_size_inches(12.0, 10.0, forward=True)
        session.figure.tight_layout()
        session.figure.canvas.draw()
        initial_layout = axes_layout_snapshot(session)

        for cycle in range(3):
            self.assertTrue(session.toggle_axes_maximized(session.axes[0]))
            session.figure.canvas.draw()
            self.assertFalse(session.toggle_axes_maximized(session.axes[0]))
            session.figure.canvas.draw()

            restored_layout = axes_layout_snapshot(session)
            for axis_index, (initial, restored) in enumerate(
                zip(initial_layout, restored_layout, strict=True)
            ):
                with self.subTest(cycle=cycle, axis=axis_index):
                    self.assertEqual(restored[:2], initial[:2])
                    np.testing.assert_allclose(
                        restored[2], initial[2], rtol=0, atol=1e-12
                    )
                    np.testing.assert_allclose(
                        restored[3], initial[3], rtol=0, atol=1e-12
                    )

    def test_single_axes_layout_restores_after_external_layout_change(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "single", color="red")]
        )
        session.figure.set_size_inches(12.0, 10.0, forward=True)
        session.figure.tight_layout()
        session.figure.canvas.draw()
        initial_layout = axes_layout_snapshot(session)

        for cycle in range(3):
            self.assertTrue(session.toggle_axes_maximized(session.axes[0]))
            session.figure.canvas.draw()
            self.assertFalse(session.toggle_axes_maximized(session.axes[0]))
            session.figure.canvas.draw()

            restored_layout = axes_layout_snapshot(session)
            with self.subTest(cycle=cycle):
                self.assertEqual(restored_layout[0][:2], initial_layout[0][:2])
                np.testing.assert_allclose(
                    restored_layout[0][2],
                    initial_layout[0][2],
                    rtol=0,
                    atol=1e-12,
                )
                np.testing.assert_allclose(
                    restored_layout[0][3],
                    initial_layout[0][3],
                    rtol=0,
                    atol=1e-12,
                )

    def test_double_click_maximizes_without_applying_the_first_single_click(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "left",
                    panel=(0, 0),
                    color="red",
                ),
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "right",
                    panel=(0, 1),
                    color="blue",
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(session, "motion_notify_event", left, 0, 0.0)
        controller = session.controllers[0]
        marker = controller.hover_highlight
        state_before = (
            tuple(marker.get_xdata()),
            tuple(marker.get_ydata()),
            marker.get_visible(),
            marker.get_marker(),
            marker.get_markeredgecolor(),
            len(cursor_highlight_lines(left)),
            len(left.texts),
        )

        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=False
        )
        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=True
        )

        self.assertTrue(left.get_visible())
        self.assertFalse(right.get_visible())
        self.assertEqual(
            (
                tuple(marker.get_xdata()),
                tuple(marker.get_ydata()),
                marker.get_visible(),
                marker.get_marker(),
                marker.get_markeredgecolor(),
                len(cursor_highlight_lines(left)),
                len(left.texts),
            ),
            state_before,
        )
        self.assertIsNone(controller.active_selection)

        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=False
        )
        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=True
        )
        self.assertTrue(right.get_visible())
        self.assertEqual(
            (
                tuple(marker.get_xdata()),
                tuple(marker.get_ydata()),
                marker.get_visible(),
                marker.get_marker(),
                marker.get_markeredgecolor(),
                len(cursor_highlight_lines(left)),
                len(left.texts),
            ),
            state_before,
        )

        send_mouse_event(
            session,
            "button_press_event",
            left,
            1,
            1.0,
            button=1,
            key="shift",
            dblclick=False,
        )
        send_mouse_event(
            session,
            "button_press_event",
            left,
            1,
            1.0,
            button=1,
            key="shift",
            dblclick=True,
        )
        self.assertFalse(right.get_visible())
        self.assertEqual(len(cursor_highlight_lines(left)), 1)
        session.restore_layout()

        send_mouse_event(session, "button_press_event", left, 1, 1.0, button=1)
        active = controller.active_selection
        self.assertEqual(active.highlight.get_xdata()[0], 1)
        self.assertEqual(active.highlight.get_marker(), "o")

    def test_double_click_restores_an_initially_hidden_cursor(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "left",
                    panel=(0, 0),
                    color="red",
                ),
                SeriesData(
                    [0, 1, 2],
                    [10.0, 11.0, 12.0],
                    "right",
                    panel=(0, 1),
                    color="blue",
                ),
            ]
        )
        left = session.axes[0]
        controller = session.controllers[0]
        marker = controller.hover_highlight
        self.assertFalse(marker.get_visible())
        self.assertIsNone(controller.active_selection)

        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=False
        )
        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=True
        )

        self.assertFalse(marker.get_visible())
        self.assertEqual(marker.get_xdata()[0], 0)
        self.assertEqual(marker.get_ydata()[0], 0.0)
        self.assertEqual(marker.get_marker(), "o")
        self.assertIsNone(controller.active_selection)
        self.assertEqual(len(left.texts), 0)

    def test_double_click_restores_the_previous_figure_tooltip(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [10.0, 11.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(
            session, "button_press_event", right, 0, 10.0, button=1
        )
        self.assertTrue(right.texts[0].get_visible())

        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, dblclick=False
        )
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, dblclick=True
        )
        session.restore_layout()

        visible_tooltips = [
            tooltip
            for axis in session.axes
            for tooltip in axis.texts
            if tooltip.get_visible()
        ]
        self.assertEqual(visible_tooltips, [right.texts[0]])

    def test_double_click_restores_active_series_identity_and_visuals(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "red", color="red"),
                SeriesData(
                    [0, 1, 2], [10.0, 11.0, 12.0], "blue", color="blue"
                ),
            ]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 1, 1.0, button=1)
        active = controller.active_selection

        send_mouse_event(
            session,
            "button_press_event",
            axis,
            1,
            11.0,
            button=1,
            dblclick=False,
        )
        send_mouse_event(
            session,
            "button_press_event",
            axis,
            1,
            11.0,
            button=1,
            dblclick=True,
        )

        self.assertIs(controller.active_selection, active)
        self.assertEqual(active.series_idx, 0)
        self.assertEqual(active.color, "red")
        self.assertEqual(active.highlight.get_color(), "red")
        self.assertEqual(active.highlight.get_xdata()[0], 1)
        self.assertEqual(active.highlight.get_ydata()[0], 1.0)
        self.assertEqual(active.tooltip.xy, (1, 1.0))
        self.assertIn("Value: 1", active.tooltip.get_text())

    def test_double_click_restores_hover_focus_on_a_pinned_point(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        active = controller.active_selection
        send_mouse_event(
            session,
            "button_press_event",
            axis,
            1,
            1.0,
            button=1,
            key="shift",
        )
        pinned = controller.pinned_selections[0]

        session.figure.canvas.draw()
        bbox = active.tooltip.get_window_extent(session.figure.canvas.get_renderer())
        send_canvas_mouse_event(
            session,
            "button_press_event",
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )
        send_canvas_mouse_event(
            session,
            "button_release_event",
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )
        send_mouse_event(session, "motion_notify_event", axis, 1, 1.0)
        self.assertEqual(pinned.highlight.get_markeredgecolor(), "gold")

        send_mouse_event(
            session,
            "button_press_event",
            axis,
            1,
            1.0,
            button=1,
            dblclick=False,
        )
        send_mouse_event(
            session,
            "button_press_event",
            axis,
            1,
            1.0,
            button=1,
            dblclick=True,
        )

        self.assertEqual(controller.pinned_selections, (pinned,))
        self.assertFalse(controller.hover_highlight.get_visible())
        self.assertEqual(pinned.highlight.get_markersize(), 10)
        self.assertEqual(pinned.highlight.get_markeredgecolor(), "gold")

    def test_double_click_preserves_the_selected_controller_for_keyboard_input(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "left",
                    panel=(0, 0),
                    color="red",
                ),
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "right",
                    panel=(0, 1),
                    color="blue",
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(session, "motion_notify_event", right, 0, 0.0)
        right_marker = cursor_highlights(right)["blue"]
        self.assertEqual(right_marker.get_markeredgecolor(), "gold")
        # Clicking anchors right's cursor for the keyboard before maximizing.
        send_mouse_event(
            session, "button_press_event", right, 0, 0.0, button=1
        )
        right_marker = session.controllers[1].active_selection.highlight

        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=False
        )
        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1, dblclick=True
        )
        send_key_event(session, "right")

        self.assertEqual(right_marker.get_xdata()[0], 1)
        self.assertEqual(right_marker.get_markeredgecolor(), "gold")

    def test_escape_restores_layout_before_clearing_extra_cursors(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [0.0, 1.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, key="shift"
        )
        self.assertEqual(len(cursor_highlight_lines(left)), 2)
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, dblclick=False
        )
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, dblclick=True
        )
        self.assertFalse(right.get_visible())

        send_key_event(session, "escape")

        self.assertTrue(right.get_visible())
        self.assertEqual(len(cursor_highlight_lines(left)), 2)

        send_key_event(session, "escape")
        self.assertEqual(len(cursor_highlight_lines(left)), 1)

    def test_legend_drag_and_interactive_artists_take_priority_over_maximize(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [0.0, 1.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        canvas = session.figure.canvas
        canvas.draw()
        legend = left.get_legend()
        self.assertTrue(legend.get_draggable())

        legend_box = legend.get_window_extent(canvas.get_renderer())
        center_x = legend_box.x0 + legend_box.width / 2
        center_y = legend_box.y0 + legend_box.height / 2
        send_canvas_mouse_event(
            session, "button_press_event", center_x, center_y, button=1
        )
        send_canvas_mouse_event(
            session, "motion_notify_event", center_x + 35, center_y - 20, button=1
        )
        send_canvas_mouse_event(
            session, "button_release_event", center_x + 35, center_y - 20, button=1
        )
        canvas.draw()
        dragged_bounds = tuple(legend.get_window_extent(canvas.get_renderer()).bounds)
        self.assertNotEqual(dragged_bounds, tuple(legend_box.bounds))

        session.toggle_axes_maximized(left)
        canvas.draw()
        session.restore_layout()
        canvas.draw()
        np.testing.assert_allclose(
            legend.get_window_extent(canvas.get_renderer()).bounds,
            dragged_bounds,
        )

        legend_box = legend.get_window_extent(canvas.get_renderer())
        center_x = legend_box.x0 + legend_box.width / 2
        center_y = legend_box.y0 + legend_box.height / 2
        for double in (False, True):
            send_canvas_mouse_event(
                session,
                "button_press_event",
                center_x,
                center_y,
                button=1,
                dblclick=double,
            )
            send_canvas_mouse_event(
                session, "button_release_event", center_x, center_y, button=1
            )
        self.assertTrue(right.get_visible())

        send_mouse_event(session, "motion_notify_event", left, 0, 0.0)
        send_mouse_event(session, "button_press_event", left, 0, 0.0, button=1)
        canvas.draw()
        tooltip = left.texts[0]
        tooltip_box = tooltip.get_window_extent(canvas.get_renderer())
        tooltip_x = tooltip_box.x0 + tooltip_box.width / 2
        tooltip_y = tooltip_box.y0 + tooltip_box.height / 2
        for double in (False, True):
            send_canvas_mouse_event(
                session,
                "button_press_event",
                tooltip_x,
                tooltip_y,
                button=1,
                dblclick=double,
            )
            send_canvas_mouse_event(
                session, "button_release_event", tooltip_x, tooltip_y, button=1
            )
        self.assertTrue(right.get_visible())

        manager = session.figure.canvas.manager
        with patch.object(manager, "toolbar", SimpleNamespace(mode="pan/zoom")):
            send_mouse_event(
                session,
                "button_press_event",
                left,
                0,
                0.0,
                button=1,
                dblclick=False,
            )
            send_mouse_event(
                session,
                "button_press_event",
                left,
                0,
                0.0,
                button=1,
                dblclick=True,
            )
        self.assertTrue(right.get_visible())

    def test_series_validation_and_missing_values_are_publicly_enforced(self):
        from interactive_plotting import create_interactive_plot

        invalid_cases = [
            ("empty", [], []),
            ("not-1d", [[0, 1]], [[1, 2]]),
            ("length", [0, 1], [1]),
            ("frames-finite", [0, np.inf], [1, 2]),
            ("numeric", ["a", "b"], [1, 2]),
            ("values-numeric", [0, 1], ["a", "b"]),
            ("no-valid-values", [0, 1], [np.nan, np.inf]),
        ]
        for label, frames, values in invalid_cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, label):
                    SeriesData(frames=frames, values=values, label=label)
        for panel in (None, 1, (0,), ("0", 0), (-1, 0)):
            with self.subTest(panel=panel):
                with self.assertRaisesRegex(ValueError, "invalid-panel"):
                    SeriesData([0], [1.0], "invalid-panel", panel=panel)
        with self.assertRaisesRegex(ValueError, "at least one series"):
            create_interactive_plot([])

        caller_frames = np.array([0, 1, 2, 3])
        caller_values = np.array([1.0, np.nan, np.inf, 4.0])
        series = SeriesData(
            frames=caller_frames,
            values=caller_values,
            label="gaps",
        )
        caller_frames[0] = 99
        caller_values[0] = 99
        self.assertEqual(series.frames[0], 0)
        self.assertEqual(series.values[0], 1.0)
        self.assertFalse(series.frames.flags.writeable)
        self.assertFalse(series.values.flags.writeable)
        session = create_interactive_plot([series])
        data_line = session.axes[0].lines[0]
        scatter = session.axes[0].collections[0]

        np.testing.assert_array_equal(
            np.isnan(data_line.get_ydata()), [False, True, True, False]
        )
        self.assertEqual(len(scatter.get_offsets()), 2)
        send_mouse_event(session, "motion_notify_event", session.axes[0], 3, 4.0)
        self.assertEqual(
            cursor_highlight_lines(session.axes[0])[0].get_xdata()[0], 3
        )

    def test_hover_highlights_only_the_nearest_hit_series(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 14], [0.0, 1.0], "red", color="red"),
                SeriesData([0, 4, 10, 18], [2.0, 3.0, 4.0, 5.0], "blue", color="blue"),
                SeriesData([18, 10], [6.0, 7.0], "green", color="green"),
            ]
        )
        figure = session.figure
        axis = session.axes[0]
        figure.canvas.draw()
        x_pixel, y_pixel = axis.transData.transform((14, 1.0))
        event = MouseEvent("motion_notify_event", figure.canvas, x_pixel, y_pixel)
        marker = session.controllers[0].hover_highlight

        figure.canvas.callbacks.process("motion_notify_event", event)

        self.assertEqual(marker.get_xdata()[0], 14)
        self.assertEqual(marker.get_color(), "red")
        self.assertTrue(marker.get_visible())

    def test_hover_requires_a_hit_within_the_shared_radius(self):
        from interactive_plotting import create_interactive_plot

        for interaction in ("hover", "click"):
            for offset, should_hit in ((5.9, True), (6.0, True), (6.1, False)):
                with self.subTest(
                    interaction=interaction, offset=offset, should_hit=should_hit
                ):
                    session = create_interactive_plot(
                        [
                            SeriesData(
                                [0, 1, 2],
                                [0.0, 1.0, 2.0],
                                "sample",
                                color="red",
                            )
                        ]
                    )
                    axis = session.axes[0]
                    controller = session.controllers[0]
                    marker = controller.hover_highlight
                    session.figure.canvas.draw()
                    x_pixel, y_pixel = axis.transData.transform((1, 1.0))
                    event_name = (
                        "motion_notify_event"
                        if interaction == "hover"
                        else "button_press_event"
                    )
                    event = MouseEvent(
                        event_name,
                        session.figure.canvas,
                        x_pixel,
                        y_pixel,
                        button=1 if interaction == "click" else None,
                    )
                    event.x = x_pixel + offset
                    event.y = y_pixel
                    event.inaxes = axis

                    result = (
                        controller.on_hover(event)
                        if interaction == "hover"
                        else controller.on_click(event)
                    )

                    if interaction == "click":
                        self.assertEqual(result is not None, should_hit)
                        self.assertEqual(
                            controller.active_selection is not None, should_hit
                        )
                        if should_hit:
                            active = controller.active_selection
                            self.assertEqual(active.highlight.get_xdata()[0], 1)
                            self.assertTrue(active.tooltip.get_visible())
                    else:
                        self.assertEqual(marker.get_visible(), should_hit)
                        self.assertEqual(marker.get_xdata()[0], 1 if should_hit else 0)
                    session.close()

    def test_overlapping_hits_highlight_only_the_closest_series(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 10], [0.0, 10.0], "red", color="red"),
                SeriesData([0, 10], [0.1, 10.1], "blue", color="blue"),
            ]
        )
        axis = session.axes[0]
        session.figure.canvas.draw()

        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        marker = session.controllers[0].hover_highlight
        self.assertTrue(marker.get_visible())
        self.assertEqual(marker.get_color(), "red")

        send_mouse_event(session, "motion_notify_event", axis, 0, 0.1)
        self.assertTrue(marker.get_visible())
        self.assertEqual(marker.get_color(), "blue")

    def test_hover_is_transient_while_active_selection_persists(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        marker = controller.hover_highlight
        session.figure.canvas.draw()
        self.assertFalse(marker.get_visible())

        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        self.assertTrue(marker.get_visible())

        send_mouse_event(session, "motion_notify_event", axis, 1.5, 1.5)
        self.assertFalse(marker.get_visible())

        send_mouse_event(session, "motion_notify_event", axis, 1, 1.0)
        send_mouse_event(session, "button_press_event", axis, 1, 1.0, button=1)
        active = controller.active_selection.highlight
        self.assertFalse(marker.get_visible())
        self.assertTrue(active.get_visible())

        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        self.assertTrue(marker.get_visible())
        self.assertEqual(marker.get_xdata()[0], 0)
        self.assertTrue(active.get_visible())
        self.assertEqual(active.get_xdata()[0], 1)

    def test_pinned_selection_persists_during_same_and_cross_series_hover(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 1], [0.0, 1.0], "red", color="red"),
                SeriesData([0, 1], [10.0, 11.0], "blue", color="blue"),
            ]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(
            session,
            "button_press_event",
            axis,
            1,
            1.0,
            button=1,
            key="shift",
        )
        pinned = controller.pinned_selections[0]
        pinned_position = tuple(pinned.tooltip.xy)

        for x_value, y_value, color in ((0, 0.0, "red"), (0, 10.0, "blue")):
            with self.subTest(color=color):
                send_mouse_event(
                    session, "motion_notify_event", axis, x_value, y_value
                )
                self.assertTrue(controller.hover_highlight.get_visible())
                self.assertEqual(controller.hover_highlight.get_color(), color)
                self.assertEqual(pinned.current_index, 1)
                self.assertEqual(tuple(pinned.tooltip.xy), pinned_position)
                self.assertTrue(pinned.highlight.get_visible())
                self.assertTrue(pinned.tooltip.get_visible())

    def test_motion_away_from_a_panel_hides_only_its_transient_marker(self):
        from interactive_plotting import create_interactive_plot

        for destination in ("other-panel", "outside-axes"):
            for selected in (False, True):
                with self.subTest(destination=destination, selected=selected):
                    session = create_interactive_plot(
                        [
                            SeriesData(
                                [0, 1],
                                [0.0, 1.0],
                                "left",
                                panel=(0, 0),
                                color="red",
                            ),
                            SeriesData(
                                [0, 1],
                                [10.0, 11.0],
                                "right",
                                panel=(0, 1),
                                color="blue",
                            ),
                        ]
                    )
                    left, right = session.axes
                    left_controller, right_controller = session.controllers
                    markers = {
                        "left": left_controller.hover_highlight,
                        "right": right_controller.hover_highlight,
                    }
                    send_mouse_event(
                        session, "motion_notify_event", left, 0, 0.0
                    )
                    if selected:
                        send_mouse_event(
                            session,
                            "button_press_event",
                            left,
                            0,
                            0.0,
                            button=1,
                        )

                    if destination == "other-panel":
                        send_mouse_event(
                            session, "motion_notify_event", right, 0, 10.0
                        )
                    else:
                        session.figure.canvas.draw()
                        send_canvas_mouse_event(
                            session, "motion_notify_event", 0, 0
                        )

                    self.assertFalse(markers["left"].get_visible())
                    self.assertEqual(markers["left"].get_xdata()[0], 0)
                    self.assertEqual(
                        left_controller.active_selection is not None, selected
                    )
                    if selected:
                        self.assertTrue(
                            left_controller.active_selection.highlight.get_visible()
                        )
                    self.assertEqual(
                        markers["right"].get_visible(),
                        destination == "other-panel",
                    )
                    session.close()

    def test_hover_keeps_tooltips_hidden_and_click_shows_only_the_hit_point(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 1], [0.0, 1.0], "low", color="red"),
                SeriesData([0, 1], [10.0, 11.0], "high", color="blue"),
            ]
        )
        axis = session.axes[0]
        session.figure.canvas.draw()
        self.assertFalse(any(tooltip.get_visible() for tooltip in axis.texts))

        send_mouse_event(session, "motion_notify_event", axis, 1, 1.0)
        self.assertFalse(any(tooltip.get_visible() for tooltip in axis.texts))

        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1
        )
        visible_tooltips = [
            tooltip for tooltip in axis.texts if tooltip.get_visible()
        ]
        self.assertEqual(len(visible_tooltips), 1)
        self.assertEqual(visible_tooltips[0].xy, (1, 1.0))
        self.assertEqual(
            visible_tooltips[0].get_bbox_patch().get_facecolor()[:3],
            (1.0, 1.0, 1.0),
        )

    def test_each_click_replaces_the_only_visible_tooltip_in_the_figure(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left-low", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1],
                    [10.0, 11.0],
                    "left-high",
                    panel=(0, 0),
                    color="blue",
                ),
                SeriesData(
                    [0, 1],
                    [20.0, 21.0],
                    "right",
                    panel=(0, 1),
                    color="green",
                ),
            ]
        )
        left, right = session.axes

        def visible_tooltips():
            return [
                tooltip
                for axis in session.axes
                for tooltip in axis.texts
                if tooltip.get_visible()
            ]

        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1
        )
        first = visible_tooltips()
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].xy, (0, 0.0))

        send_mouse_event(
            session, "button_press_event", left, 0, 10.0, button=1
        )
        second = visible_tooltips()
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0].xy, (0, 10.0))

        send_mouse_event(
            session, "button_press_event", right, 0, 20.0, button=1
        )
        third = visible_tooltips()
        self.assertEqual(len(third), 1)
        self.assertIsNot(third[0], second[0])
        self.assertEqual(third[0].xy, (0, 20.0))

    def test_shift_click_pins_multiple_tooltips_and_ordinary_click_preserves_them(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 0.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [10.0, 10.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        left_controller, right_controller = session.controllers

        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, key="shift"
        )
        send_mouse_event(
            session, "button_press_event", left, 1, 0.0, button=1, key="shift"
        )
        send_mouse_event(
            session, "button_press_event", right, 0, 10.0, button=1, key="shift"
        )

        self.assertEqual(len(left_controller.pinned_selections), 2)
        self.assertEqual(len(right_controller.pinned_selections), 1)
        self.assertEqual(
            sum(text.get_visible() for axis in session.axes for text in axis.texts),
            3,
        )
        self.assertTrue(
            all(
                cursor.highlight.get_marker() == "o"
                for controller in session.controllers
                for cursor in controller.pinned_selections
            )
        )

        send_mouse_event(session, "button_press_event", right, 1, 10.0, button=1)

        self.assertIsNotNone(right_controller.active_selection)
        self.assertEqual(
            sum(text.get_visible() for axis in session.axes for text in axis.texts),
            4,
        )
        self.assertTrue(
            all(
                cursor.tooltip.get_visible()
                for controller in session.controllers
                for cursor in controller.pinned_selections
            )
        )

    def test_deleting_selected_pin_keeps_active_and_other_pins(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 0.0, 0.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        active = controller.active_selection
        send_mouse_event(
            session, "button_press_event", axis, 1, 0.0, button=1, key="shift"
        )
        first_pin = controller.pinned_selections[0]
        send_mouse_event(
            session, "button_press_event", axis, 2, 0.0, button=1, key="shift"
        )
        second_pin = controller.pinned_selections[1]

        send_key_event(session, "delete")

        self.assertIs(controller.active_selection, active)
        self.assertEqual(controller.pinned_selections, (first_pin,))
        self.assertTrue(active.highlight.get_visible())
        self.assertTrue(active.tooltip.get_visible())
        self.assertIsNone(controller.keyboard_target)
        self.assertEqual(active.highlight.get_markersize(), 8)
        self.assertEqual(active.highlight.get_markeredgecolor(), "red")
        self.assertTrue(first_pin.highlight.get_visible())
        self.assertTrue(first_pin.tooltip.get_visible())
        self.assertNotIn(second_pin.highlight, axis.lines)
        self.assertNotIn(second_pin.tooltip, axis.texts)

    def test_clicking_active_point_again_cancels_it_and_clears_keyboard_target(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 0.0, 0.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(
            session, "button_press_event", axis, 2, 0.0, button=1, key="shift"
        )
        pinned = controller.pinned_selections[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        active = controller.active_selection

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)

        self.assertIsNone(controller.active_selection)
        self.assertIsNone(controller.keyboard_target)
        self.assertFalse(active.highlight.get_visible())
        self.assertFalse(active.tooltip.get_visible())
        self.assertEqual(controller.pinned_selections, (pinned,))
        self.assertTrue(pinned.highlight.get_visible())
        self.assertTrue(pinned.tooltip.get_visible())

        send_key_event(session, "right")
        self.assertEqual(pinned.highlight.get_xdata()[0], 2)

    def test_clicking_pinned_point_removes_only_that_pin(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 0.0, 0.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        active = controller.active_selection
        send_mouse_event(
            session, "button_press_event", axis, 1, 0.0, button=1, key="shift"
        )
        removed_pin = controller.pinned_selections[0]
        send_mouse_event(
            session, "button_press_event", axis, 2, 0.0, button=1, key="shift"
        )
        retained_pin = controller.pinned_selections[1]

        send_mouse_event(session, "button_press_event", axis, 1, 0.0, button=1)

        self.assertIs(controller.active_selection, active)
        self.assertEqual(controller.pinned_selections, (retained_pin,))
        self.assertNotIn(removed_pin.highlight, axis.lines)
        self.assertNotIn(removed_pin.tooltip, axis.texts)
        self.assertTrue(active.highlight.get_visible())
        self.assertTrue(active.tooltip.get_visible())
        self.assertTrue(retained_pin.highlight.get_visible())
        self.assertTrue(retained_pin.tooltip.get_visible())

    def test_clicking_same_active_and_pinned_point_removes_pin_first(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 0.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        active = controller.active_selection
        send_mouse_event(
            session, "button_press_event", axis, 0, 0.0, button=1, key="shift"
        )

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)

        self.assertEqual(controller.pinned_selections, ())
        self.assertIs(controller.active_selection, active)
        self.assertTrue(active.highlight.get_visible())
        self.assertTrue(active.tooltip.get_visible())
        self.assertIsNone(controller.keyboard_target)
        self.assertEqual(active.highlight.get_markersize(), 8)
        self.assertEqual(active.highlight.get_markeredgecolor(), "red")

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        self.assertIsNone(controller.active_selection)
        self.assertIsNone(controller.keyboard_target)

    def test_hovering_a_selected_point_does_not_show_a_duplicate_preview(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)

        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)

        self.assertFalse(controller.hover_highlight.get_visible())
        self.assertTrue(controller.active_selection.highlight.get_visible())
        self.assertEqual(controller.active_selection.highlight.get_marker(), "o")

    def test_clicking_empty_axes_space_does_not_select_or_show_a_tooltip(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 10], [0.0, 10.0], "sample", color="red")]
        )
        axis = session.axes[0]
        marker = cursor_highlights(axis)["red"]
        initial_state = (
            tuple(marker.get_xdata()),
            tuple(marker.get_ydata()),
            marker.get_marker(),
            marker.get_markeredgecolor(),
        )

        send_mouse_event(
            session, "button_press_event", axis, 5, 10.0, button=1
        )

        self.assertFalse(any(tooltip.get_visible() for tooltip in axis.texts))
        self.assertEqual(
            (
                tuple(marker.get_xdata()),
                tuple(marker.get_ydata()),
                marker.get_marker(),
                marker.get_markeredgecolor(),
            ),
            initial_state,
        )

    def test_unsigned_frame_distance_does_not_overflow(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    np.array([5], dtype=np.uint64), [1.0], "target", color="red"
                ),
                SeriesData(
                    np.array([0, 10], dtype=np.uint64),
                    [2.0, 3.0],
                    "candidate",
                    color="blue",
                ),
            ]
        )
        axis = session.axes[0]

        with np.errstate(over="raise"):
            send_mouse_event(session, "motion_notify_event", axis, 5, 1.0)

        marker = session.controllers[0].hover_highlight
        self.assertTrue(marker.get_visible())
        self.assertEqual(marker.get_color(), "red")
        self.assertEqual(marker.get_xdata()[0], 5)

    def test_duplicate_frames_preserve_the_explicit_selected_point(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 0, 1], [0.0, 10.0, 20.0], "duplicates", color="red")]
        )
        axis = session.axes[0]

        send_mouse_event(session, "motion_notify_event", axis, 0, 10.0)
        preview = session.controllers[0].hover_highlight
        self.assertEqual(preview.get_ydata()[0], 10.0)
        send_mouse_event(session, "button_press_event", axis, 0, 10.0, button=1)
        selected = session.controllers[0].active_selection.highlight

        send_key_event(session, "right")
        self.assertEqual(selected.get_xdata()[0], 1)
        self.assertEqual(selected.get_ydata()[0], 20.0)

    def test_ordinary_click_replaces_active_and_hover_remains_independent(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "red", color="red"),
                SeriesData(
                    [0, 1, 2], [10.0, 11.0, 12.0], "blue", color="blue"
                ),
            ]
        )
        axis = session.axes[0]

        send_mouse_event(session, "button_press_event", axis, 0, 10.0, button=1)
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        controller = session.controllers[0]
        active = controller.active_selection.highlight
        self.assertEqual(active.get_color(), "red")
        self.assertEqual(active.get_marker(), "o")
        self.assertEqual(sum(text.get_visible() for text in axis.texts), 1)

        send_mouse_event(session, "button_press_event", axis, 1, 1.0, button=1)
        self.assertEqual(active.get_xdata()[0], 1)
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        self.assertEqual(active.get_xdata()[0], 1)
        self.assertEqual(controller.hover_highlight.get_xdata()[0], 0)
        self.assertTrue(controller.hover_highlight.get_visible())

    def test_keyboard_moves_only_the_most_recent_clicked_selection(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 14], [0.0, 1.0], "red", color="red"),
                SeriesData([0, 4, 10], [2.0, 3.0, 4.0], "blue", color="blue"),
            ]
        )
        axis = session.axes[0]
        send_mouse_event(
            session, "button_press_event", axis, 0, 2.0, button=1, key="shift"
        )
        controller = session.controllers[0]
        blue_pin = controller.pinned_selections[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        red_active = controller.active_selection

        send_key_event(session, "end")
        self.assertEqual(red_active.highlight.get_xdata()[0], 14)
        self.assertEqual(blue_pin.highlight.get_xdata()[0], 0)

        # Clicking the pinned tooltip makes it the new keyboard target.
        session.figure.canvas.draw()
        bbox = blue_pin.tooltip.get_window_extent(session.figure.canvas.get_renderer())
        send_canvas_mouse_event(
            session,
            "button_press_event",
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )
        send_canvas_mouse_event(
            session,
            "button_release_event",
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )
        send_key_event(session, "right")
        self.assertEqual(blue_pin.highlight.get_xdata()[0], 4)
        self.assertEqual(red_active.highlight.get_xdata()[0], 14)

    def test_active_selection_persists_and_keyboard_moves_it(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        marker = session.controllers[0].active_selection.highlight
        self.assertTrue(marker.get_visible())

        send_mouse_event(session, "motion_notify_event", axis, 1.5, 1.5)
        self.assertTrue(marker.get_visible())

        send_key_event(session, "right")

        self.assertEqual(marker.get_xdata()[0], 1)
        self.assertTrue(marker.get_visible())

    def test_keyboard_move_into_hovered_point_uses_one_highlight(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        controller = session.controllers[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        send_mouse_event(session, "motion_notify_event", axis, 1, 1.0)
        self.assertTrue(controller.hover_highlight.get_visible())

        send_key_event(session, "right")

        active = controller.active_selection
        self.assertEqual(active.current_index, 1)
        self.assertFalse(controller.hover_highlight.get_visible())
        self.assertEqual(active.highlight.get_markersize(), 10)
        self.assertEqual(active.highlight.get_markeredgecolor(), "gold")

    def test_keyboard_requires_a_click_selected_cursor(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        preview = session.controllers[0].hover_highlight
        self.assertEqual(preview.get_xdata()[0], 0)

        send_key_event(session, "right")
        self.assertEqual(preview.get_xdata()[0], 0)
        self.assertFalse(any(text.get_visible() for text in axis.texts))

        # Hovering selects the cursor but never anchors it for the keyboard.
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        send_key_event(session, "right")
        self.assertEqual(preview.get_xdata()[0], 0)
        self.assertFalse(any(text.get_visible() for text in axis.texts))

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        send_key_event(session, "right")
        marker = session.controllers[0].active_selection.highlight
        self.assertEqual(marker.get_xdata()[0], 1)
        tooltip = next(text for text in axis.texts if text.get_visible())
        self.assertEqual(tooltip.xy, (1, 1.0))

    def test_keyboard_keeps_targeting_the_clicked_cursor_while_hovering(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 14], [0.0, 1.0], "red", color="red"),
                SeriesData([0, 7, 14], [10.0, 11.0, 12.0], "blue", color="blue"),
            ]
        )
        axis = session.axes[0]
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)

        # Hovering the other series moves the selection, not the keyboard target.
        send_mouse_event(session, "motion_notify_event", axis, 0, 10.0)
        self.assertEqual(cursor_highlights(axis)["blue"].get_markeredgecolor(), "gold")

        send_key_event(session, "end")
        highlights = cursor_highlights(axis)
        self.assertEqual(highlights["red"].get_xdata()[0], 14)
        self.assertEqual(highlights["blue"].get_xdata()[0], 0)

    def test_keyboard_target_is_figure_wide_across_hovered_panels(self):
        from interactive_plotting import create_interactive_plot

        for right_has_older_click in (False, True):
            with self.subTest(right_has_older_click=right_has_older_click):
                session = create_interactive_plot(
                    [
                        SeriesData(
                            [0, 1, 2],
                            [0.0, 1.0, 2.0],
                            "left",
                            panel=(0, 0),
                            color="red",
                        ),
                        SeriesData(
                            [0, 1, 2],
                            [10.0, 11.0, 12.0],
                            "right",
                            panel=(0, 1),
                            color="blue",
                        ),
                    ]
                )
                left, right = session.axes
                if right_has_older_click:
                    send_mouse_event(
                        session,
                        "button_press_event",
                        right,
                        0,
                        10.0,
                        button=1,
                    )
                send_mouse_event(
                    session, "button_press_event", left, 0, 0.0, button=1
                )

                send_mouse_event(session, "motion_notify_event", right, 0, 10.0)
                send_key_event(session, "right")

                self.assertEqual(cursor_highlights(left)["red"].get_xdata()[0], 1)
                self.assertEqual(cursor_highlights(right)["blue"].get_xdata()[0], 0)
                session.close()

    def test_shift_click_replaces_an_older_panel_keyboard_target(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "left",
                    panel=(0, 0),
                    color="red",
                ),
                SeriesData(
                    [0, 1, 2],
                    [10.0, 11.0, 12.0],
                    "right",
                    panel=(0, 1),
                    color="blue",
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(session, "button_press_event", right, 1, 11.0, button=1)
        send_mouse_event(
            session,
            "button_press_event",
            left,
            1,
            1.0,
            button=1,
            key="shift",
        )
        left_markers = cursor_highlight_lines(left)
        default, extra = left_markers
        self.assertEqual(extra.get_xdata()[0], 1)

        send_key_event(session, "left")

        self.assertEqual(default.get_xdata()[0], 0)
        self.assertEqual(extra.get_xdata()[0], 0)
        self.assertEqual(cursor_highlights(right)["blue"].get_xdata()[0], 1)

    def test_cross_panel_click_keeps_one_keyboard_target_and_visual_focus(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [10.0, 11.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        left_controller, right_controller = session.controllers
        send_mouse_event(session, "button_press_event", left, 0, 0.0, button=1)
        left_active = left_controller.active_selection
        send_mouse_event(
            session,
            "button_press_event",
            right,
            0,
            10.0,
            button=1,
            key="shift",
        )
        right_pin = right_controller.pinned_selections[0]

        self.assertIsNone(left_controller.keyboard_target)
        self.assertIs(right_controller.keyboard_target, right_pin)
        self.assertEqual(left_active.highlight.get_markersize(), 8)
        self.assertEqual(left_active.highlight.get_markeredgecolor(), "red")
        self.assertEqual(right_pin.highlight.get_markersize(), 10)
        self.assertEqual(right_pin.highlight.get_markeredgecolor(), "gold")

        session.figure.canvas.draw()
        bbox = left_active.tooltip.get_window_extent(
            session.figure.canvas.get_renderer()
        )
        send_canvas_mouse_event(
            session,
            "button_press_event",
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )
        send_canvas_mouse_event(
            session,
            "button_release_event",
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )

        self.assertIs(left_controller.keyboard_target, left_active)
        self.assertIsNone(right_controller.keyboard_target)
        self.assertEqual(left_active.highlight.get_markeredgecolor(), "gold")
        self.assertEqual(right_pin.highlight.get_markeredgecolor(), "blue")

    def test_delete_uses_clicked_pin_after_hovering_another_panel(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [10.0, 11.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        left_controller = session.controllers[0]
        send_mouse_event(
            session,
            "button_press_event",
            left,
            0,
            0.0,
            button=1,
            key="shift",
        )

        send_mouse_event(session, "motion_notify_event", right, 0, 10.0)
        send_key_event(session, "delete")

        self.assertEqual(left_controller.pinned_selections, ())

    def test_clicking_a_tooltip_makes_its_panel_the_keyboard_target(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "left",
                    panel=(0, 0),
                    color="red",
                ),
                SeriesData(
                    [0, 1, 2],
                    [10.0, 11.0, 12.0],
                    "right",
                    panel=(0, 1),
                    color="blue",
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(session, "button_press_event", right, 0, 10.0, button=1)
        send_mouse_event(session, "button_press_event", left, 0, 0.0, button=1)

        right_tooltip = right.texts[0]
        right_tooltip.set_visible(True)
        session.figure.canvas.draw()
        bbox = right_tooltip.get_window_extent(session.figure.canvas.get_renderer())
        tooltip_x = bbox.x0 + bbox.width / 2
        tooltip_y = bbox.y0 + bbox.height / 2
        send_canvas_mouse_event(
            session,
            "button_press_event",
            tooltip_x,
            tooltip_y,
            button=1,
        )
        send_canvas_mouse_event(
            session,
            "button_release_event",
            tooltip_x,
            tooltip_y,
            button=1,
        )

        send_mouse_event(session, "motion_notify_event", left, 0, 0.0)
        send_key_event(session, "right")

        self.assertEqual(cursor_highlights(left)["red"].get_xdata()[0], 0)
        self.assertEqual(cursor_highlights(right)["blue"].get_xdata()[0], 1)

    def test_keyboard_movement_carries_the_visible_tooltip_with_the_cursor(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _position: f"F{value:.2f}")
        )
        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _position: f"V{value:.2f}")
        )

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        tooltip = axis.texts[0]
        self.assertTrue(tooltip.get_visible())
        self.assertEqual(tooltip.get_text(), "Frame: F0.00\nValue: V0.00")

        send_key_event(session, "right")

        self.assertEqual(cursor_highlights(axis)["red"].get_xdata()[0], 1)
        self.assertEqual(tooltip.xy, (1, 1.0))
        self.assertEqual(tooltip.get_text(), "Frame: F1.00\nValue: V1.00")

    def test_toolbar_navigation_mode_suspends_cursor_interaction(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        manager = session.figure.canvas.manager

        with patch.object(manager, "toolbar", SimpleNamespace(mode="pan/zoom")):
            send_mouse_event(session, "motion_notify_event", axis, 1, 1.0)
            send_mouse_event(session, "button_press_event", axis, 1, 1.0, button=1)
            send_key_event(session, "end")

        self.assertEqual(cursor_highlights(axis)["red"].get_xdata()[0], 0)

    def test_non_click_interactions_never_create_another_visible_tooltip(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1, 2],
                    [0.0, 1.0, 2.0],
                    "left",
                    panel=(0, 0),
                    color="red",
                ),
                SeriesData(
                    [0, 1, 2],
                    [10.0, 11.0, 12.0],
                    "right",
                    panel=(0, 1),
                    color="blue",
                ),
            ]
        )
        left, right = session.axes

        def visible_tooltips():
            return [
                tooltip
                for axis in session.axes
                for tooltip in axis.texts
                if tooltip.get_visible()
            ]

        session.figure.canvas.draw()
        self.assertEqual(visible_tooltips(), [])
        send_mouse_event(session, "motion_notify_event", left, 0, 0.0)
        self.assertEqual(visible_tooltips(), [])

        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1
        )
        send_mouse_event(
            session, "button_press_event", left, 1, 1.0, button=1
        )
        clicked_tooltip_state = (left.texts[0].xy, left.texts[0].get_text())
        send_mouse_event(session, "motion_notify_event", left, 2, 2.0)
        self.assertEqual(
            (left.texts[0].xy, left.texts[0].get_text()),
            clicked_tooltip_state,
        )
        send_key_event(session, "home")
        self.assertEqual(left.texts[0].xy, (0, 0.0))
        self.assertEqual(visible_tooltips(), [left.texts[0]])

        session.toggle_axes_maximized(left)
        session.figure.canvas.draw()
        session.restore_layout()
        session.figure.canvas.draw()
        self.assertEqual(visible_tooltips(), [left.texts[0]])

        manager = session.figure.canvas.manager
        with patch.object(manager, "toolbar", SimpleNamespace(mode="pan/zoom")):
            send_mouse_event(session, "motion_notify_event", right, 0, 10.0)
        self.assertEqual(visible_tooltips(), [left.texts[0]])

        send_mouse_event(
            session, "button_press_event", right, 0, 10.0, button=3
        )
        self.assertEqual(visible_tooltips(), [left.texts[0]])

    def test_dragging_tooltip_moves_text_without_moving_cursor_anchor(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        session.figure.canvas.draw()
        tooltip = axis.texts[0]
        initial_position = tooltip.get_position()
        bbox = tooltip.get_window_extent(session.figure.canvas.get_renderer())
        press = MouseEvent(
            "button_press_event",
            session.figure.canvas,
            bbox.x0 + bbox.width / 2,
            bbox.y0 + bbox.height / 2,
            button=1,
        )
        session.figure.canvas.callbacks.process("button_press_event", press)
        send_mouse_event(session, "motion_notify_event", axis, 1, 1.0, button=1)
        send_mouse_event(session, "button_release_event", axis, 1, 1.0, button=1)

        self.assertEqual(cursor_highlights(axis)["red"].get_xdata()[0], 0)
        self.assertNotEqual(tooltip.get_position(), initial_position)

    def test_cursor_visual_state_and_extra_cursor_deletion_shortcuts(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        preview = session.controllers[0].hover_highlight
        self.assertEqual(preview.get_markeredgecolor(), "gold")

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        active = session.controllers[0].active_selection.highlight
        self.assertEqual(active.get_marker(), "o")
        send_key_event(session, "delete")
        self.assertEqual(len(cursor_highlight_lines(axis)), 2)

        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1, key="shift"
        )
        self.assertEqual(len(cursor_highlight_lines(axis)), 3)
        send_key_event(session, "backspace")
        self.assertEqual(len(cursor_highlight_lines(axis)), 2)

        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1, key="shift"
        )
        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1, key="shift"
        )
        self.assertEqual(len(cursor_highlight_lines(axis)), 4)
        send_key_event(session, "escape")
        self.assertEqual(len(cursor_highlight_lines(axis)), 2)

    def test_escape_clears_extra_cursors_from_every_panel(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData(
                    [0, 1], [0.0, 1.0], "left", panel=(0, 0), color="red"
                ),
                SeriesData(
                    [0, 1], [0.0, 1.0], "right", panel=(0, 1), color="blue"
                ),
            ]
        )
        left, right = session.axes
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, key="shift"
        )
        send_mouse_event(
            session, "button_press_event", right, 0, 0.0, button=1, key="shift"
        )
        self.assertEqual(
            [len(cursor_highlight_lines(axis)) for axis in (left, right)], [2, 2]
        )

        send_key_event(session, "escape")

        self.assertEqual(
            [len(cursor_highlight_lines(axis)) for axis in (left, right)], [1, 1]
        )

    def test_clicked_tooltip_uses_axis_formatters_without_a_series_label(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0.25, 1.25], [0.0, 1.0], "sample", color="red")]
        )
        axis = session.axes[0]
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _position: f"F{value:.2f}")
        )
        axis.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _position: f"V{value:.2f}")
        )

        send_mouse_event(session, "motion_notify_event", axis, 0.25, 0.0)
        self.assertEqual(len(axis.texts), 0)
        send_mouse_event(
            session, "button_press_event", axis, 0.25, 0.0, button=1
        )
        tooltip = session.controllers[0].active_selection.tooltip

        self.assertTrue(tooltip.get_visible())
        self.assertEqual(tooltip.get_text(), "Frame: F0.25\nValue: V0.00")
        self.assertNotIn("sample", tooltip.get_text())

    def test_cursors_use_only_markers_and_tooltips(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "sample", color="red")]
        )
        axis = session.axes[0]

        self.assertEqual(len(axis.lines), 2)
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        marker = cursor_highlights(axis)["red"]
        self.assertEqual(marker.get_marker(), "o")
        self.assertEqual(marker.get_markeredgecolor(), "gold")
        self.assertTrue(axis.texts[0].get_visible())
        self.assertEqual(len(axis.lines), 3)

    def test_plot_session_cursor_management_disconnect_and_close_are_idempotent(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "sample", color="red")]
        )
        axis = session.axes[0]
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        send_mouse_event(
            session, "button_press_event", axis, 0, 0.0, button=1, key="shift"
        )
        self.assertTrue(session.remove_selected_cursor())
        self.assertEqual(len(cursor_highlight_lines(axis)), 1)

        for frame, value in ((0, 0.0), (0, 0.0)):
            send_mouse_event(
                session,
                "button_press_event",
                axis,
                frame,
                value,
                button=1,
                key="shift",
            )
        self.assertEqual(session.clear_extra_cursors(), 2)

        session.disconnect()
        session.disconnect()
        send_mouse_event(session, "motion_notify_event", axis, 1, 1.0)
        self.assertEqual(cursor_highlight_lines(axis)[0].get_xdata()[0], 0)

        figure_number = session.figure.number
        session.close()
        session.close()
        self.assertNotIn(figure_number, plt.get_fignums())

        close_event_session = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "close-event", color="red")]
        )
        close_axis = close_event_session.axes[0]
        close_event_session.figure.canvas.callbacks.process(
            "close_event", CloseEvent("close_event", close_event_session.figure.canvas)
        )
        send_mouse_event(
            close_event_session, "motion_notify_event", close_axis, 1, 1.0
        )
        self.assertEqual(cursor_highlight_lines(close_axis)[0].get_xdata()[0], 0)
        close_event_session.close()

    def test_disconnect_and_close_event_restore_layout_and_disable_legends(self):
        from interactive_plotting import create_interactive_plot

        def build_two_panel_session():
            return create_interactive_plot(
                [
                    SeriesData(
                        [0, 1],
                        [0.0, 1.0],
                        "left",
                        panel=(0, 0),
                        color="red",
                    ),
                    SeriesData(
                        [0, 1],
                        [0.0, 1.0],
                        "right",
                        panel=(0, 1),
                        color="blue",
                    ),
                ]
            )

        session = build_two_panel_session()
        original_layout = axes_layout_snapshot(session)
        left, right = session.axes
        self.assertTrue(left.get_legend().get_draggable())
        session.toggle_axes_maximized(left)
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1
        )

        session.disconnect()
        session.disconnect()

        self.assertEqual(axes_layout_snapshot(session), original_layout)
        self.assertFalse(left.get_legend().get_draggable())
        send_mouse_event(
            session, "button_press_event", left, 0, 0.0, button=1, dblclick=True
        )
        self.assertTrue(right.get_visible())
        self.assertFalse(session.toggle_axes_maximized(left))
        self.assertEqual(axes_layout_snapshot(session), original_layout)

        close_event_session = build_two_panel_session()
        close_original = axes_layout_snapshot(close_event_session)
        close_left = close_event_session.axes[0]
        close_event_session.toggle_axes_maximized(close_left)
        close_event_session.figure.canvas.callbacks.process(
            "close_event",
            CloseEvent("close_event", close_event_session.figure.canvas),
        )
        self.assertEqual(axes_layout_snapshot(close_event_session), close_original)
        self.assertFalse(close_left.get_legend().get_draggable())
        close_event_session.close()
        close_event_session.close()

    def test_dispatch_and_transform_cache_scale_per_figure(self):
        from interactive_plotting import create_interactive_plot, make_demo_series

        single = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "sample", color="red")]
        )
        multi = create_interactive_plot(make_demo_series(seed=9))
        event_names = (
            "motion_notify_event",
            "button_press_event",
            "button_release_event",
            "key_press_event",
            "draw_event",
            "close_event",
        )

        def callback_counts(session):
            callbacks = session.figure.canvas.callbacks.callbacks
            return {name: len(callbacks.get(name, {})) for name in event_names}

        single_counts = callback_counts(single)
        multi_counts = callback_counts(multi)
        additional_legends = len(multi.controllers) - len(single.controllers)
        for event_name in event_names:
            expected_difference = (
                additional_legends
                if event_name in ("motion_notify_event", "button_release_event")
                else 0
            )
            self.assertEqual(
                multi_counts[event_name] - single_counts[event_name],
                expected_difference,
            )

        axis = single.axes[0]
        original_transform = axis.transData.transform
        with patch.object(
            axis.transData, "transform", wraps=original_transform
        ) as transform:
            axis.set_xlim(-10, 10)
            self.assertEqual(transform.call_count, 0)

            x_pixel, y_pixel = original_transform((1, 1.0))
            motion = MouseEvent(
                "motion_notify_event", single.figure.canvas, x_pixel, y_pixel
            )
            single.figure.canvas.callbacks.process("motion_notify_event", motion)
            self.assertGreater(transform.call_count, 0)
            calls_after_hover = transform.call_count

            single.figure.canvas.callbacks.process(
                "draw_event", SimpleNamespace(canvas=single.figure.canvas)
            )
            self.assertEqual(transform.call_count, calls_after_hover)

            single.figure.set_size_inches(8, 6)
            single.figure.canvas.callbacks.process(
                "draw_event", SimpleNamespace(canvas=single.figure.canvas)
            )
            self.assertEqual(transform.call_count, calls_after_hover)
            resized_x, resized_y = original_transform((0, 0.0))
            resized_motion = MouseEvent(
                "motion_notify_event",
                single.figure.canvas,
                resized_x,
                resized_y,
            )
            single.figure.canvas.callbacks.process(
                "motion_notify_event", resized_motion
            )
            self.assertGreater(transform.call_count, calls_after_hover)


class ViewNavigationKeymapTests(unittest.TestCase):
    """Session keymap claims must stay balanced despite Agg's silent closes."""

    SETTINGS = ("keymap.back", "keymap.forward", "keymap.home")

    def setUp(self):
        from interactive_plotting import core as plot_core

        self._core = plot_core
        self._claims = plot_core._view_navigation_key_claims
        self._snapshots = plot_core._view_navigation_key_snapshots
        self._defaults = {
            setting: list(plt.rcParams[setting]) for setting in self.SETTINGS
        }

    def tearDown(self):
        plt.close("all")
        self._core._view_navigation_key_claims = self._claims
        self._core._view_navigation_key_snapshots = self._snapshots
        for setting, snapshot in self._defaults.items():
            plt.rcParams[setting] = snapshot

    def test_sessions_detach_view_navigation_keys_until_the_last_disconnect(self):
        from interactive_plotting import create_interactive_plot

        first = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "first", color="red")]
        )
        second = create_interactive_plot(
            [SeriesData([0, 1], [0.0, 1.0], "second", color="blue")]
        )
        self.assertNotIn("left", plt.rcParams["keymap.back"])
        self.assertNotIn("backspace", plt.rcParams["keymap.back"])
        self.assertNotIn("right", plt.rcParams["keymap.forward"])
        self.assertNotIn("home", plt.rcParams["keymap.home"])

        first.disconnect()
        self.assertNotIn("left", plt.rcParams["keymap.back"])

        second.close()
        for setting in self.SETTINGS:
            self.assertEqual(
                list(plt.rcParams[setting]), self._defaults[setting]
            )

    def test_keymap_cleanup_tolerates_keys_already_removed(self):
        from interactive_plotting import create_interactive_plot

        reduced = [key for key in self._defaults["keymap.home"] if key != "home"]
        with patch.dict(plt.rcParams, {"keymap.home": list(reduced)}):
            session = create_interactive_plot(
                [SeriesData([0, 1], [0.0, 1.0], "sample", color="red")]
            )
            self.assertNotIn("home", plt.rcParams["keymap.home"])
            session.disconnect()
            self.assertEqual(list(plt.rcParams["keymap.home"]), reduced)


if __name__ == "__main__":
    unittest.main()

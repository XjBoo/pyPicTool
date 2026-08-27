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
        self.assertTrue(any(text.get_visible() for text in first.texts))
        send_mouse_event(
            session, "button_press_event", first, frame, value, button=1
        )
        self.assertEqual(marker.get_marker(), "s")

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
        marker = cursor_highlights(left)["red"]
        tooltip = left.texts[0]
        state_before = (
            tuple(marker.get_xdata()),
            tuple(marker.get_ydata()),
            marker.get_marker(),
            marker.get_markeredgecolor(),
            tooltip.get_visible(),
            tooltip.get_text(),
            tooltip.get_position(),
            len(cursor_highlight_lines(left)),
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
                marker.get_marker(),
                marker.get_markeredgecolor(),
                tooltip.get_visible(),
                tooltip.get_text(),
                tooltip.get_position(),
                len(cursor_highlight_lines(left)),
            ),
            state_before,
        )

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
                marker.get_marker(),
                marker.get_markeredgecolor(),
                tooltip.get_visible(),
                tooltip.get_text(),
                tooltip.get_position(),
                len(cursor_highlight_lines(left)),
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
        self.assertEqual(marker.get_xdata()[0], 1)
        self.assertEqual(marker.get_marker(), "s")

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
        send_mouse_event(session, "motion_notify_event", session.axes[0], 1, 2.0)
        self.assertNotEqual(
            cursor_highlight_lines(session.axes[0])[0].get_xdata()[0], 1
        )

    def test_hover_synchronizes_each_series_by_nearest_frame_value(self):
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

        figure.canvas.callbacks.process("motion_notify_event", event)

        highlights = {
            line.get_color(): line
            for line in axis.lines
            if line.get_marker() == "o"
        }
        self.assertEqual(highlights["red"].get_xdata()[0], 14)
        self.assertEqual(highlights["blue"].get_xdata()[0], 10)
        self.assertEqual(highlights["green"].get_xdata()[0], 18)

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

        self.assertEqual(cursor_highlights(axis)["blue"].get_xdata()[0], 0)

    def test_duplicate_frames_preserve_the_explicit_selected_point(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 0, 1], [0.0, 10.0, 20.0], "duplicates", color="red")]
        )
        axis = session.axes[0]

        send_mouse_event(session, "motion_notify_event", axis, 0, 10.0)
        selected = cursor_highlights(axis)["red"]
        self.assertEqual(selected.get_ydata()[0], 10.0)

        send_key_event(session, "right")
        self.assertEqual(selected.get_xdata()[0], 1)
        self.assertEqual(selected.get_ydata()[0], 20.0)

    def test_ordinary_clicks_keep_default_cursor_owners_fixed(self):
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
        highlights = cursor_highlights(axis)
        self.assertEqual(highlights["red"].get_marker(), "s")
        self.assertEqual(highlights["blue"].get_marker(), "s")

        send_mouse_event(session, "button_press_event", axis, 1, 1.0, button=1)
        self.assertEqual(highlights["red"].get_xdata()[0], 1)
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        self.assertEqual(highlights["red"].get_xdata()[0], 0)
        self.assertEqual(highlights["blue"].get_xdata()[0], 0)

    def test_locked_selected_cursor_freezes_and_unlocked_keyboard_synchronizes(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [
                SeriesData([0, 14], [0.0, 1.0], "red", color="red"),
                SeriesData([0, 4, 10], [2.0, 3.0, 4.0], "blue", color="blue"),
            ]
        )
        axis = session.axes[0]
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)

        send_key_event(session, "end")
        highlights = cursor_highlights(axis)
        self.assertEqual(highlights["red"].get_xdata()[0], 0)
        self.assertEqual(highlights["blue"].get_xdata()[0], 0)

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        send_key_event(session, "end")
        self.assertEqual(highlights["red"].get_xdata()[0], 14)
        self.assertEqual(highlights["blue"].get_xdata()[0], 10)

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

    def test_dragging_tooltip_moves_text_without_moving_cursor_anchor(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0, 1, 2], [0.0, 1.0, 2.0], "sample", color="red")]
        )
        axis = session.axes[0]
        send_mouse_event(session, "motion_notify_event", axis, 0, 0.0)
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
        default = cursor_highlight_lines(axis)[0]
        self.assertEqual(default.get_markeredgecolor(), "gold")

        send_mouse_event(session, "button_press_event", axis, 0, 0.0, button=1)
        self.assertEqual(default.get_marker(), "s")
        send_key_event(session, "delete")
        self.assertEqual(len(cursor_highlight_lines(axis)), 1)

        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1, key="shift"
        )
        self.assertEqual(len(cursor_highlight_lines(axis)), 2)
        send_key_event(session, "backspace")
        self.assertEqual(len(cursor_highlight_lines(axis)), 1)

        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1, key="shift"
        )
        send_mouse_event(
            session, "button_press_event", axis, 1, 1.0, button=1, key="shift"
        )
        self.assertEqual(len(cursor_highlight_lines(axis)), 3)
        send_key_event(session, "escape")
        self.assertEqual(len(cursor_highlight_lines(axis)), 1)

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

    def test_tooltip_is_lazy_and_uses_axis_frame_formatter(self):
        from interactive_plotting import create_interactive_plot

        session = create_interactive_plot(
            [SeriesData([0.25, 1.25], [0.0, 1.0], "sample", color="red")]
        )
        axis = session.axes[0]
        tooltip = axis.texts[0]
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _position: f"F{value:.2f}")
        )

        self.assertFalse(tooltip.get_visible())
        send_mouse_event(session, "motion_notify_event", axis, 1.25, 1.0)

        self.assertTrue(tooltip.get_visible())
        self.assertIn("Frame: F1.25", tooltip.get_text())

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
        self.assertEqual(marker.get_marker(), "s")
        self.assertEqual(marker.get_markeredgecolor(), "gold")
        self.assertTrue(axis.texts[0].get_visible())
        self.assertEqual(len(axis.lines), 2)

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


if __name__ == "__main__":
    unittest.main()

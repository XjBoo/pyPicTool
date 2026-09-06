"""External callers exercise the same interface used by the demo."""

import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from matplotlib.markers import MarkerStyle

from interactive_plotting import figure, create_interactive_plot, make_demo_series
from interactive_plotting import core
from tests.test_public_api import send_mouse_event, send_key_event, axes_layout_snapshot


class FigureInterfaceTests(unittest.TestCase):
    def build(self, description):
        session = description.build()
        self.addCleanup(session.close)
        return session

    def test_description_has_no_window_and_build_does_not_show(self):
        before = plt.get_fignums()
        with patch("matplotlib.pyplot.show") as show:
            fig = figure()
            ax = fig.subplot(1)
            self.assertIs(ax.plot([0, 1], [1, 2]), ax)
            self.assertEqual(plt.get_fignums(), before)
            session = self.build(fig)
            show.assert_not_called()
        self.assertEqual(len(session.axes), 1)
        self.assertEqual(session.axes[0].get_xlabel(), "")
        self.assertEqual(session.axes[0].get_ylabel(), "")

    def test_sparse_grid_empty_panels_and_multiple_figures(self):
        first = self.build(figure())
        fig = figure(rows=2, cols=2, title="Overview", figsize=(10, 8))
        fig.subplot(1).plot([0, 1], [1, 2])
        fig.subplot(3, title="Empty", xlabel="Time")
        fig.subplot(4).plot([0, 1], [2, 1])
        session = self.build(fig)
        self.assertIsNot(first.figure, session.figure)
        self.assertEqual([ax.get_visible() for ax in first.axes], [False])
        self.assertEqual([ax.get_visible() for ax in session.axes], [True, False, True, True])
        np.testing.assert_array_equal(session.figure.get_size_inches(), [10, 8])
        self.assertIn("Overview", [t.get_text() for t in session.figure.texts])
        self.assertEqual(session.axes[2].get_title(), "Empty")
        self.assertIsNone(session.axes[2].get_legend())
        first.close()
        self.assertIn(session.figure.number, plt.get_fignums())
        before = axes_layout_snapshot(session)
        send_mouse_event(session, "button_press_event", session.axes[2], .5, .5,
                         button=1, dblclick=True)
        self.assertEqual([ax.get_visible() for ax in session.axes], [False, False, True, False])
        send_key_event(session, "escape")
        self.assertEqual(axes_layout_snapshot(session), before)

    def test_repeated_subplot_updates_only_supplied_text(self):
        fig = figure()
        ax = fig.subplot(1, title="Before", xlabel="Time", ylabel="Temperature")
        ax.plot([0, 1], [2, 3], label="Data")
        self.assertIs(fig.subplot(1, title="After"), ax)
        session = self.build(fig)
        actual = session.axes[0]
        self.assertEqual(actual.get_title(), "After")
        self.assertEqual(actual.title.get_horizontalalignment(), "left")
        self.assertEqual(actual.get_xlabel(), "Time")
        self.assertEqual(actual.get_ylabel(), "Temperature")
        self.assertEqual(len(session.controllers[0].series_list), 1)

    def test_curve_styles_legend_and_missing_values(self):
        fig = figure()
        ax = fig.subplot(1)
        ax.plot([0, 1, 2], [1, np.nan, 3], label="Circle", color="blue",
                marker="o", linewidth=2.5, markersize=7)
        ax.plot([0, 1, 2], [3, 2, 1], label="_Square", color="orange",
                marker="s", linestyle="dashed")
        ax.plot([0, 1, 2], [0, 1, 0], marker="^", linestyle="None", label="")
        session = self.build(fig)
        actual = session.axes[0]
        self.assertEqual(len(session.controllers[0].series_list), 3)
        self.assertEqual(to_rgba(actual.lines[0].get_color()), to_rgba("blue"))
        self.assertEqual(actual.lines[0].get_linewidth(), 2.5)
        self.assertEqual(actual.lines[1].get_linestyle(), "--")
        self.assertTrue(np.isnan(actual.lines[0].get_ydata()[1]))
        np.testing.assert_array_equal(actual.collections[0].get_sizes(), [49])
        self.assertEqual(len(actual.collections[0].get_offsets()), 2)
        square = MarkerStyle("s")
        np.testing.assert_array_equal(actual.collections[1].get_paths()[0].vertices,
                                      square.get_path().transformed(square.get_transform()).vertices)
        self.assertEqual([text.get_text() for text in actual.get_legend().texts],
                         ["Circle", "_Square"])
        self.assertEqual([handle.get_marker() for handle in actual.get_legend().legend_handles],
                         ["o", "s"])
        self.assertEqual(actual.get_legend().legend_handles[0].get_linewidth(), 2.5)
        self.assertEqual(actual.get_legend().legend_handles[0].get_markersize(), 7)

    def test_color_cycles_are_independent_and_unlabelled_has_no_legend(self):
        fig = figure(rows=1, cols=2)
        for index in (1, 2):
            ax = fig.subplot(index)
            for offset in range(12):
                ax.plot([0, 1], [offset, offset + 1])
        session = self.build(fig)
        first, second = session.axes
        colors = [line.get_color() for line in first.lines[:12]]
        self.assertEqual(colors, [line.get_color() for line in second.lines[:12]])
        self.assertNotEqual(colors[0], colors[1])
        self.assertEqual(colors[0], colors[10])
        self.assertIsNone(first.get_legend())
        self.assertIsNone(second.get_legend())

    def test_line_only_and_unfilled_points_remain_visible(self):
        fig = figure()
        fig.subplot(1).plot([0, 1], [0, 1], marker=None, label="Line")
        fig.subplot(1).plot([0, 1], [1, 0], marker="x", linestyle="None", label="Points")
        session = self.build(fig)
        ax = session.axes[0]
        self.assertEqual(len(ax.collections), 1)
        self.assertGreater(ax.collections[0].get_linewidths()[0], 0)
        self.assertEqual(ax.lines[1].get_linestyle(), "None")
        self.assertEqual(ax.get_legend().legend_handles[1].get_marker(), "x")

    def test_invalid_parameters_are_atomic_and_window_free(self):
        before = plt.get_fignums()
        for kwargs in ({"rows": 0}, {"cols": -1}, {"rows": True}, {"cols": 1.5},
                       {"figsize": (1, 0)}, {"figsize": (1,)}, {"figsize": "12"},
                       {"figsize": (np.inf, 2)}, {"title": 123}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                figure(**kwargs)
        fig = figure()
        for index in (0, -1, True, 1.5, 2):
            with self.subTest(index=index), self.assertRaises(ValueError):
                fig.subplot(index)
        ax = fig.subplot(1, title="Keep")
        for kwargs in ({"color": "invalid"}, {"marker": "bad"}, {"marker": []},
                       {"linestyle": "bad"}, {"linewidth": 0}, {"markersize": -1},
                       {"markersize": np.nan}, {"linewidth": True}, {"label": 12},
                       {"marker": None, "linestyle": "None"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                ax.plot([0, 1], [0, 1], **kwargs)
        for x, y in (([], []), ([0], [1, 2]), ([np.nan], [1]), ([0], [np.nan]),
                     (["x"], [1]), ([[1]], [1])):
            with self.subTest(x=x, y=y), self.assertRaises(ValueError):
                ax.plot(x, y)
        with self.assertRaises(ValueError):
            fig.subplot(1, title="Changed", xlabel=5)
        self.assertEqual(plt.get_fignums(), before)
        ax.plot([0, 1], [0, 1])
        session = self.build(fig)
        self.assertEqual(len(session.controllers[0].series_list), 1)
        self.assertEqual(session.axes[0].get_title(), "Keep")

    def test_data_is_copied_and_description_freezes_after_build(self):
        x = np.array([0, 1])
        y = np.array([2, 3])
        fig = figure(rows=1, cols=2)
        ax = fig.subplot(1)
        ax.plot(x, y)
        x[:] = 100
        y[:] = 100
        session = self.build(fig)
        np.testing.assert_array_equal(session.axes[0].lines[0].get_xdata(), [0, 1])
        np.testing.assert_array_equal(session.axes[0].lines[0].get_ydata(), [2, 3])
        self.assertIs(fig.build(), session)
        self.assertIs(fig.subplot(1), ax)
        for mutate in (lambda: ax.plot([0], [1]), lambda: fig.subplot(1, title="New"),
                       lambda: fig.subplot(2)):
            with self.assertRaises(RuntimeError):
                mutate()
        session.close()
        before = plt.get_fignums()
        self.assertIs(fig.build(), session)
        self.assertEqual(plt.get_fignums(), before)

    def test_failed_build_cleans_controllers_legends_and_can_retry(self):
        fig = figure()
        fig.subplot(1).plot([0, 1], [0, 1], label="Data")
        before = plt.get_fignums()
        claims = core._view_navigation_key_claims
        captured = []

        def fail(figure):
            captured.append(figure)
            raise RuntimeError("injected toolbar failure")

        with patch("interactive_plotting.core.install_toolbar_toggle", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                fig.build()
        self.assertEqual(plt.get_fignums(), before)
        self.assertEqual(core._view_navigation_key_claims, claims)
        self.assertFalse(captured[0].axes[0].get_legend().get_draggable())
        self.assertEqual(captured[0].axes[0].callbacks.callbacks, {})
        fig.subplot(1, title="Retry").plot([0, 1], [1, 0])
        session = self.build(fig)
        self.assertEqual(session.axes[0].get_title(), "Retry")
        self.assertEqual(len(session.controllers[0].series_list), 2)
        session.disconnect()
        session.disconnect()
        self.assertEqual(core._view_navigation_key_claims, claims)

    def test_subplot_allocation_failure_does_not_leak_figure(self):
        fig = figure()
        before = plt.get_fignums()
        with patch("matplotlib.figure.Figure.subplots", side_effect=RuntimeError("allocate")):
            with self.assertRaisesRegex(RuntimeError, "allocate"):
                fig.build()
        self.assertEqual(plt.get_fignums(), before)
        self.build(fig)

    def test_custom_grid_interactions_and_other_window_survive_close(self):
        fig = figure(rows=2, cols=2, title="Selections")
        for index in (1, 4):
            fig.subplot(index).plot([0, 1, 2], [0, 1, 0], marker="s")
        session = self.build(fig)
        other = figure()
        other.subplot(1).plot([0, 1, 2], [2, 3, 2])
        second = self.build(other)
        ax = session.axes[0]
        before = axes_layout_snapshot(session)
        send_mouse_event(session, "motion_notify_event", ax, 0, 0)
        self.assertTrue(session.controllers[0].hover_highlight.get_visible())
        send_mouse_event(session, "button_press_event", ax, 0, 0, button=1)
        selected = session.controllers[0].active_selection
        self.assertEqual(selected.highlight.get_marker(), "o")
        send_key_event(session, "right")
        self.assertEqual(selected.current_index, 1)
        send_mouse_event(session, "button_press_event", session.axes[3], 0, 0,
                         button=1, key="shift")
        send_mouse_event(session, "button_press_event", ax, 1, .5, button=1, dblclick=True)
        send_key_event(session, "escape")
        self.assertEqual(axes_layout_snapshot(session), before)
        self.assertEqual(len(session.controllers[1].pinned_selections), 1)
        session.close()
        send_mouse_event(second, "button_press_event", second.axes[0], 0, 2, button=1)
        send_key_event(second, "right")
        self.assertEqual(second.controllers[0].active_selection.current_index, 1)

    def test_new_and_legacy_entry_points_render_equivalent_demo(self):
        data = make_demo_series(seed=7)
        old = create_interactive_plot(data)
        self.addCleanup(old.close)
        fig = figure(rows=3, cols=2)
        for item in data:
            fig.subplot(item.panel[0] * 2 + item.panel[1] + 1,
                        title=item.panel_title, xlabel="Frame Number", ylabel="Value").plot(
                            item.frames, item.values, label=item.label, color=item.color)
        new = self.build(fig)
        for original, actual in zip(old.axes, new.axes):
            self.assertEqual(original.get_title(), actual.get_title())
            self.assertEqual(original.get_xlabel(), actual.get_xlabel())
            self.assertEqual(original.get_ylabel(), actual.get_ylabel())
            np.testing.assert_allclose(original.get_position().bounds, actual.get_position().bounds)
            for expected, result in zip(original.lines[:2], actual.lines[:2]):
                np.testing.assert_array_equal(expected.get_ydata(), result.get_ydata())
                self.assertEqual(to_rgba(expected.get_color()), to_rgba(result.get_color()))


if __name__ == "__main__":
    unittest.main()

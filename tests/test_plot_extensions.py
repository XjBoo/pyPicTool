"""Behavioral coverage for the plotting TODO ledger."""
import unittest
import copy
from dataclasses import replace
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import MouseEvent, KeyEvent
from matplotlib.colors import to_rgba

from interactive_plotting import (figure, build_figure, FigureSpec, PanelSpec,
                                  SeriesData, SuptitleStyle)
from tests.test_public_api import send_mouse_event, send_key_event


class PlotExtensionsTests(unittest.TestCase):
    def build(self, builder):
        session = builder.build()
        self.addCleanup(session.close)
        session.figure.canvas.draw()
        return session

    def click(self, session, axis, x, y, **kwargs):
        send_mouse_event(session, "button_press_event", axis, x, y, button=1, **kwargs)
        send_mouse_event(session, "button_release_event", axis, x, y, button=1)

    def test_dual_axes_click_hover_keyboard_and_layout(self):
        fig = figure(rows=2)
        ax = fig.subplot(1, ylabel="Temperature", right_ylabel="Pressure")
        ax.plot([0, 1, 2], [0, 2, 0], label="Left")
        ax.plot([0, 1, 2], [100, 100, 200], label="Right", yaxis="right")
        fig.subplot(2).plot([0, 1], [0, 1])
        session = self.build(fig)
        left, right = session.axes[0], session.right_axes[1]
        self.assertEqual(left.get_xlim(), right.get_xlim())
        self.assertNotEqual(left.get_ylim(), right.get_ylim())
        self.assertEqual(right.get_ylabel(), "Pressure")
        self.assertEqual([t.get_text() for t in right.get_legend().texts], ["Left", "Right"])
        # Real MouseEvent sees the top twin, even when targeting a left point.
        self.click(session, left, 1, 2)
        self.assertIsNotNone(session.controllers[0].active_selection)
        self.click(session, right, 1, 100)
        self.assertIsNone(session.controllers[0].active_selection)
        cursor = session.controllers[1].active_selection
        self.assertIsNotNone(cursor)
        send_key_event(session, "right")
        self.assertEqual(cursor.current_index, 2)
        before = [tuple(a.get_position().bounds) for a in session.figure.axes]
        session.toggle_axes_maximized(right)
        self.assertTrue(left.get_visible() and right.get_visible())
        self.assertFalse(session.axes[1].get_visible())
        session.restore_layout()
        self.assertEqual(before, [tuple(a.get_position().bounds) for a in session.figure.axes])
        send_mouse_event(session, "motion_notify_event", left, 2, 0)
        self.assertTrue(session.controllers[0].hover_highlight.get_visible())

    def test_tooltip_callback_original_index_enum_and_failure_fallback(self):
        received = []
        def tooltip(point):
            received.append(point)
            return f"{point.series.label}: {point.index} / {point.y_text}"
        fig = figure()
        mapping = {0: "Stopped", 1: "Running", 2: "Failed"}
        fig.subplot(1, y_enum=mapping).plot([0, 1, 2], [0, np.nan, 2],
                                          label="State", tooltip=tooltip)
        mapping[2] = "Modified"
        session = self.build(fig)
        self.click(session, session.axes[0], 0, 0)
        send_key_event(session, "end")
        self.assertEqual(received[-1].index, 2)
        self.assertEqual(received[-1].y, 2)
        self.assertEqual(received[-1].y_text, "Failed")
        self.assertEqual(session.controllers[0].active_selection.tooltip.get_text(),
                         "State: 2 / Failed")
        fig = figure()
        fig.subplot(1, right_y_enum={1: "On"}).plot([0, 1], [1, 1], yaxis="right",
                                                       tooltip=lambda p: 42)
        session = self.build(fig)
        with self.assertWarnsRegex(RuntimeWarning, "must return a string"):
            self.click(session, session.right_axes[1], 0, 1)
        self.assertIn("Value: On", session.controllers[0].active_selection.tooltip.get_text())

    def test_theme_title_and_public_spec_round_trip(self):
        baseline = copy.deepcopy(dict(plt.rcParams))
        fig = figure(theme="matlab", title="Experiment\nSecond line\nThird line",
                     window_title="Signals", suptitle_style=SuptitleStyle(
                         fontsize=16, linespacing=1.6, horizontalalignment="left"))
        fig.subplot(1, legend_loc="lower left").plot([0, 1], [0, 1], label="A")
        spec = fig.to_spec()
        self.assertIsInstance(spec, FigureSpec)
        self.assertEqual(plt.get_fignums(), [])
        session = build_figure(spec)
        self.addCleanup(session.close)
        session.figure.canvas.draw()
        self.assertEqual(to_rgba(session.axes[0].lines[0].get_color()), to_rgba("#0072BD"))
        self.assertTrue(session.axes[0].spines["top"].get_visible())
        self.assertEqual(session.axes[0].get_legend()._loc, 3)
        title = session.figure._suptitle
        self.assertEqual(title.get_fontsize(), 16)
        self.assertEqual(title.get_ha(), "left")
        renderer = session.figure.canvas.get_renderer()
        self.assertGreater(title.get_window_extent(renderer).y0,
                           session.axes[0].get_window_extent(renderer).y1)
        session.close()
        self.assertEqual(dict(plt.rcParams), baseline)
        second = build_figure(spec)
        self.addCleanup(second.close)
        self.assertIsNot(second, session)

    def test_public_spec_validation_before_window_allocation(self):
        series = SeriesData([0, 1], [0, 1], "A")
        panel = PanelSpec((0, 0), (series,))
        spec = FigureSpec(1, 1, (panel,))
        bad = [replace(spec, rows=True), replace(spec, theme="missing"),
               replace(spec, panels=(panel, panel)),
               replace(spec, panels=(replace(panel, panel=(1, 0)),)),
               replace(spec, panels=(replace(panel, y_enum={float('nan'): "Bad"}),)),
               replace(spec, panels=(replace(panel, legend_loc="invalid"),)),
               replace(spec, panels=(replace(panel, series=(replace(series, yaxis="z"),)),)),
               replace(spec, panels=(replace(panel, series=(replace(series, tooltip=1),)),)),
               replace(spec, panels=(replace(panel, series=(replace(series, marker="!"),)),)),
               replace(spec, panels=(replace(panel, series=(replace(series, line_alpha=2),)),))]
        with patch("matplotlib.pyplot.figure") as create:
            for value in bad:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    build_figure(value)
            create.assert_not_called()

    def test_remove_series_fits_data_and_preserves_other_selection(self):
        fig = figure()
        ax = fig.subplot(1)
        ax.plot([0, 1], [0, 1], label="Keep", linestyle="None")
        ax.plot([0, 100], [100, 1000], label="Remove")
        ax.plot([0, 1], [2, 3], label="Keep")
        session = self.build(fig)
        axis = session.axes[0]
        self.click(session, axis, 1, 1000, key="shift")
        axis.set_xlim(-.1, 1.1)
        axis.set_ylim(-.1, 4)
        session.figure.canvas.draw()
        self.click(session, axis, 1, 3, key="shift")
        survivor = session.controllers[0].pinned_selections[-1]
        axis.set_xlim(-1000, 1000)
        axis.set_ylim(-2000, 2000)
        self.assertTrue(session.remove_series(session.series[1]))
        self.assertFalse(session.remove_series(session.series[1]))
        self.assertLess(axis.get_xlim()[1], 2)
        self.assertLess(axis.get_ylim()[1], 4)
        self.assertEqual(session.controllers[0].pinned_selections, (survivor,))
        self.assertEqual(survivor.series_idx, 1)
        send_key_event(session, "home")
        self.assertEqual(survivor.current_index, 0)
        self.assertEqual([t.get_text() for t in axis.get_legend().texts], ["Keep", "Keep"])
        for record in session.series:
            session.remove_series(record)
        self.assertEqual(axis.get_xlim(), (0, 1))
        self.assertEqual(axis.get_ylim(), (0, 1))
        self.assertIsNone(axis.get_legend())
        self.click(session, axis, .5, .5)
        send_mouse_event(session, "motion_notify_event", axis, .5, .5)
        self.assertFalse(session.controllers[0].cursors)

    def test_whole_line_mode_selects_segment_delete_and_exit(self):
        fig = figure()
        ax = fig.subplot(1)
        ax.plot([0, 10], [0, 10], label="Delete", marker=None)
        ax.plot([0, 1], [2, 2], label="Keep")
        session = self.build(fig)
        axis = session.axes[0]
        send_key_event(session, "l")
        self.assertTrue(session.series_selection_mode)
        self.click(session, axis, 5, 5)
        self.assertIs(session.selected_series, session.series[0])
        self.assertIsNone(session.controllers[0].active_selection)
        send_key_event(session, "delete")
        self.assertTrue(session.series[0].removed)
        self.assertIsNone(session.selected_series)
        self.assertLess(axis.get_xlim()[1], 2)
        send_key_event(session, "escape")
        self.assertFalse(session.series_selection_mode)
        self.click(session, axis, 0, 2)
        self.assertIsNotNone(session.controllers[0].active_selection)
        send_key_event(session, "delete")
        self.assertFalse(session.series[1].removed)

    def test_line_shortcut_with_mouse_position_preserves_scale_and_restores_keymap(self):
        original = list(plt.rcParams["keymap.yscale"])
        fig = figure()
        fig.subplot(1).plot([0, 1], [-1, 2])
        session = self.build(fig)
        axis = session.axes[0]
        limits = axis.get_ylim()
        self.assertNotIn("l", plt.rcParams["keymap.yscale"])
        x, y = axis.transData.transform((.5, .5))
        for expected in (True, False):
            event = KeyEvent("key_press_event", session.figure.canvas, key="l", x=x, y=y)
            session.figure.canvas.callbacks.process("key_press_event", event)
            self.assertEqual(session.series_selection_mode, expected)
            self.assertEqual(axis.get_yscale(), "linear")
            self.assertEqual(axis.get_ylim(), limits)
        session.close()
        self.assertEqual(plt.rcParams["keymap.yscale"], original)

    def test_dual_interaction_layer_draw_order_cleanup_and_restore(self):
        fig = figure(rows=2)
        panel = fig.subplot(1)
        panel.plot([0, 1, 2], [0, 2, 0], label="left")
        panel.plot([0, 1, 2], [100, 100, 200], label="right", yaxis="right")
        fig.subplot(2).plot([0, 1], [0, 1])
        session = self.build(fig)
        self.click(session, session.axes[0], 1, 2, key="shift")
        cursor = session.controllers[0].pinned_selections[0]
        legend = session.right_axes[1].get_legend()
        order = []
        artists = [(session.series[1].artists[0], "right data"),
                   (cursor.tooltip, "left tooltip"), (cursor.highlight, "left focus")]
        from contextlib import ExitStack
        with ExitStack() as stack:
            for artist, name in artists:
                draw = artist.draw
                def record(renderer, draw=draw, name=name):
                    order.append(name)
                    draw(renderer)
                stack.enter_context(patch.object(artist, "draw", record))
            session.figure.canvas.draw()
        self.assertEqual(order, ["right data", "left tooltip", "left focus"])
        self.assertGreater(legend.get_zorder(), cursor.highlight.get_zorder())
        self.assertGreater(legend.get_zorder(), session.controllers[0].hover_highlight.get_zorder())
        # Double click begins by removing the pin; restore must reattach to overlay.
        self.click(session, session.axes[0], 1, 2)
        self.click(session, session.axes[0], 1, 2, dblclick=True)
        self.assertIn(cursor, session.controllers[0].pinned_selections)
        self.assertIn(cursor.tooltip, session._layer.items)
        session.restore_layout()
        session.remove_series(session.series[0])
        self.assertNotIn(cursor.tooltip, session._layer.items)
        self.assertNotIn(legend, session._layer.items)
        self.assertEqual(len(session.right_axes[1].get_legend().texts), 1)

    def test_invalid_falsy_title_style_is_rejected(self):
        for value in (False, 0, "", [], {}):
            with self.subTest(value=value), patch("matplotlib.pyplot.figure") as create:
                with self.assertRaises(ValueError):
                    build_figure(FigureSpec(1, 1, (), suptitle_style=value))
                create.assert_not_called()

    def test_enum_clear_unmapped_values_and_callback_exception(self):
        fig = figure()
        ax = fig.subplot(1, y_enum={0: "off"})
        snapshot = fig.to_spec()
        for mapping in ({True: "bad"}, {float("inf"): "bad"}, {0: 1}):
            with self.assertRaises(ValueError):
                fig.subplot(1, y_enum=mapping)
        self.assertEqual(fig.to_spec(), snapshot)
        fig.subplot(1, y_enum={})
        received = []
        def callback(point):
            received.append(point.index)
            raise RuntimeError("business failure")
        ax.plot([0, 1], [0, 7], tooltip=callback)
        session = self.build(fig)
        send_mouse_event(session, "motion_notify_event", session.axes[0], 0, 0)
        self.assertEqual(received, [])
        with self.assertWarnsRegex(RuntimeWarning, "business failure"):
            self.click(session, session.axes[0], 1, 7, key="shift")
        self.assertEqual(received, [1])
        self.assertNotIn("off", session.controllers[0].pinned_selections[0].tooltip.get_text())
        self.assertIn("7", session.controllers[0].pinned_selections[0].tooltip.get_text())

    def test_mode_blank_click_and_escape_preserve_pins_and_layout(self):
        fig = figure(rows=2)
        fig.subplot(1).plot([0, 1, 2], [0, 1, 0])
        fig.subplot(2).plot([0, 1], [0, 1])
        session = self.build(fig)
        axis = session.axes[0]
        self.click(session, axis, 1, 1, key="shift")
        pin = session.controllers[0].pinned_selections[0]
        session.toggle_axes_maximized(axis)
        session.set_series_selection_mode(True)
        self.click(session, axis, .5, .5)
        self.assertIsNotNone(session.selected_series)
        self.click(session, axis, .2, .8)
        self.assertIsNone(session.selected_series)
        send_key_event(session, "delete")
        send_key_event(session, "right")
        self.assertFalse(session.series[0].removed)
        self.assertEqual(pin.current_index, 1)
        send_key_event(session, "escape")
        self.assertIs(session._dispatcher.layout.maximized_axes, axis)
        self.assertEqual(session.controllers[0].pinned_selections, (pin,))

    def test_handles_other_panels_disconnect_and_foreign_session(self):
        fig = figure(rows=2)
        fig.subplot(1).plot([0, 1], [0, 1], label="same")
        fig.subplot(1).plot([0, 2], [0, 3], label="same")
        fig.subplot(2).plot([0, 10], [-10, 10])
        session = self.build(fig)
        other_fig = figure()
        other_fig.subplot(1).plot([0, 1], [1, 0])
        other = self.build(other_fig)
        handles = session.series
        axis = session.axes[1]
        axis.set_xlim(2, 4)
        axis.set_ylim(-2, 2)
        with self.assertRaises(ValueError):
            session.remove_series(other.series[0])
        session.remove_series(handles[0])
        self.assertEqual(session.series, handles)
        self.assertEqual(axis.get_xlim(), (2, 4))
        self.assertEqual(axis.get_ylim(), (-2, 2))
        self.assertFalse(handles[1].removed)
        session.disconnect()
        self.assertFalse(session.remove_series(handles[1]))
        session.close()
        self.assertFalse(session.remove_series(handles[1]))

    def test_hidden_dual_tooltip_not_drawn_and_export_remains_valid(self):
        import io
        fig = figure(rows=2)
        fig.subplot(1, right_ylabel="right").plot([0, 1], [0, 1])
        fig.subplot(2).plot([0, 1], [0, 1])
        session = self.build(fig)
        self.click(session, session.axes[0], 0, 0)
        tooltip = session.controllers[0].active_selection.tooltip
        session.toggle_axes_maximized(session.axes[1])
        with patch.object(tooltip, "draw", wraps=tooltip.draw) as draw:
            session.figure.canvas.draw()
            draw.assert_not_called()
        session.restore_layout()
        with patch.object(tooltip, "draw", wraps=tooltip.draw) as draw:
            output = io.BytesIO()
            session.figure.savefig(output, format="png")
            self.assertTrue(output.getvalue().startswith(b"\x89PNG"))
            self.assertGreater(draw.call_count, 0)

    def test_dual_axis_removal_and_gap_selection(self):
        fig = figure()
        ax = fig.subplot(1)
        ax.plot([0, 1], [0, 1])
        ax.plot([0, 100], [1000, 2000], yaxis="right")
        session = self.build(fig)
        right = session.right_axes[1]
        session.set_series_selection_mode(True)
        self.click(session, right, 50, 1500)
        self.assertIs(session.selected_series, session.series[1])
        send_key_event(session, "backspace")
        self.assertEqual(right.get_ylim(), (0, 1))
        self.assertLess(session.axes[0].get_xlim()[1], 2)
        self.assertEqual(right.get_xlim(), session.axes[0].get_xlim())
        fig = figure()
        fig.subplot(1).plot([0, 1, 2], [0, np.nan, 2], marker=None)
        gap = self.build(fig)
        gap.set_series_selection_mode(True)
        self.click(gap, gap.axes[0], 1, 1)
        self.assertIsNone(gap.selected_series)


if __name__ == "__main__":
    unittest.main()

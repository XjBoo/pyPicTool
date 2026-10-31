"""Behavioral coverage for cross-window series copy and paste."""

import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import CloseEvent
from matplotlib.colors import to_rgba

from interactive_plotting import SeriesData, figure
from interactive_plotting import core, series_clipboard
from tests.test_public_api import (
    send_canvas_mouse_event, send_key_event, send_mouse_event,
)


class SessionTestCase(unittest.TestCase):
    def build(self, description):
        session = description.build()
        self.addCleanup(session.close)
        session.figure.canvas.draw()
        return session

    def click(self, session, axis, x, y, **kwargs):
        send_mouse_event(
            session, "button_press_event", axis, x, y, button=1, **kwargs,
        )
        send_mouse_event(
            session, "button_release_event", axis, x, y, button=1,
        )


class SeriesClipboardTests(unittest.TestCase):
    def setUp(self):
        series_clipboard.clear()
        self.addCleanup(series_clipboard.clear)

    def test_store_copies_arrays_and_preserves_metadata(self):
        calls = []

        def tooltip(context):
            calls.append(context.index)
            return "custom"

        source = SeriesData(
            np.array([0.0, 1.0, 2.0]),
            np.array([0.0, np.nan, 2.0]),
            "Signal",
            panel=(1, 0),
            color="#123456",
            line_color="#654321",
            line_alpha=0.4,
            marker="s",
            linestyle="--",
            linewidth=2.5,
            markersize=8,
            yaxis="right",
            tooltip=tooltip,
        )
        snapshot = series_clipboard.store_series(source)
        self.assertIs(series_clipboard.get_series(), snapshot)
        self.assertTrue(series_clipboard.is_active())
        self.assertIsNot(snapshot, source)
        self.assertIsNot(snapshot.frames, source.frames)
        self.assertIsNot(snapshot.values, source.values)
        self.assertFalse(snapshot.frames.flags.writeable)
        self.assertFalse(snapshot.values.flags.writeable)
        np.testing.assert_array_equal(snapshot.values, [0.0, np.nan, 2.0])
        self.assertEqual(snapshot.label, "Signal")
        self.assertEqual(snapshot.panel, (1, 0))
        self.assertEqual(snapshot.color, "#123456")
        self.assertEqual(snapshot.line_color, "#654321")
        self.assertEqual(snapshot.line_alpha, 0.4)
        self.assertEqual(snapshot.marker, "s")
        self.assertEqual(snapshot.linestyle, "--")
        self.assertEqual(snapshot.linewidth, 2.5)
        self.assertEqual(snapshot.markersize, 8)
        self.assertEqual(snapshot.yaxis, "right")
        self.assertIs(snapshot.tooltip, tooltip)

    def test_new_store_replaces_only_the_previous_snapshot(self):
        first = series_clipboard.store_series(SeriesData([0, 1], [0, 1], "First"))
        second = series_clipboard.store_series(SeriesData([0, 1], [1, 0], "Second"))
        self.assertIsNot(first, second)
        self.assertEqual(series_clipboard.get_series().label, "Second")
        self.assertTrue(series_clipboard.is_active())
        series_clipboard.disarm()
        self.assertFalse(series_clipboard.is_active())
        self.assertIs(series_clipboard.get_series(), second)
        self.assertTrue(series_clipboard.arm())
        self.assertTrue(series_clipboard.is_active())
        series_clipboard.clear()
        self.assertIsNone(series_clipboard.get_series())
        self.assertFalse(series_clipboard.is_active())

    def test_invalid_payload_is_rejected_without_replacing_snapshot(self):
        stored = series_clipboard.store_series(SeriesData([0, 1], [0, 1], "Keep"))
        with self.assertRaisesRegex(ValueError, "SeriesData"):
            series_clipboard.store_series(object())
        self.assertIs(series_clipboard.get_series(), stored)


class RuntimeSeriesAppendTests(SessionTestCase):
    def setUp(self):
        series_clipboard.clear()
        self.addCleanup(series_clipboard.clear)

    def controller_for(self, session, axis):
        return next(
            (controller for controller in session.controllers
             if controller.ax is axis),
            None,
        )

    def test_empty_panel_gets_controller_and_full_point_interaction(self):
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [0, 1], label="Existing")
        description.subplot(2)
        session = self.build(description)
        panel = session.axes[1]
        self.assertIsNone(self.controller_for(session, panel))
        record = session._append_series(
            SeriesData([0, 1, 2], [10, 20, 15], "Pasted"), panel,
        )
        self.assertIsNotNone(record)
        controller = self.controller_for(session, panel)
        self.assertIsNotNone(controller)
        self.assertEqual(controller.series_list[-1].label, "Pasted")
        self.click(session, panel, 1, 20)
        self.assertEqual(controller.active_selection.series_idx, 0)
        send_key_event(session, "right")
        self.assertEqual(controller.active_selection.current_index, 2)
        self.click(session, panel, 0, 10, key="shift")
        self.assertEqual(len(controller.pinned_selections), 1)
        self.assertEqual(
            [text.get_text() for text in panel.get_legend().texts],
            ["Pasted"],
        )

    def test_dynamic_right_axis_preserves_left_state_and_layout(self):
        description = figure(rows=2)
        first = description.subplot(1)
        first.plot([0, 1], [0, 1], label="Left")
        description.subplot(2).plot([0, 1], [1, 0], label="Other")
        session = self.build(description)
        primary = session.axes[0]
        left_controller = session.controllers[0]
        self.click(session, primary, 0, 0, key="shift")
        pin = left_controller.pinned_selections[0]
        item = SeriesData(
            [0, 50], [1500, 1000], "Right", yaxis="right",
            color="orange", line_color="purple", line_alpha=0.5,
        )
        record = session._append_series(item, primary)
        self.assertIsNotNone(record)
        right = session.right_axes[1]
        self.assertIs(record.axis, right)
        self.assertEqual(right.get_ylabel(), "")
        self.assertEqual(primary.get_xlim(), right.get_xlim())
        self.assertEqual(
            [text.get_text() for text in right.get_legend().texts],
            ["Left", "Right"],
        )
        self.assertIs(left_controller.pinned_selections[0], pin)
        self.assertEqual(pin.series_idx, 0)
        self.assertEqual(
            len([controller for controller in session.controllers
                 if controller.ax in (primary, right)]),
            2,
        )
        self.assertIn(right, left_controller.panel_axes)
        self.click(session, right, 0, 1500)
        self.assertIs(
            self.controller_for(session, right).active_selection.tooltip.axes,
            right,
        )
        left_position = tuple(primary.get_position().bounds)
        right_position = tuple(right.get_position().bounds)
        session.toggle_axes_maximized(primary)
        self.assertTrue(primary.get_visible() and right.get_visible())
        self.assertEqual(primary.get_position().bounds, right.get_position().bounds)
        session.restore_layout()
        self.assertEqual(tuple(primary.get_position().bounds), left_position)
        self.assertEqual(tuple(right.get_position().bounds), right_position)

    def test_new_controllers_use_overlay_when_panel_has_twin_axis(self):
        description = figure(rows=1, cols=2)
        description.subplot(1, right_ylabel="Pressure")
        description.subplot(2)
        session = self.build(description)
        self.assertIn(1, session.right_axes)
        session._append_series(
            SeriesData([0, 1], [10, 20], "Left first"),
            session.axes[0],
        )
        left_controller = self.controller_for(session, session.axes[0])
        self.assertFalse(left_controller._keep_axes)
        self.assertNotIn(left_controller.hover_highlight, session.axes[0].lines)

        session._append_series(
            SeriesData([0, 1], [100, 200], "Right", yaxis="right"),
            session.axes[1],
        )
        right_controller = self.controller_for(
            session, session.right_axes[2],
        )
        self.assertFalse(right_controller._keep_axes)
        session._append_series(
            SeriesData([0, 1], [1, 2], "Left second"),
            session.axes[1],
        )
        left_secondary = self.controller_for(session, session.axes[1])
        self.assertFalse(left_secondary._keep_axes)
        self.assertNotIn(left_secondary.hover_highlight, session.axes[1].lines)

    def test_dynamic_right_axis_created_while_panel_is_maximized(self):
        description = figure(rows=2)
        primary = description.subplot(1)
        primary.plot([0, 1], [0, 1], label="Left")
        description.subplot(2).plot([0, 1], [1, 0], label="Other")
        session = self.build(description)
        session.toggle_axes_maximized(session.axes[0])
        self.assertNotIn(1, session.right_axes)
        record = session._append_series(
            SeriesData([0, 1], [100, 200], "Right", yaxis="right"),
            session.axes[0],
        )
        self.assertIsNotNone(record)
        right = session.right_axes[1]
        self.assertTrue(right.get_visible())
        self.assertEqual(
            tuple(right.get_position().bounds),
            tuple(session.axes[0].get_position().bounds),
        )
        self.assertFalse(session.axes[1].get_visible())
        session.restore_layout()
        self.assertTrue(right.get_visible())
        self.assertEqual(
            tuple(right.get_position().bounds),
            tuple(session.axes[0].get_position().bounds),
        )
        self.assertTrue(session.axes[1].get_visible())

    def test_paste_preserves_fidelity_duplicates_and_source_independence(self):
        calls = []

        def tooltip(context):
            calls.append(context.index)
            return f"Copied {context.index}"

        source_description = figure()
        source_axis = source_description.subplot(1)
        source_axis.plot(
            [0, 1, 2, 3], [5, np.nan, 7, 8], label="Copied",
            color="#123456", marker="s", linestyle="--", linewidth=2.5,
            markersize=7, tooltip=tooltip,
        )
        source = self.build(source_description)
        series_clipboard.store_series(source.series[0].data)

        target_description = figure()
        target_axis = target_description.subplot(
            1, legend_loc="lower left", legend_frame_alpha=0.3,
        )
        target_axis.plot([0, 1], [0, 1], label="Existing")
        target = self.build(target_description)
        self.click(target, target.axes[0], 1, 1, key="shift")
        pin = target.controllers[0].pinned_selections[0]
        snapshot = series_clipboard.get_series()
        first = target._append_series(snapshot, target.axes[0])
        second = target._append_series(snapshot, target.axes[0])
        self.assertIsNot(first, second)
        self.assertIsNot(first.data, snapshot)
        self.assertIsNot(second.data, first.data)
        self.assertIs(first.data.tooltip, tooltip)
        np.testing.assert_array_equal(first.data.values, [5, np.nan, 7, 8])
        self.assertTrue(np.isnan(first.artists[0].get_ydata()[1]))
        self.assertEqual(to_rgba(first.artists[0].get_color()), to_rgba("#123456"))
        self.assertEqual(first.artists[0].get_linestyle(), "--")
        self.assertEqual(first.artists[0].get_linewidth(), 2.5)
        self.assertEqual(len(first.artists), 2)
        self.assertEqual(
            [text.get_text() for text in target.axes[0].get_legend().texts],
            ["Existing", "Copied", "Copied"],
        )
        legend = target.axes[0].get_legend()
        self.assertEqual(legend._loc, 3)
        self.assertAlmostEqual(legend.get_frame().get_alpha(), 0.3)
        self.assertIs(target.controllers[0].pinned_selections[0], pin)
        self.assertEqual(pin.series_idx, 0)
        self.assertEqual(target.controllers[0].series_list[-1].label, "Copied")
        self.assertGreater(target.axes[0].get_xlim()[1], 3)
        self.assertGreater(target.axes[0].get_ylim()[1], 8)
        self.click(target, target.axes[0], 3, 8)
        self.assertEqual(target.controllers[0].active_selection.tooltip.get_text(),
                         "Copied 3")
        copied_count = len(source.series)
        self.assertTrue(target.remove_series(second))
        self.assertEqual(len(source.series), copied_count)
        self.assertFalse(source.series[0].removed)
        self.assertFalse(first.removed)

    def test_unnamed_paste_and_global_panel_order(self):
        description = figure(rows=2)
        description.subplot(1).plot([0, 1], [0, 1], label="First")
        description.subplot(2).plot([0, 1], [2, 3], label="Second")
        session = self.build(description)
        other_xlim = session.axes[0].get_xlim()
        other_ylim = session.axes[0].get_ylim()
        unnamed = SeriesData([5, 6], [10, 11], "")
        session._append_series(unnamed, session.axes[1])
        self.assertEqual(session.axes[0].get_xlim(), other_xlim)
        self.assertEqual(session.axes[0].get_ylim(), other_ylim)
        session._append_series(SeriesData([2, 3], [4, 5], "Late"), session.axes[0])
        self.assertEqual(
            [(record.data.label, record.primary_axis) for record in session.series],
            [
                ("First", session.axes[0]),
                ("Late", session.axes[0]),
                ("Second", session.axes[1]),
                ("", session.axes[1]),
            ],
        )
        self.assertEqual(
            [text.get_text() for text in session.axes[1].get_legend().texts],
            ["Second"],
        )


class ManualAcceptanceSceneTests(unittest.TestCase):
    def test_scene_contains_same_figure_cross_window_empty_and_right_axis(self):
        from examples.copy_paste_manual import check_scene, make_sessions

        sessions = make_sessions()
        try:
            check_scene(sessions)
            self.assertEqual(len(sessions), 2)
        finally:
            for session in sessions:
                session.close()


class SeriesCopyPasteInteractionTests(SessionTestCase):
    def setUp(self):
        series_clipboard.clear()
        self.addCleanup(series_clipboard.clear)

    def make_source(self, label="Copied", values=None):
        description = figure()
        axis = description.subplot(1)
        axis.plot(
            [0, 1], [10, 20] if values is None else values,
            label=label, marker=None,
        )
        return self.build(description)

    def copy_via_shortcut(self, source, axis=None, point=(0, 10)):
        axis = axis or source.axes[0]
        send_key_event(source, "l")
        self.click(source, axis, *point)
        self.assertIsNotNone(source.selected_series)
        send_key_event(source, "ctrl+c")

    def test_visible_target_selection_cross_window_paste_and_escape(self):
        source = self.make_source()
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        first, second = target.axes
        self.copy_via_shortcut(source)
        selected = source.selected_series
        self.assertTrue(source.series_selection_mode)
        self.assertEqual(series_clipboard.get_series().label, "Copied")
        self.assertIs(source.selected_series, selected)
        self.assertTrue(selected.artists[0].get_visible())

        before = len(target.series)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), before)
        self.assertIsNone(target._paste_target_axis)

        send_mouse_event(target, "motion_notify_event", second, 0, 2)
        self.assertIsNone(target._paste_preview_axis)
        self.click(target, second, 0, 2)
        self.assertIsNone(target._paste_target_axis)
        active = target.controllers[1].active_selection
        self.assertIsNotNone(active)

        send_mouse_event(target, "motion_notify_event", second, .1, 2.9)
        self.assertIs(target._paste_preview_axis, second)
        preview = target._paste_preview_outlines[second]
        self.assertTrue(preview.get_visible())
        self.assertIsNone(target._paste_target_axis)
        send_canvas_mouse_event(target, "motion_notify_event", 1, 1)
        self.assertIsNone(target._paste_preview_axis)
        self.assertFalse(preview.get_visible())

        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        self.assertIsNone(target._paste_preview_axis)
        target_outline = target._paste_target_outlines[second]
        self.assertTrue(target_outline.get_visible())
        self.assertEqual(target_outline.get_linestyle(), "-")
        self.assertNotEqual(
            to_rgba(target_outline.get_edgecolor()), to_rgba("gold"),
        )
        self.assertEqual(preview.get_linestyle(), "--")
        self.assertLess(
            preview.get_linewidth(), target_outline.get_linewidth(),
        )
        self.assertIs(target.controllers[1].active_selection, active)

        send_mouse_event(target, "motion_notify_event", first, .5, .5)
        self.assertIs(target._paste_preview_axis, first)
        self.assertIs(target._paste_target_axis, second)
        send_canvas_mouse_event(target, "motion_notify_event", 1, 1)
        self.assertIsNone(target._paste_preview_axis)
        self.assertIs(target._paste_target_axis, second)

        send_key_event(target, "cmd+v")
        self.assertEqual(len(target.series), before + 1)
        self.assertEqual(target.series[-1].data.label, "Copied")
        self.assertIs(target.series[-1].primary_axis, second)
        self.assertIs(target._paste_target_axis, second)
        self.assertEqual(
            [text.get_text() for text in second.get_legend().texts],
            ["Second", "Copied"],
        )
        self.assertIs(target.controllers[1].active_selection, active)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), before + 2)
        self.assertEqual(
            [text.get_text() for text in second.get_legend().texts],
            ["Second", "Copied", "Copied"],
        )
        self.assertIs(target.controllers[1].active_selection, active)

        target.toggle_axes_maximized(second)
        send_key_event(target, "escape")
        self.assertIsNone(target._paste_target_axis)
        self.assertFalse(target_outline.get_visible())
        self.assertIs(target._dispatcher.layout.maximized_axes, second)
        self.assertIsNotNone(series_clipboard.get_series())
        self.assertFalse(series_clipboard.is_active())
        self.assertFalse(source.series_selection_mode)
        self.assertIs(target.controllers[1].active_selection, active)
        target.restore_layout()

        after_escape = len(target.series)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), after_escape)
        send_key_event(target, "l")
        self.assertTrue(series_clipboard.is_active())
        send_mouse_event(target, "motion_notify_event", first, .1, .9)
        self.assertIs(target._paste_preview_axis, first)
        self.click(target, first, .1, .9)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), after_escape + 1)
        self.assertIs(target._paste_target_axis, first)

    def test_same_figure_cross_subplot_paste_while_selection_mode_stays_on(self):
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [10, 20], label="Same Figure")
        description.subplot(2)
        session = self.build(description)
        source_panel, target_panel = session.axes
        send_key_event(session, "l")
        self.click(session, source_panel, 0, 10)
        send_key_event(session, "ctrl+c")
        source_record = session.selected_series
        self.assertEqual(series_clipboard.get_series().label, "Same Figure")
        self.assertTrue(session.series_selection_mode)
        self.assertTrue(series_clipboard.is_active())

        send_mouse_event(session, "motion_notify_event", source_panel, .5, 15)
        self.assertIsNone(session._paste_preview_axis)
        self.click(session, source_panel, .5, 15)
        self.assertIs(session.selected_series, source_record)
        self.assertIsNone(session._paste_target_axis)

        send_mouse_event(session, "motion_notify_event", target_panel, .5, .5)
        self.assertIs(session._paste_preview_axis, target_panel)
        self.assertIsNone(session._paste_target_axis)
        self.click(session, target_panel, .5, .5)
        self.assertIs(session._paste_target_axis, target_panel)
        self.assertIsNone(session.selected_series)
        send_key_event(session, "ctrl+v")
        pasted = session.series[-1]
        self.assertIs(pasted.primary_axis, target_panel)
        self.assertEqual(pasted.data.label, "Same Figure")
        self.assertFalse(source_record.removed)
        self.assertIs(source_record.primary_axis, source_panel)
        self.assertTrue(session.series_selection_mode)
        self.assertIs(session._paste_target_axis, target_panel)
        self.assertEqual(
            [text.get_text() for text in target_panel.get_legend().texts],
            ["Same Figure"],
        )
        send_key_event(session, "escape")
        self.assertFalse(session.series_selection_mode)
        self.assertIsNone(session._paste_target_axis)
        self.assertFalse(series_clipboard.is_active())
        controller = next(
            controller for controller in session.controllers
            if controller.ax is target_panel
        )
        self.click(session, target_panel, 0, 10)
        self.assertIsNotNone(controller.active_selection)

    def test_selection_mode_tooltip_is_not_a_blank_paste_target(self):
        description = figure()
        description.subplot(1).plot([0, 1, 2], [0, 0, 0], label="Line")
        session = self.build(description)
        axis = session.axes[0]
        self.click(session, axis, 0, 0, key="shift")
        pin = session.controllers[0].pinned_selections[0]
        send_key_event(session, "l")
        self.click(session, axis, 1, 0)
        send_key_event(session, "ctrl+c")
        session.figure.canvas.draw()
        tooltip = pin.tooltip
        self.assertTrue(tooltip.get_visible())
        bbox = tooltip.get_window_extent(session.figure.canvas.get_renderer())
        center = ((bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2)
        send_canvas_mouse_event(session, "motion_notify_event", *center)
        self.assertIsNone(session._paste_preview_axis)
        send_canvas_mouse_event(
            session, "button_press_event", *center, button=1,
        )
        send_canvas_mouse_event(
            session, "button_release_event", *center, button=1,
        )
        self.assertIsNone(session._paste_target_axis)
        self.assertIsNone(session.selected_series)

    def test_blank_click_moves_target_between_panels(self):
        source = self.make_source()
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        first, second = target.axes
        self.copy_via_shortcut(source)
        self.click(target, first, .1, .9)
        self.assertIs(target._paste_target_axis, first)
        first_outline = target._paste_target_outlines[first]
        self.assertTrue(first_outline.get_visible())
        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        self.assertFalse(first_outline.get_visible())
        self.assertTrue(target._paste_target_outlines[second].get_visible())
        before = len(target.series)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), before + 1)
        self.assertIs(target.series[-1].primary_axis, second)

    def test_double_click_maximizes_without_confirming_paste_target(self):
        source = self.make_source()
        self.copy_via_shortcut(source)
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        first = target.axes[0]
        self.click(target, first, .1, .9, dblclick=True)
        self.assertIsNone(target._paste_target_axis)
        self.assertIs(target._dispatcher.layout.maximized_axes, first)
        target.restore_layout()

    def test_legend_click_in_selection_mode_does_not_confirm_target(self):
        description = figure()
        subplot = description.subplot(1)
        subplot.plot([0, 1], [0, 1], label="First")
        subplot.plot([0, 1], [1, 0], label="Second")
        session = self.build(description)
        axis = session.axes[0]
        send_key_event(session, "l")
        self.click(session, axis, 0, 0)
        send_key_event(session, "ctrl+c")
        legend = axis.get_legend()
        session.figure.canvas.draw()
        renderer = session.figure.canvas.get_renderer()
        bbox = legend.texts[1].get_window_extent(renderer)
        send_canvas_mouse_event(
            session, "button_press_event",
            (bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2, button=1,
        )
        self.assertIs(session.selected_series, session.series[1])
        self.assertIsNone(session._paste_target_axis)

    def test_normal_escape_is_local_when_no_selection_mode_remains(self):
        source = self.make_source()
        self.copy_via_shortcut(source)
        source.close()
        self.assertTrue(series_clipboard.is_active())
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        second = target.axes[1]
        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        send_key_event(target, "escape")
        self.assertIsNone(target._paste_target_axis)
        self.assertTrue(series_clipboard.is_active())
        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        before = len(target.series)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), before + 1)

    def test_l_exit_in_second_window_keeps_session_while_source_mode_remains(self):
        source = self.make_source()
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        self.copy_via_shortcut(source)
        send_key_event(target, "l")
        self.assertTrue(target.series_selection_mode)
        send_key_event(target, "l")
        self.assertFalse(target.series_selection_mode)
        self.assertTrue(source.series_selection_mode)
        self.assertTrue(series_clipboard.is_active())
        send_mouse_event(target, "motion_notify_event", target.axes[1], .1, 2.9)
        self.assertIs(target._paste_preview_axis, target.axes[1])
        send_key_event(target, "escape")
        self.assertFalse(source.series_selection_mode)
        self.assertFalse(series_clipboard.is_active())

    def test_escape_in_target_exits_source_selection_mode_and_disarms(self):
        source = self.make_source()
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        second = target.axes[1]
        self.copy_via_shortcut(source)
        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        send_key_event(target, "ctrl+v")
        pasted_count = len(target.series)
        self.assertFalse(source.selected_series.removed)

        send_key_event(target, "escape")
        self.assertFalse(source.series_selection_mode)
        self.assertIsNone(source.selected_series)
        self.assertIsNone(target._paste_target_axis)
        self.assertFalse(series_clipboard.is_active())
        self.assertIsNotNone(series_clipboard.get_series())
        self.assertEqual(len(target.series), pasted_count)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), pasted_count)

        send_key_event(target, "l")
        self.assertTrue(series_clipboard.is_active())
        self.assertTrue(target.series_selection_mode)
        self.assertFalse(source.series_selection_mode)
        send_mouse_event(target, "motion_notify_event", second, .1, 2.9)
        self.assertIs(target._paste_preview_axis, second)
        self.click(target, second, .1, 2.9)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), pasted_count + 1)

    def test_source_escape_disarms_all_windows_and_reenter_rearms(self):
        source = self.make_source()
        target_description = figure(rows=1, cols=2)
        target_description.subplot(1).plot([0, 1], [0, 1], label="First")
        target_description.subplot(2).plot([0, 1], [2, 3], label="Second")
        target = self.build(target_description)
        second = target.axes[1]
        self.copy_via_shortcut(source)
        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        target_outline = target._paste_target_outlines[second]
        self.assertTrue(target_outline.get_visible())

        send_key_event(source, "escape")
        self.assertFalse(source.series_selection_mode)
        self.assertFalse(series_clipboard.is_active())
        self.assertIsNotNone(series_clipboard.get_series())
        self.assertIsNone(target._paste_target_axis)
        self.assertFalse(target_outline.get_visible())
        before = len(target.series)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), before)
        send_mouse_event(target, "motion_notify_event", second, .1, 2.9)
        self.assertIsNone(target._paste_preview_axis)

        send_key_event(target, "l")
        self.assertTrue(series_clipboard.is_active())
        self.assertTrue(target.series_selection_mode)
        send_mouse_event(target, "motion_notify_event", second, .1, 2.9)
        self.assertIs(target._paste_preview_axis, second)
        self.click(target, second, .1, 2.9)
        self.assertIs(target._paste_target_axis, second)
        send_key_event(target, "ctrl+v")
        self.assertEqual(len(target.series), before + 1)
        self.assertEqual(target.series[-1].data.label, "Copied")

    def test_copy_requires_selection_and_replaces_snapshot(self):
        description = figure()
        subplot = description.subplot(1)
        subplot.plot([0, 1], [0, 1], label="A", marker=None)
        subplot.plot([0, 1], [10, 11], label="B", marker=None)
        source = self.build(description)
        axis = source.axes[0]
        send_key_event(source, "l")
        self.click(source, axis, 0, 0)
        send_key_event(source, "ctrl+c")
        first = series_clipboard.get_series()
        self.assertEqual(first.label, "A")
        send_key_event(source, "escape")
        send_key_event(source, "ctrl+c")
        self.assertIs(series_clipboard.get_series(), first)
        send_key_event(source, "l")
        self.click(source, axis, 0, 10)
        self.assertEqual(source.selected_series.data.label, "B")
        send_key_event(source, "cmd+c")
        self.assertEqual(series_clipboard.get_series().label, "B")
        self.assertIsNot(series_clipboard.get_series(), first)

    def test_single_panel_default_works_after_source_window_closes(self):
        source = self.make_source(label="Detached")
        send_key_event(source, "l")
        self.click(source, source.axes[0], 0, 10)
        send_key_event(source, "cmd+c")
        source.close()
        self.assertTrue(series_clipboard.is_active())
        target_description = figure()
        target_description.subplot(1).plot([0, 1], [0, 1], label="Target")
        target = self.build(target_description)
        send_key_event(target, "cmd+v")
        self.assertEqual(
            [record.data.label for record in target.series],
            ["Target", "Detached"],
        )
        self.assertIs(target._paste_target_axis, target.axes[0])
        self.assertTrue(
            target._paste_target_outlines[target.axes[0]].get_visible()
        )

    def test_empty_panel_can_be_confirmed_and_receive_first_curve(self):
        series_clipboard.store_series(
            SeriesData([0, 1, 2], [10, 20, 15], "First Pasted")
        )
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [0, 1], label="Existing")
        description.subplot(2)
        target = self.build(description)
        empty = target.axes[1]
        send_mouse_event(target, "motion_notify_event", empty, .5, .5)
        self.assertIs(target._paste_preview_axis, empty)
        self.click(target, empty, .5, .5)
        self.assertIs(target._paste_target_axis, empty)
        send_key_event(target, "ctrl+v")
        controller = next(
            controller for controller in target.controllers
            if controller.ax is empty
        )
        self.assertEqual(controller.series_list[-1].label, "First Pasted")
        self.assertEqual(
            [text.get_text() for text in empty.get_legend().texts],
            ["First Pasted"],
        )
        self.click(target, empty, 1, 20)
        self.assertIsNotNone(controller.active_selection)
        self.assertIs(target._paste_target_axis, empty)

    def test_close_event_cleans_target_state_and_live_session_registry(self):
        series_clipboard.store_series(
            SeriesData([0, 1], [10, 20], "Waiting")
        )
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [0, 1], label="One")
        description.subplot(2).plot([0, 1], [1, 0], label="Two")
        target = self.build(description)
        self.click(target, target.axes[0], .1, .9)
        self.assertIs(target._paste_target_axis, target.axes[0])
        self.assertIn(id(target), core._LIVE_SESSIONS)
        target.figure.canvas.callbacks.process(
            "close_event", CloseEvent("close_event", target.figure.canvas),
        )
        self.assertFalse(target._dispatcher.connected)
        self.assertIsNone(target._paste_target_axis)
        self.assertIsNone(target._paste_preview_axis)
        self.assertEqual(target._paste_target_outlines, {})
        self.assertEqual(target._paste_preview_outlines, {})
        self.assertNotIn(id(target), core._LIVE_SESSIONS)
        self.assertTrue(series_clipboard.is_active())
        target.close()

    def test_disconnected_target_rejects_paste_and_cleans_highlights(self):
        series_clipboard.store_series(
            SeriesData([0, 1], [10, 20], "Waiting")
        )
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [0, 1], label="One")
        description.subplot(2).plot([0, 1], [1, 0], label="Two")
        target = self.build(description)
        self.click(target, target.axes[0], 0, 0)
        before = len(target.series)
        target.close()
        self.assertIsNone(target._paste_clipboard_series())
        self.assertEqual(len(target.series), before)
        self.assertIsNone(target._paste_target_axis)
        self.assertEqual(target._paste_target_outlines, {})
        self.assertIsNotNone(series_clipboard.get_series())

    def test_no_clipboard_and_navigation_or_drag_prevent_target_changes(self):
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [0, 1], label="One")
        description.subplot(2).plot([0, 1], [1, 0], label="Two")
        session = self.build(description)
        self.click(session, session.axes[0], 0, 0)
        self.assertIsNone(session._paste_target_axis)
        self.assertEqual(session._paste_target_outlines, {})
        self.assertEqual(session._paste_preview_outlines, {})

        series_clipboard.store_series(SeriesData([0, 1], [5, 6], "Stored"))
        with patch.object(
            session._dispatcher, "_toolbar_is_active", return_value=True,
        ):
            send_mouse_event(session, "motion_notify_event", session.axes[0], 0, 0)
            self.assertIsNone(session._paste_preview_axis)
            self.click(session, session.axes[0], 0, 0)
            self.assertIsNone(session._paste_target_axis)
            before = len(session.series)
            send_key_event(session, "ctrl+v")
            self.assertEqual(len(session.series), before)

        session.figure.canvas.draw()
        tooltip = session.controllers[0].active_selection.tooltip
        bbox = tooltip.get_window_extent(session.figure.canvas.get_renderer())
        send_canvas_mouse_event(
            session, "button_press_event", (bbox.x0 + bbox.x1) / 2,
            (bbox.y0 + bbox.y1) / 2, button=1,
        )
        self.assertTrue(session.controllers[0].is_dragging)
        before = len(session.series)
        send_key_event(session, "ctrl+v")
        self.assertEqual(len(session.series), before)
        send_canvas_mouse_event(
            session, "button_release_event", (bbox.x0 + bbox.x1) / 2,
            (bbox.y0 + bbox.y1) / 2, button=1,
        )
        self.assertFalse(session.controllers[0].is_dragging)

    def test_hidden_unused_cell_is_not_a_preview_target(self):
        series_clipboard.store_series(SeriesData([0, 1], [0, 1], "Stored"))
        description = figure(rows=1, cols=2)
        description.subplot(1).plot([0, 1], [0, 1], label="Visible")
        session = self.build(description)
        hidden = session.axes[1]
        self.assertFalse(hidden.get_visible())
        renderer = session.figure.canvas.get_renderer()
        bbox = hidden.get_window_extent(renderer)
        send_canvas_mouse_event(
            session, "motion_notify_event",
            (bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2,
        )
        self.assertIsNone(session._paste_preview_axis)

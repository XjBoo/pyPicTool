"""Behavior checks for presentation compatibility, independent of exact pixels."""
import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgba
from interactive_plotting import SeriesData, create_interactive_plot, make_demo_series
from tests.test_public_api import send_mouse_event, send_key_event


class PresentationTests(unittest.TestCase):
    def make_session(self, series):
        session = create_interactive_plot(series)
        self.addCleanup(session.close)
        return session

    def test_colors_explicit_overrides_and_missing_data_survive_styling(self):
        series = [
            SeriesData([0, 1, 2], [0, np.nan, 2], 'matched', color='purple'),
            SeriesData([0, 1, 2], [2, 1, 0], 'override', color='teal',
                       line_color='orange', line_alpha=0.35),
        ]
        session = self.make_session(series)
        axis = session.axes[0]
        lines = {line.get_label(): line for line in axis.lines}
        self.assertEqual(to_rgba(lines['matched'].get_color()), to_rgba('purple'))
        self.assertEqual(to_rgba(lines['override'].get_color()), to_rgba('orange'))
        self.assertEqual(lines['override'].get_alpha(), 0.35)
        np.testing.assert_array_equal(lines['matched'].get_ydata(), series[0].values)
        self.assertEqual(len(axis.collections[0].get_offsets()), 2)
        legend = axis.get_legend()
        for handle, label in zip(legend.legend_handles, legend.get_texts()):
            self.assertEqual(handle.get_color(), lines[label.get_text()].get_color())

    def test_font_fallback_and_late_tooltip_leave_global_defaults_unchanged(self):
        before = dict(plt.rcParams)
        with patch('interactive_plotting.style.font_manager.fontManager.ttflist', []):
            session = self.make_session([
                SeriesData([0, 1, 2], [-1, 0, 1], 'fallback', panel_title='Fallback')
            ])
        session.figure.canvas.draw()
        axis = session.axes[0]
        send_mouse_event(session, 'button_press_event', axis, 1, 0, button=1)
        tooltip = session.controllers[0].active_selection.tooltip
        self.assertEqual(tooltip.get_fontfamily(), ['DejaVu Sans'])
        self.assertEqual(tooltip.get_bbox_patch().get_alpha(), 1)
        session.close()
        self.assertEqual(dict(plt.rcParams), before)

    def test_layout_titles_and_scaled_hit_testing(self):
        series = make_demo_series(seed=42)
        session = self.make_session(series)
        session.figure.set_dpi(150)
        session.figure.canvas.draw()
        renderer = session.figure.canvas.get_renderer()
        for axis in session.axes:
            self.assertTrue(axis.get_title())
            self.assertGreater(axis.title.get_fontsize(), axis.get_xticklabels()[0].get_fontsize())
            self.assertFalse(axis.title.get_window_extent(renderer).overlaps(
                axis.get_legend().get_window_extent(renderer)))
        before = [axis.get_position().bounds for axis in session.axes]
        axis = session.axes[0]
        send_mouse_event(session, 'button_press_event', axis,
                         series[0].frames[50], series[0].values[50], button=1)
        selected = session.controllers[0].active_selection
        self.assertIsNotNone(selected)
        session.toggle_axes_maximized(axis)
        send_key_event(session, 'right')
        self.assertEqual(selected.current_index, 51)
        session.restore_layout()
        np.testing.assert_allclose([a.get_position().bounds for a in session.axes], before)
        self.assertTrue(selected.tooltip.get_visible())

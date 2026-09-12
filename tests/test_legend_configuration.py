"""Public legend configuration and rendered placement regressions."""
import unittest
from dataclasses import replace
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
import numpy as np

from interactive_plotting import figure, build_figure


class LegendConfigurationTests(unittest.TestCase):
    def build(self, loc='best_corner', alpha=.3, dual=False, cols=1):
        builder = figure(figsize=(6, 4), cols=cols)
        panel = builder.subplot(1, legend_loc=loc, legend_frame_alpha=alpha,
                                right_ylabel='Right' if dual else None)
        panel.plot([0, 1], [.5, .5], label='Signal', marker=None)
        if dual:
            panel.plot([0, 1], [50, 50], label='Right signal', marker=None, yaxis='right')
        if cols > 1:
            builder.subplot(2).plot([0, 1], [0, 1], label='Other panel')
        session = builder.build()
        self.addCleanup(session.close)
        axis = session.axes[0]
        axis.set(xlim=(0, 1), ylim=(0, 1))
        if dual:
            session.right_axes[1].set_ylim(0, 100)
        session.figure.canvas.draw()
        return session

    def legend(self, session):
        return (session.right_axes.get(1) or session.axes[0]).get_legend()

    def event(self, session, name, x, y):
        canvas = session.figure.canvas
        canvas.callbacks.process(name, MouseEvent(name, canvas, x, y, button=1))

    def test_validation_snapshot_and_frozen_builder(self):
        builder = figure(cols=2)
        builder.subplot(1, legend_frame_alpha=.2).plot([0, 1], [0, 1], label='A')
        builder.subplot(2, legend_loc='best_corner', legend_frame_alpha=0)
        builder.subplot(1, legend_frame_alpha=None)
        before = builder.to_spec()
        for value in (True, '0.5', np.nan, np.inf, -1, 1.1):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'legend_frame_alpha'):
                builder.subplot(1, title='wrong', legend_frame_alpha=value)
            self.assertEqual(builder.to_spec(), before)
        for value in (None, True, '0.5', np.nan, np.inf, -.1, 1.1):
            bad = replace(before, panels=(replace(before.panels[0], legend_frame_alpha=value),))
            with patch('matplotlib.pyplot.figure') as allocate:
                with self.assertRaisesRegex(ValueError, 'legend_frame_alpha'):
                    build_figure(bad)
                allocate.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'legend_loc'):
            builder.subplot(1, legend_loc='wrong')
        session = build_figure(before)
        self.addCleanup(session.close)
        self.assertEqual(session.axes[0].get_legend().get_frame().get_alpha(), .2)
        self.assertEqual(before.panels[1].legend_frame_alpha, 0)
        session2 = builder.build()
        self.addCleanup(session2.close)
        with self.assertRaises(RuntimeError):
            builder.subplot(1, legend_frame_alpha=.7)

    def test_fixed_positions_defaults_and_best(self):
        for loc, code in [('upper right', 1), ('upper left', 2), ('lower left', 3), ('lower right', 4), ('best', 0)]:
            session = self.build(loc)
            self.assertEqual(self.legend(session)._loc, code)
        builder = figure()
        builder.subplot(1).plot([0, 1], [0, 1], label='A')
        session = builder.build()
        self.addCleanup(session.close)
        self.assertEqual(self.legend(session)._loc, 1)
        self.assertEqual(self.legend(session).get_frame().get_alpha(), .95)

    def test_alpha_render_and_rebuild(self):
        rasters = []
        for alpha in (0, .3, 1):
            builder = figure()
            panel = builder.subplot(1, legend_frame_alpha=alpha)
            panel.plot([0, 1], [0, 1], label='A')
            panel.plot([0, 1], [1, 0], label='B')
            session = builder.build()
            self.addCleanup(session.close)
            session.figure.canvas.draw()
            legend = self.legend(session)
            self.assertEqual(legend.get_frame().get_alpha(), alpha)
            self.assertEqual(legend.texts[0].get_alpha(), None)
            self.assertEqual(legend.legend_handles[0].get_alpha(), session.series[0].data.line_alpha)
            rasters.append(np.asarray(session.figure.canvas.buffer_rgba()).copy())
            session.remove_series(session.series[0])
            self.assertEqual(self.legend(session).get_frame().get_alpha(), alpha)
            session.remove_series(session.series[1])
            self.assertIsNone(self.legend(session))
        self.assertFalse(np.array_equal(rasters[0], rasters[1]))
        self.assertFalse(np.array_equal(rasters[1], rasters[2]))

    def test_unique_free_corner_and_sparse_crossing(self):
        # Horizontal segments cross top corners without vertices in either box;
        # a short segment crosses the bottom left, leaving bottom right free.
        builder = figure()
        panel = builder.subplot(1, legend_loc='best_corner')
        panel.plot([-.5, 1.5, 2, -.5, .3], [.95, .95, np.nan, .05, .05], label='A', marker=None)
        session = builder.build()
        self.addCleanup(session.close)
        session.axes[0].set(xlim=(0, 1), ylim=(0, 1))
        session.figure.canvas.draw()
        self.assertEqual(self.legend(session)._loc, 4)
        # Break the top line with NaN: upper right now wins only if the
        # previous bottom-right is made occupied.
        session.series[0].artists[0].set_data([-.5, np.nan, 1.5, np.nan, -.5, 1.5], [.95, np.nan, .95, np.nan, .05, .05])
        session.figure.canvas.draw()
        self.assertEqual(self.legend(session)._loc, 1)

    def test_scatter_dual_unnamed_hidden_and_decorations(self):
        builder = figure()
        panel = builder.subplot(1, legend_loc='best_corner')
        panel.plot([0, 1], [.5, .5], label='A', marker=None)
        panel.plot([.95, .05, .05], [95, 95, 5], yaxis='right', linestyle='None', markersize=10)
        session = builder.build()
        self.addCleanup(session.close)
        session.axes[0].set(xlim=(0, 1), ylim=(0, 1))
        session.right_axes[1].set_ylim(0, 100)
        canvas = session.figure.canvas
        canvas.draw()
        legend = self.legend(session)
        self.assertEqual(legend._loc, 4)
        self.assertEqual(len(legend.texts), 1)
        session.right_axes[1].text(.9, 5, 'Decoration')
        with patch.object(legend, '_score_corners', wraps=legend._score_corners) as score:
            canvas.draw()
            score.assert_not_called()
        for artist in session.series[1].artists:
            artist.set_visible(False)
        canvas.draw()
        self.assertEqual(legend._loc, 4)  # same score retains current corner
        self.assertTrue(np.all(legend._score_corners([
            matplotlib.transforms.Bbox.from_bounds(.01, .01, 1, 1)] * 4, canvas.get_renderer()) == 0))

    def test_view_cache_and_hover_raster(self):
        session = self.build(dual=True, cols=2)
        legend = self.legend(session)
        canvas = session.figure.canvas
        for mutation in (lambda: session.axes[0].set_xlim(-1, 2),
                         lambda: session.right_axes[1].set_ylim(-50, 150),
                         lambda: session.figure.set_size_inches(8, 5),
                         lambda: session.figure.set_dpi(120),
                         lambda: session.toggle_axes_maximized(session.axes[0]),
                         session.restore_layout):
            old_key = legend._corner_key
            with patch.object(legend, '_score_corners', wraps=legend._score_corners) as score:
                mutation()
                canvas.draw()
                self.assertGreater(score.call_count, 0, mutation.__code__.co_firstlineno)
                self.assertNotEqual(legend._corner_key, old_key)
        with patch.object(legend, '_score_corners', wraps=legend._score_corners) as score:
            for x, y in [(0, .5), (1, .5), (0, 0)]:
                px, py = session.axes[0].transData.transform((x, y))
                self.event(session, 'motion_notify_event', px, py)
                raster = np.asarray(canvas.buffer_rgba()).copy()
                canvas.draw()
                np.testing.assert_array_equal(raster, np.asarray(canvas.buffer_rgba()))
            score.assert_not_called()
        session.disconnect()
        self.assertFalse(legend._corner_auto)
        self.assertEqual(legend._data_records, ())

    def test_view_change_relocates_legend(self):
        builder = figure()
        panel = builder.subplot(1, legend_loc='best_corner')
        panel.plot([-.5, 1.5, 2, -.5, .3],
                   [.95, .95, np.nan, .05, .05], label='A', marker=None)
        session = builder.build()
        self.addCleanup(session.close)
        axis = session.axes[0]
        axis.set(xlim=(0, 1), ylim=(0, 1))
        session.figure.canvas.draw()
        self.assertEqual(self.legend(session)._loc, 4)
        axis.set_ylim(0, 20)
        session.figure.canvas.draw()
        self.assertEqual(self.legend(session)._loc, 1)

    def test_click_drag_and_rebuild(self):
        builder = figure()
        panel = builder.subplot(1, legend_loc='best_corner', legend_frame_alpha=0)
        for name in ('A', 'B'):
            panel.plot([0, 1], [.5, .5], label=name)
        session = builder.build()
        self.addCleanup(session.close)
        canvas = session.figure.canvas
        canvas.draw()
        legend = self.legend(session)
        box = legend.get_window_extent()
        x, y = box.x0 + box.width / 2, box.y0 + box.height / 2
        self.event(session, 'button_press_event', x, y)
        self.event(session, 'button_release_event', x, y)
        self.assertTrue(legend._corner_auto)
        self.event(session, 'button_press_event', x, y)
        self.event(session, 'motion_notify_event', x - 60, y - 35)
        self.event(session, 'button_release_event', x - 60, y - 35)
        self.assertFalse(legend._corner_auto)
        manual = legend._loc
        self.assertIsInstance(manual, tuple)
        session.axes[0].set_xlim(-1, 3)
        session.figure.set_size_inches(8, 5)
        canvas.draw()
        self.assertEqual(legend._loc, manual)
        session.set_series_selection_mode(True)
        self.assertFalse(legend.get_draggable())
        text = legend.texts[0].get_window_extent()
        self.event(session, 'button_press_event', text.x0 + text.width / 2, text.y0 + text.height / 2)
        self.assertIs(session.selected_series, session.series[0])
        session.remove_series(session.series[0])
        self.assertEqual(self.legend(session)._loc, manual)
        self.assertEqual(self.legend(session).get_frame().get_alpha(), 0)

    def test_all_occupied_scores_and_oversized_legend(self):
        session = self.build()
        legend = self.legend(session)
        canvas = session.figure.canvas
        renderer = canvas.get_renderer()
        with patch.object(legend, '_score_corners', return_value=np.array([4, 3, 2, 1])):
            legend._corner_key = None
            canvas.draw()
            self.assertEqual(legend._loc, 4)
        legend.texts[0].set_text('Very long legend ' * 30)
        canvas.draw()
        self.assertIn(legend._loc, (1, 2, 3, 4))
        self.assertGreater(legend.get_window_extent(renderer).width, session.axes[0].bbox.width)

    def test_unnamed_only_has_no_legend(self):
        builder = figure()
        builder.subplot(1, legend_loc='best_corner').plot([0, 1], [0, 1])
        session = builder.build()
        self.addCleanup(session.close)
        self.assertIsNone(self.legend(session))

"""Screen-distance and raster regressions for the interactive overlay."""
import io
import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import MouseEvent, LocationEvent
from PIL import Image

from interactive_plotting import SeriesData, create_interactive_plot, figure


class HoverRenderingTests(unittest.TestCase):
    def setUp(self):
        self.session = create_interactive_plot([
            SeriesData([0, 1, 2], [0, 1, 0], 'red', color='red'),
            SeriesData([0, 1, 2], [2, 3, 2], 'blue', color='blue', panel=(0, 1)),
        ])
        self.canvas = self.session.figure.canvas
        self.canvas.draw()
        self.addCleanup(self.session.close)

    def motion(self, x=1, y=1, panel=0, offset=0, name='motion_notify_event'):
        axis = self.session.axes[panel]
        px, py = axis.transData.transform((x, y))
        event = MouseEvent(name, self.canvas, px, py, button=1 if name == 'button_press_event' else None)
        event.x, event.y, event.inaxes = px + offset, py, axis
        self.canvas.callbacks.process(name, event)

    def assert_matches_full_draw(self):
        optimized = np.asarray(self.canvas.buffer_rgba()).copy()
        self.canvas.draw()
        np.testing.assert_array_equal(optimized, np.asarray(self.canvas.buffer_rgba()))

    def test_logical_radius_and_runtime_ratio(self):
        for ratio in (1, 2, 1):
            self.canvas._set_device_pixel_ratio(ratio)
            self.canvas.draw()
            for offset, hit in ((9, True), (10, True), (11, False)):
                with self.subTest(ratio=ratio, offset=offset):
                    self.motion(offset=offset * ratio)
                    self.assertEqual(self.session.controllers[0].hover_highlight.get_visible(), hit)
                    result = self.session.controllers[0].active_selection
                    self.motion(offset=offset * ratio, name='button_press_event')
                    self.assertEqual(self.session.controllers[0].active_selection is not result, hit)
                    self.session.controllers[0].clear_active()
                    self.canvas.callbacks.process(
                        "button_release_event", MouseEvent("button_release_event", self.canvas, 0, 0, button=1)
                    )

    def test_hover_uses_blit_and_matches_full_draw(self):
        with patch.object(self.canvas, 'draw', wraps=self.canvas.draw) as draw:
            self.motion()
            self.motion(0, 0)
            self.motion(2, 0)
            self.assertEqual(draw.call_count, 0)
        self.assert_matches_full_draw()
        self.motion(1, 3, panel=1)
        self.assert_matches_full_draw()
        self.canvas.callbacks.process('figure_leave_event', LocationEvent('figure_leave_event', self.canvas, 0, 0))
        self.assertFalse(any(c.hover_highlight.get_visible() for c in self.session.controllers))
        self.assert_matches_full_draw()

    def test_static_mutations_rebuild_before_blit(self):
        axis = self.session.axes[0]
        for mutation in (
            lambda: axis.set_xlim(-1, 4),
            lambda: axis.lines[0].set_color('green'),
            lambda: self.session.figure.set_size_inches(10, 5),
            lambda: axis.set_facecolor('lightgray'),
        ):
            mutation()
            with patch.object(self.canvas, 'draw', wraps=self.canvas.draw) as draw:
                self.motion()
                self.assertGreater(draw.call_count, 0)
            self.assert_matches_full_draw()
            self.motion(0, 0)
            self.assert_matches_full_draw()

    def test_save_and_fallback_preserve_overlay(self):
        self.motion(name='button_press_event')
        self.motion(0, 0)
        self.assert_matches_full_draw()
        expected = np.asarray(self.canvas.buffer_rgba()).copy()
        target = io.BytesIO()
        self.session.figure.savefig(target, format='png', dpi=self.session.figure.dpi)
        target.seek(0)
        np.testing.assert_array_equal(expected, np.asarray(Image.open(target)))
        self.motion(2, 0)
        self.assert_matches_full_draw()
        with patch.object(self.canvas, 'supports_blit', False):
            self.motion(0, 0)
            self.assert_matches_full_draw()

    def test_same_target_after_view_change_and_pending_leave(self):
        self.motion()
        self.session.axes[0].set_facecolor('lightgray')
        self.motion()
        self.assert_matches_full_draw()
        self.session.axes[0].set_xlim(-1, 4)
        with patch.object(self.canvas, 'draw_idle'):
            self.motion()
            self.canvas.callbacks.process('motion_notify_event', MouseEvent(
                'motion_notify_event', self.canvas, 0, 0))
        self.canvas.draw()
        self.assertFalse(self.session.controllers[0].hover_highlight.get_visible())
        self.assert_matches_full_draw()

    def test_layout_legend_and_deletion_preserve_raster(self):
        self.motion(name='button_press_event')
        self.motion(0, 0)
        self.session.toggle_axes_maximized(self.session.axes[0])
        self.motion(2, 0)
        self.assert_matches_full_draw()
        self.session.restore_layout()
        self.session.axes[0].get_legend().set_loc('lower left')
        self.motion(0, 0)
        self.assert_matches_full_draw()
        self.session.remove_series(self.session.series[0])
        self.motion(1, 3, panel=1)
        self.assert_matches_full_draw()

    def test_dual_axes_pins_and_tooltips_match_full_draw(self):
        builder = figure()
        panel = builder.subplot(1, right_ylabel='Right')
        panel.plot([0, 1, 2], [0, 1, 0], label='Left')
        panel.plot([0, 1, 2], [10, 30, 10], label='Right', yaxis='right')
        session = builder.build()
        self.addCleanup(session.close)
        canvas = session.figure.canvas
        canvas.draw()
        for axis, name, x, y, key in (
            (session.axes[0], 'button_press_event', 0, 0, 'shift'),
            (session.right_axes[1], 'button_press_event', 2, 10, 'shift'),
            (session.axes[0], 'motion_notify_event', 1, 1, None),
            (session.right_axes[1], 'motion_notify_event', 1, 30, None),
        ):
            px, py = axis.transData.transform((x, y))
            canvas.callbacks.process(name, MouseEvent(name, canvas, px, py, button=1 if key else None, key=key))
            raster = np.asarray(canvas.buffer_rgba()).copy()
            canvas.draw()
            np.testing.assert_array_equal(raster, np.asarray(canvas.buffer_rgba()))

    def test_pending_full_draw_uses_latest_state(self):
        self.session.axes[0].set_xlim(-1, 3)
        with patch.object(self.canvas, 'draw_idle'):
            for x, y in ((0, 0), (1, 1), (2, 0)):
                self.motion(x, y)
            self.assertEqual(self.session.controllers[0].hover_highlight.get_xdata()[0], 2)
        self.canvas.draw()
        self.assert_matches_full_draw()
        self.session.disconnect()
        with patch.object(self.canvas, 'draw') as draw, patch.object(self.canvas, 'blit') as blit:
            self.motion()
            self.session._layer.refresh()
            draw.assert_not_called()
            blit.assert_not_called()


if __name__ == '__main__':
    unittest.main()

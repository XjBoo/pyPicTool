"""Exercise queued hover work on a real Qt event loop, offscreen."""
import os
import subprocess
import sys
import textwrap
import unittest


class QtHoverLifecycleTests(unittest.TestCase):
    def test_queued_draw_coalesces_and_is_cancelled_on_disconnect(self):
        result = subprocess.run(
            [sys.executable, '-c', textwrap.dedent('''
                import matplotlib
                matplotlib.use('QtAgg')
                from matplotlib.backends.qt_compat import QtWidgets, QtCore
                from matplotlib.backend_bases import MouseEvent
                from unittest.mock import patch
                from interactive_plotting import SeriesData, create_interactive_plot

                def process_events():
                    loop = QtCore.QEventLoop()
                    QtCore.QTimer.singleShot(20, loop.quit)
                    loop.exec()

                def build():
                    session = create_interactive_plot([
                        SeriesData([0, 1, 2], [0, 1, 0], 'data')])
                    session.figure.canvas.draw()
                    process_events()
                    return session

                for close in (False, True):
                    session = build()
                    canvas = session.figure.canvas
                    session.axes[0].set_facecolor('gray')
                    session._layer.refresh()
                    assert session._layer._draw_requested
                    with patch.object(canvas, 'draw', wraps=canvas.draw) as draw:
                        if close:
                            session.close()
                        else:
                            session.disconnect()
                        process_events()
                        draw.assert_not_called()
                    assert not session._layer._draw_requested
                    session.close()

                session = build()
                canvas = session.figure.canvas
                axis = session.axes[0]
                axis.set_facecolor('gray')
                with patch.object(canvas, 'draw', wraps=canvas.draw) as draw:
                    for x, y in ((0, 0), (1, 1), (2, 0)):
                        px, py = axis.transData.transform((x, y))
                        canvas.callbacks.process('motion_notify_event', MouseEvent(
                            'motion_notify_event', canvas, px, py))
                    draw.assert_not_called()
                    process_events()
                    assert draw.call_count == 1, draw.call_count
                    assert session.controllers[0].hover_highlight.get_xdata()[0] == 2
                session.close()
            ''')],
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'},
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

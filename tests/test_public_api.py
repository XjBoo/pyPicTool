import unittest
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

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
            [(row, column) for row in range(3) for column in range(2) for _ in range(2)],
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

    def test_show_demo_builds_six_panels_and_calls_show(self):
        from interactive_plotting import PlotSession, show_demo

        with patch("matplotlib.pyplot.show") as show:
            session = show_demo()

        self.assertIsInstance(session, PlotSession)
        self.assertEqual(len(session.figure.axes), 6)
        self.assertEqual(len(session.controllers), 6)
        np.testing.assert_array_equal(session.figure.get_size_inches(), [12.0, 10.0])
        show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

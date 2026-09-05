"""Keep native Qt tests isolated from the Agg interaction suite."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class QtToolbarTests(unittest.TestCase):
    def test_native_toolbar_toggle_offscreen(self):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", MPLBACKEND="QtAgg")
        result = subprocess.run(
            [sys.executable, "-m", "tests.qt_toolbar_probe"],
            cwd=Path(__file__).resolve().parents[1], env=env,
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Qt toolbar probe: passed", result.stdout)

"""Keep native Qt tests isolated from the Agg interaction suite."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class QtToolbarTests(unittest.TestCase):
    def test_native_toolbar_toggle_offscreen(self):
        repo_root = Path(__file__).resolve().parents[1]
        env = dict(
            os.environ,
            QT_QPA_PLATFORM="offscreen",
            MPLBACKEND="QtAgg",
            # A cold font cache must not make a fresh checkout fail spuriously.
            MPLCONFIGDIR=str(repo_root / ".mplconfig"),
        )
        result = subprocess.run(
            [sys.executable, "-m", "tests.qt_toolbar_probe"],
            cwd=repo_root, env=env,
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Qt toolbar probe: passed", result.stdout)

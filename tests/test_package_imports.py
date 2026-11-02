"""Game modules can load independently of the window and audio adapters."""

from pathlib import Path
import subprocess
import sys
import unittest


class PackageImportTests(unittest.TestCase):
    def test_game_imports_before_presentation_without_loading_mlx_or_audio(self) -> None:
        result = subprocess.run(
            [sys.executable, '-B', '-c', '''
import sys
import game.game
import game.strategy
import controls.game_input
import storage.highscore
assert "mlx" not in sys.modules
assert "pygame" not in sys.modules
from visualize import MazeVisualizer
from visualize.maze_visualizer import MazeVisualizer as DirectVisualizer
assert MazeVisualizer is DirectVisualizer
'''],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

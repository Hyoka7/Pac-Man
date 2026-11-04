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
import pacman.game.game
import pacman.game.strategy
import pacman.controls.game_input
import pacman.storage.highscore
assert "mlx" not in sys.modules
assert "pygame" not in sys.modules
assert "pacman.visualize" not in sys.modules
assert "PIL" not in sys.modules
from pacman.visualize import GameVisualizer
from pacman.visualize.game_visualizer import GameVisualizer as DirectVisualizer
assert GameVisualizer is DirectVisualizer
'''],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

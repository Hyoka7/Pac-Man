"""Ranking deletion requires confirmation and persists an empty score list."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast
import unittest
from unittest.mock import Mock, patch

from visualize.game import Game
from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import HighscoreManager, ScoreEntry
from visualize.controls import KeyEnum
from visualize.maze_visualizer import MazeVisualizer
from visualize.visualizerutils import VisualizerUtils


class RankingClearTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "scores.json"
        self.manager = HighscoreManager(str(self.path))
        self.manager += ScoreEntry(name="Alice", score=120)
        self.before = self.path.read_bytes()
        self.viewer = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
        self.viewer.audio = Mock()
        self.viewer.game = cast(Any, Game.__new__(Game))
        self.viewer.game.level_needs_placement = False
        self.viewer.game.no_collision = False
        self.viewer.canvas = Mock()
        self.viewer.closed = False
        self.viewer.game.shift_keys = set()
        self.viewer.game.state = GUIStateEnum.Ranking
        self.viewer.game.needs_redraw = False
        self.viewer.game.score_manager = self.manager

    def test_c_opens_confirmation_without_deleting(self) -> None:
        with patch.object(self.manager, "clear", wraps=self.manager.clear) as clear:
            self.viewer._on_key(KeyEnum.C)
        clear.assert_not_called()
        self.assertEqual(self.viewer.game.state, GUIStateEnum.Confirm_Clear)
        self.assertTrue(self.viewer.game.needs_redraw)
        self.assertEqual(self.path.read_bytes(), self.before)

    def test_y_clears_memory_and_disk_only_after_confirmation(self) -> None:
        self.viewer._on_key(KeyEnum.Y)
        self.assertEqual(self.path.read_bytes(), self.before)
        self.viewer._on_key(KeyEnum.C)
        self.viewer.game.needs_redraw = False
        self.viewer._on_key(KeyEnum.Y)
        self.assertEqual(self.manager.scores.scores, [])
        self.assertEqual(HighscoreManager(str(self.path)).scores.scores, [])
        self.assertEqual(self.viewer.game.state, GUIStateEnum.Ranking)
        self.assertTrue(self.viewer.game.needs_redraw)

    def test_n_cancels_without_saving_or_deleting(self) -> None:
        self.viewer._on_key(KeyEnum.C)
        self.viewer.game.needs_redraw = False
        with patch.object(self.manager, "save") as save:
            self.viewer._on_key(KeyEnum.N)
        save.assert_not_called()
        self.assertEqual(self.path.read_bytes(), self.before)
        self.assertEqual(len(self.manager.scores.scores), 1)
        self.assertEqual(self.viewer.game.state, GUIStateEnum.Ranking)
        self.assertTrue(self.viewer.game.needs_redraw)

    def test_other_keys_and_repeated_c_do_not_confirm(self) -> None:
        self.viewer._on_key(KeyEnum.C)
        self.viewer.game.needs_redraw = False
        for key in (KeyEnum.C, KeyEnum.ENTER, KeyEnum.A):
            self.viewer._on_key(key)
        self.assertEqual(self.viewer.game.state, GUIStateEnum.Confirm_Clear)
        self.assertFalse(self.viewer.game.needs_redraw)
        self.assertEqual(self.path.read_bytes(), self.before)

    def test_instruction_keys_do_not_open_confirmation(self) -> None:
        self.viewer.game.state = GUIStateEnum.Instruction
        self.viewer._on_key(KeyEnum.C)
        self.assertEqual(self.viewer.game.state, GUIStateEnum.Instruction)
        self.viewer._on_key(KeyEnum.ENTER)
        self.assertEqual(self.viewer.game.state, GUIStateEnum.Home)

    def test_confirmation_screen_draws_panel_and_labels_once(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Confirm_Clear
        v.width, v.height = 800, 600
        v.canvas = VisualizerUtils(
            800, 600, 20, 0, memoryview(bytearray(800 * 600 * 4)),
            800 * 4, 0, 0, 0,
        )
        v.gui = GUI()
        v.gui.update_layout(v.width, v.height)
        v.m = Mock()
        v.p = v.win = v.img = 1
        with patch.object(v.gui, "confirm_clear", wraps=v.gui.confirm_clear) as draw:
            v._draw()
        draw.assert_called_once_with(v.canvas, v.width, v.height)
        v.m.mlx_put_image_to_window.assert_called_once()
        v.m.mlx_string_put.assert_not_called()
        self.assertFalse(v.game.needs_redraw)
        self.assertEqual(self.path.read_bytes(), self.before)


if __name__ == "__main__":
    unittest.main()

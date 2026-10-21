"""Home rendering should persist until its content needs refreshing."""

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock

from visualize.gui import GUIStateEnum
from visualize.highscore import HighscoreManager
from visualize.maze_visualizer import KeyEnum, MazeVisualizer


class HomeRedrawTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.viewer = MazeVisualizer.__new__(MazeVisualizer)
        v = self.viewer
        v.closed = False
        v.state = GUIStateEnum.Home
        v.needs_redraw = True
        v.last_time = monotonic()
        v.canvas = Mock()
        v.m = Mock()
        v.gui = Mock()
        v.p = v.win = v.img = 1
        v.width = v.height = 600
        v.player = SimpleNamespace(
            is_invincible=False, score=120, lives=3,
            draw=Mock(), update=Mock(), update_mouth=Mock(),
        )
        v.maze = Mock()
        v.pacgums = MagicMock()
        v.pacgums.__len__.return_value = 1
        v.ghosts = []
        v.cmodes = [((255, 255, 255), (255, 0, 0), (0, 0, 0))]
        v.cm = 0
        v.level = 1
        v.remaining_time = 42.0
        v.player_name = "Alice"
        v.score_manager = HighscoreManager(
            str(Path(self.directory.name) / "scores.json")
        )

    def test_initial_draw_is_not_repeated_by_idle_loops(self) -> None:
        v = self.viewer
        v._draw()
        for _ in range(3):
            v._on_loop()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.gui.home.assert_called_once()
        self.assertFalse(v.needs_redraw)
        self.assertGreater(v.last_time, 0.0)

    def test_return_after_score_save_refreshes_home_once(self) -> None:
        v = self.viewer
        v._draw()
        v.state = GUIStateEnum.GameOver
        v._on_key(KeyEnum.ENTER)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)
        scores = v.gui.home.call_args.args[-1]
        self.assertEqual((scores[0].name, scores[0].score), ("Alice", 120))

    def test_expose_can_redraw_an_unchanged_home(self) -> None:
        v = self.viewer
        v._draw()
        v._draw()  # Same callback registered with mlx_expose_hook.
        self.assertEqual(v.gui.home.call_count, 2)

    def test_other_screens_keep_drawing_each_loop(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Stage_Clear
        v.needs_redraw = False
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.m.mlx_put_image_to_window.call_count, 2)
        self.assertEqual(v.gui.stage_clear.call_count, 2)

    def test_pause_draws_once_without_updating_game(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Playing
        v.needs_redraw = False
        v._on_key(KeyEnum.P)
        self.assertTrue(v.needs_redraw)
        for _ in range(3):
            v._on_loop()
        v.gui.pause.assert_called_once()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.player.update.assert_not_called()
        self.assertEqual(v.remaining_time, 42.0)

    def test_expose_can_redraw_pause(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Pause
        v._draw()
        self.assertFalse(v.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.pause.call_count, 2)

    def test_pause_to_home_refreshes_home(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Pause
        v.needs_redraw = False
        v._on_key(KeyEnum.H)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.home.assert_called_once()

    def test_resume_keeps_updating_and_drawing(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Pause
        v.needs_redraw = False
        v._on_key(KeyEnum.P)
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.player.update.call_count, 2)
        self.assertEqual(v.m.mlx_put_image_to_window.call_count, 2)

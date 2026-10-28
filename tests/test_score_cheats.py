"""Score multipliers use visualizer-owned point values and gated cheat keys."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from models.models import Config, LevelConfig
from visualize.ghost import Ghost
from visualize.gui import GUIStateEnum
from visualize.maze_visualizer import KeyEnum, MazeVisualizer
from visualize.strategy import BFSStrategy
from visualize.visualizerutils import VisualizerUtils


class ScoreCheatTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        config = Config(
            highscore_filename=str(Path(directory.name) / 'scores.json'),
            levels=[LevelConfig(width=5, height=1)],
            points_per_pacgum=11, points_per_super_pacgum=37, points_per_ghost=123,
        )
        self.viewer = MazeVisualizer([[13, 5, 5, 5, 7]], Mock(), config)
        v = self.viewer
        v.canvas = VisualizerUtils(120, 60, 20, 10,
            memoryview(bytearray(120 * 60 * 4)), 480, 0, 10, 10)
        v.player.place(v.canvas)
        v.ghosts = []
        v.closed = False
        v.cheat_enabled = True
        v.state = GUIStateEnum.Playing
        v.last_time = 10.0
        self.enterContext(patch.object(v, '_draw'))

    def tick(self, now: float = 10.125) -> None:
        with patch('visualize.maze_visualizer.time.monotonic', return_value=now):
            self.viewer._on_loop()

    def test_gum_rewards_use_configured_values_and_multiplier_including_last_gum(self) -> None:
        v = self.viewer
        for boosted in (False, True):
            for super_gum, base in ((False, 11), (True, 37)):
                with self.subTest(boosted=boosted, super_gum=super_gum):
                    v.state = GUIStateEnum.Playing
                    v.last_time = 10.0
                    v.player.reset(v.canvas)
                    v.player.score = 77
                    v.score_multiplier = 1
                    v.pacgums.remain_gums.clear()
                    v.pacgums.super_gums.clear()
                    points = v.pacgums.super_gums if super_gum else v.pacgums.remain_gums
                    points.add(v.canvas.cell_center(3, 0))
                    if boosted:
                        v._on_key(KeyEnum.X)
                    self.assertEqual(v.player.score, 77)
                    v.player.request_move('E', v.maze, v.canvas)
                    self.tick()
                    self.assertEqual(v.player.score, 77 + base * (10 if boosted else 1))
                    self.assertEqual(v.state, GUIStateEnum.All_Clear)
                    self.assertEqual(v.player.is_invincible, super_gum)

    def test_ghost_reward_is_multiplied_once_during_invincible_collision(self) -> None:
        v = self.viewer
        ghost = Ghost(v.player.movement.cell, BFSStrategy())
        ghost.place(v.canvas)
        v.ghosts = [ghost]
        v.ghost_frozen = True
        v.player.is_invincible = True
        v.player.invincible_remain = 5.0
        v.pacgums.remain_gums.add(v.canvas.cell_center(3, 0))
        v._on_key(KeyEnum.X)
        with redirect_stdout(StringIO()):
            self.tick(10.0)
            self.tick(10.05)
        self.assertEqual(v.player.score, 1230)
        self.assertEqual(ghost.respawn_remaining, 5.0)

    def test_x_toggles_only_while_playing_with_cheats(self) -> None:
        v = self.viewer
        v.cheat_enabled = False
        v._on_key(KeyEnum.X)
        self.assertEqual(v.score_multiplier, 1)
        v.cheat_enabled = True
        v._on_key(KeyEnum.X)
        self.assertEqual(v.score_multiplier, 10)
        v._on_key(KeyEnum.X)
        self.assertEqual(v.score_multiplier, 1)
        for state in (GUIStateEnum.Home, GUIStateEnum.Pause, GUIStateEnum.Ranking):
            v.state = state
            v._on_key(KeyEnum.X)
            self.assertEqual(v.score_multiplier, 1)

    def test_h_toggles_wallhack_and_w_keeps_its_movement_meaning(self) -> None:
        v = self.viewer
        v.cheat_enabled = False
        v._on_key(KeyEnum.H)
        self.assertFalse(v.player.movement.wallhack)
        v.cheat_enabled = True
        v._on_key(KeyEnum.H)
        self.assertTrue(v.player.movement.wallhack)
        with patch.object(v.player, 'request_move') as move:
            v._on_key(KeyEnum.W)
        move.assert_called_once_with('N', v.maze, v.canvas)
        self.assertTrue(v.player.movement.wallhack)
        v._on_key(KeyEnum.H)
        self.assertFalse(v.player.movement.wallhack)

    def test_disabling_cheats_resets_multiplier_and_wallhack(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.X)
        v._on_key(KeyEnum.H)
        for key in map(ord, '3111696'):
            v._on_key(key)
        self.assertFalse(v.cheat_enabled)
        self.assertEqual(v.score_multiplier, 1)
        self.assertFalse(v.player.movement.wallhack)

    def test_new_game_resets_multiplier_and_wallhack(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.X)
        v._on_key(KeyEnum.H)
        with patch.object(v, 'regenerate_maze'):
            v.restart_game()
        self.assertEqual(v.score_multiplier, 1)
        self.assertFalse(v.player.movement.wallhack)

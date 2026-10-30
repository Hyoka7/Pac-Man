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
from visualize.controls import KeyEnum
from visualize.maze_visualizer import MazeVisualizer
from visualize.strategy import BFSStrategy
from visualize.visualizerutils import VisualizerUtils


class ScoreCheatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(patch('visualize.maze_visualizer.AudioManager'))
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
        v.game.player.place(v.canvas)
        v.game.ghosts = []
        v.closed = False
        v.game.cheat_enabled = True
        v.game.state = GUIStateEnum.Playing
        v.last_time = 10.0
        self.enterContext(patch.object(v, '_draw'))

    def tick(self, now: float | None = None) -> None:
        if now is None:
            now = self.viewer.last_time + 1 / self.viewer.game.player.movement.speed + 1e-6
        with patch('visualize.maze_visualizer.time.monotonic', return_value=now):
            self.viewer._on_loop()

    def test_gum_rewards_use_configured_values_and_multiplier_including_last_gum(self) -> None:
        v = self.viewer
        for boosted in (False, True):
            for super_gum, base in ((False, 11), (True, 37)):
                with self.subTest(boosted=boosted, super_gum=super_gum):
                    v.game.state = GUIStateEnum.Playing
                    v.last_time = 10.0
                    v.game.player.reset(v.canvas)
                    v.game.player.score = 77
                    v.game.score_multiplier = 1
                    v.game.pacgums.remain_gums.clear()
                    v.game.pacgums.super_gums.clear()
                    points = v.game.pacgums.super_gums if super_gum else v.game.pacgums.remain_gums
                    points.add(v.canvas.cell_center(3, 0))
                    if boosted:
                        v._on_key(KeyEnum.X)
                    self.assertEqual(v.game.player.score, 77)
                    v.game.player.request_move('E', v.game.maze, v.canvas)
                    self.tick()
                    self.assertEqual(v.game.player.score, 77 + base * (10 if boosted else 1))
                    self.assertEqual(v.game.state, GUIStateEnum.All_Clear)
                    self.assertEqual(v.game.player.is_invincible, super_gum)

    def test_ghost_reward_is_multiplied_once_during_invincible_collision(self) -> None:
        v = self.viewer
        ghost = Ghost(v.game.player.movement.cell, BFSStrategy())
        ghost.place(v.canvas)
        v.game.ghosts = [ghost]
        v.game.ghost_frozen = True
        v.game.player.is_invincible = True
        v.game.player.invincible_remain = 5.0
        v.game.pacgums.remain_gums.add(v.canvas.cell_center(3, 0))
        v._on_key(KeyEnum.X)
        with redirect_stdout(StringIO()):
            self.tick(10.0)
            self.tick(10.05)
        self.assertEqual(v.game.player.score, 1230)
        self.assertEqual(ghost.respawn_remaining, 5.0)

    def test_x_toggles_only_while_playing_with_cheats(self) -> None:
        v = self.viewer
        v.game.cheat_enabled = False
        v._on_key(KeyEnum.X)
        self.assertEqual(v.game.score_multiplier, 1)
        v.game.cheat_enabled = True
        v._on_key(KeyEnum.X)
        self.assertEqual(v.game.score_multiplier, 10)
        v._on_key(KeyEnum.X)
        self.assertEqual(v.game.score_multiplier, 1)
        for state in (GUIStateEnum.Home, GUIStateEnum.Pause, GUIStateEnum.Ranking):
            v.game.state = state
            v._on_key(KeyEnum.X)
            self.assertEqual(v.game.score_multiplier, 1)

    def test_h_toggles_wallhack_and_w_keeps_its_movement_meaning(self) -> None:
        v = self.viewer
        v.game.cheat_enabled = False
        v._on_key(KeyEnum.H)
        self.assertFalse(v.game.player.movement.wallhack)
        v.game.cheat_enabled = True
        v._on_key(KeyEnum.H)
        self.assertTrue(v.game.player.movement.wallhack)
        with patch.object(v.game.player, 'request_move') as move:
            v._on_key(KeyEnum.W)
        move.assert_called_once_with('N', v.game.maze, v.canvas)
        self.assertTrue(v.game.player.movement.wallhack)
        v._on_key(KeyEnum.H)
        self.assertFalse(v.game.player.movement.wallhack)

    def test_disabling_cheats_resets_multiplier_wallhack_and_death_immunity(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.X)
        v._on_key(KeyEnum.H)
        v._on_key(KeyEnum.K)
        self.assertTrue(v.game.no_collision)
        for key in map(ord, '3111696'):
            v._on_key(key)
        self.assertFalse(v.game.cheat_enabled)
        self.assertEqual(v.game.score_multiplier, 1)
        self.assertFalse(v.game.player.movement.wallhack)
        self.assertFalse(v.game.no_collision)

    def test_new_game_resets_multiplier_wallhack_and_death_immunity(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.X)
        v._on_key(KeyEnum.H)
        v._on_key(KeyEnum.K)
        self.assertTrue(v.game.no_collision)
        with patch.object(v.game, 'regenerate_maze'):
            v.restart_game()
        self.assertEqual(v.game.score_multiplier, 1)
        self.assertFalse(v.game.player.movement.wallhack)
        self.assertFalse(v.game.no_collision)

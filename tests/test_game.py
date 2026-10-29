"""Game rules run without a window; the viewer applies new screen geometry."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from mazegenerator import MazeGenerator

from models.models import Config, LevelConfig
from visualize.controls import KeyEnum, WindowAction
from visualize.game import Game
from visualize.game_state import GUIStateEnum
from visualize.ghost import Ghost
from visualize.maze_visualizer import MazeVisualizer
from visualize.strategy import BFSStrategy
from visualize.visualizerutils import VisualizerUtils


class GameTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = Config(
            highscore_filename=str(Path(directory.name) / 'scores.json'),
            levels=[LevelConfig(width=5, height=1)],
        )
        self.game = Game([[13, 5, 5, 5, 7]], Mock(), self.config)
        self.canvas = VisualizerUtils(
            120, 60, 20, 10, memoryview(bytearray(120 * 60 * 4)),
            480, 0, 10, 10,
        )
        self.game.place(self.canvas)
        self.game.ghosts = []
        self.game.state = GUIStateEnum.Playing

    def test_pause_freezes_time_and_motion_then_resume_advances(self) -> None:
        game = self.game
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        game.handle_key(KeyEnum.P, self.canvas)
        center, remaining = game.player.movement.center, game.remaining_time
        game.update(10.0, self.canvas)
        self.assertEqual(game.player.movement.center, center)
        self.assertEqual(game.remaining_time, remaining)
        game.handle_key(KeyEnum.P, self.canvas)
        game.update(0.05, self.canvas)
        self.assertGreater(game.player.movement.center[0], center[0])
        self.assertAlmostEqual(game.remaining_time, remaining - 0.05)

    def test_last_gum_scores_and_clear_wins_over_timeout(self) -> None:
        game = self.game
        game.pacgums.remain_gums = {self.canvas.cell_center(3, 0)}
        game.pacgums.super_gums.clear()
        game.remaining_time = 0.125
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        game.update(0.125, self.canvas)
        self.assertEqual(game.state, GUIStateEnum.All_Clear)
        self.assertEqual(game.remaining_time, 0.0)
        self.assertEqual(game.player.score, self.config.points_per_pacgum)
        self.assertEqual(game.player.lives, self.config.lives)

    def test_timeout_with_gums_remaining_ends_game(self) -> None:
        self.game.remaining_time = 0.1
        self.game.update(0.2, self.canvas)
        self.assertEqual(self.game.state, GUIStateEnum.GameOver)
        self.assertEqual(self.game.player.lives, 0)
        self.assertFalse(self.game.player.is_alive)

    def test_collision_respawns_without_restoring_eaten_gums_or_score(self) -> None:
        game = self.game
        ghost = Ghost(game.player.movement.cell, BFSStrategy())
        ghost.place(self.canvas)
        game.ghosts = [ghost]
        game.ghost_frozen = True
        game.player.lives, game.player.score = 2, 123
        game.pacgums.remain_gums = {self.canvas.cell_center(1, 0)}
        game.pacgums.super_gums.clear()
        before = set(game.pacgums.remain_gums)
        with redirect_stdout(StringIO()):
            game.update(0.0, self.canvas)
        self.assertEqual(game.state, GUIStateEnum.Playing)
        self.assertEqual((game.player.lives, game.player.score), (1, 123))
        self.assertEqual(game.pacgums.remain_gums, before)
        self.assertEqual(game.player.movement.center,
                         self.canvas.cell_center(*game.player.movement.initial_cell))

    def test_window_actions_are_returned_without_opening_or_drawing(self) -> None:
        game = self.game
        self.assertEqual(game.handle_key(KeyEnum.C, self.canvas),
                         WindowAction.CycleColors)
        self.assertEqual(game.handle_key(KeyEnum.ESC, self.canvas),
                         WindowAction.Close)
        game.state = GUIStateEnum.Home
        game.home_focusing = 3
        self.assertEqual(game.handle_key(KeyEnum.ENTER, self.canvas),
                         WindowAction.Close)

    def test_key_transition_places_next_level_using_updated_layout(self) -> None:
        self.config.levels = [LevelConfig(width=15, height=15),
                              LevelConfig(width=25, height=15)]
        generator = MazeGenerator(size=(15, 15), seed=42)
        viewer = MazeVisualizer(generator.maze, generator, self.config)
        viewer.width, viewer.height = 1000, 800
        viewer._update_layout()
        viewer.canvas = VisualizerUtils(
            1000, 800, viewer.cell_size, viewer.margin,
            memoryview(bytearray(1000 * 800 * 4)), 4000, 0,
            viewer.offset_x, viewer.offset_y,
        )
        viewer.game.place(viewer.canvas)
        viewer.closed = False
        viewer.game.state = GUIStateEnum.Home
        viewer._on_key(KeyEnum.ENTER)
        self.assertEqual(viewer.game.state, GUIStateEnum.Playing)
        self.assertFalse(viewer.game.level_needs_placement)
        viewer.game.state = GUIStateEnum.Stage_Clear
        viewer._on_key(32)
        self.assertEqual((viewer.game.maze.cols, viewer.game.maze.rows), (25, 15))
        self.assertFalse(viewer.game.level_needs_placement)
        self.assertEqual(viewer.canvas.cell_size, viewer.cell_size)
        self.assertEqual((viewer.canvas.offset_x, viewer.canvas.offset_y),
                         (viewer.offset_x, viewer.offset_y))
        for character in [viewer.game.player, *viewer.game.ghosts]:
            self.assertEqual(character.movement.center,
                             viewer.canvas.cell_center(*character.movement.initial_cell))
            self.assertEqual(character.radius, viewer.cell_size * 0.375)

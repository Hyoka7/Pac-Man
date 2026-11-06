"""Game rules run without a window; the viewer applies new screen geometry."""

import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Unpack
from unittest.mock import Mock, patch

from mazegenerator import MazeGenerator

from pacman.controls.keys import KeyEnum, WindowAction
from pacman.game.game import Game
from pacman.game.ghost import Ghost, GhostRole
from pacman.game.maze import Maze
from pacman.game.pacgums import PacgumEatenEnum
from pacman.game.state import GameState
from pacman.game.strategy import BFSStrategy, ReverseAmbushStrategy, StrategyKwargs
from pacman.models.models import Config, LevelConfig
from pacman.visualize.game_visualizer import GameVisualizer
from pacman.visualize.canvas import Canvas


class GameTests(unittest.TestCase):
    def test_o_leaves_manual_movement_and_reserved_turn_unchanged(self) -> None:
        game = self.game
        game.cheat_enabled = True
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        game.handle_key(KeyEnum.UP, self.canvas)
        self.assertEqual(game.player.reserved_move, 'N')
        target = game.player.movement.target_cell
        game.handle_key(KeyEnum.O, self.canvas)
        self.assertEqual(game.player.reserved_move, 'N')
        self.assertEqual(game.player.movement.target_cell, target)
        self.assertEqual(game.state, GameState.Playing)

    def test_current_red_position_reaches_strategy_target_selection(self) -> None:
        class RedTargetStrategy(BFSStrategy):
            def choose_target(
                self, maze: Maze, ghost_pos: tuple[int, int],
                player_pos: tuple[int, int], player_dir: str,
                **kwargs: Unpack[StrategyKwargs],
            ) -> tuple[int, int]:
                red_pos = kwargs.get("red_pos")
                return red_pos if red_pos is not None else player_pos

        game = self.game
        game.player.movement.cell = (0, 0)
        game.player.movement.place_movement(self.canvas)
        game.pacgums.reset_pacgums(game.maze, self.canvas, (0, 0))
        game.no_collision = True
        observer = Ghost((1, 0), RedTargetStrategy())
        red = Ghost((4, 0), BFSStrategy(), role=GhostRole.RED)
        game.ghosts = [observer, red]
        for red_cell, expected in (((4, 0), (2, 0)), ((0, 0), (0, 0))):
            with self.subTest(red_cell=red_cell):
                observer.place_ghost(self.canvas)
                red.movement.cell = red_cell
                red.place_ghost(self.canvas)
                game.update_game(0.0, self.canvas)
                self.assertEqual(observer.movement.target_cell, expected)

        red.strategy = ReverseAmbushStrategy()
        red.movement.cell = (4, 0)
        red.place_ghost(self.canvas)
        observer.place_ghost(self.canvas)
        game.update_game(0.0, self.canvas)
        self.assertEqual(observer.movement.target_cell, (2, 0))

    def test_each_ghost_follows_its_own_strategy(self) -> None:
        game = self.game
        game.maze = Maze([[9, 1, 3], [8, 0, 2], [12, 4, 6]])
        game.player.movement.cell = (2, 2)
        game.player.movement.place_movement(self.canvas)
        game.pacgums.reset_pacgums(game.maze, self.canvas, (2, 2))
        follower = Ghost((0, 0), ReverseAmbushStrategy())
        leader = Ghost((0, 0), BFSStrategy())
        game.ghosts = [follower, leader]
        for ghost in game.ghosts:
            ghost.place_ghost(self.canvas)
        with patch('pacman.game.strategy.random.choice', side_effect=lambda choices: choices[0]):
            game.update_game(0.01, self.canvas)
        self.assertEqual(leader.movement.target_cell, (1, 0))
        self.assertEqual(follower.movement.target_cell, (0, 1))
        self.assertEqual(game.ghosts, [follower, leader])

    def setUp(self) -> None:
        self.enterContext(patch('pacman.visualize.game_visualizer.AudioManager'))
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = Config(
            highscore_filename=str(Path(directory.name) / 'scores.json'),
            levels=[LevelConfig.model_construct(width=5, height=1)],
        )
        self.game = Game(Mock(maze=[[13, 5, 5, 5, 7]]), self.config)
        self.canvas = Canvas(
            120, 60, 20, 10, memoryview(bytearray(120 * 60 * 4)),
            480, 0, 10, 10,
        )
        self.game.place_level(self.canvas)
        self.game.ghosts = []
        self.game.state = GameState.Playing

    def test_pause_freezes_time_and_motion_then_resume_advances(self) -> None:
        game = self.game
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        game.handle_key(KeyEnum.P, self.canvas)
        center, remaining = game.player.movement.center, game.remaining_time
        game.update_game(10.0, self.canvas)
        self.assertEqual(game.player.movement.center, center)
        self.assertEqual(game.remaining_time, remaining)
        game.handle_key(KeyEnum.P, self.canvas)
        game.update_game(0.05, self.canvas)
        self.assertGreater(game.player.movement.center[0], center[0])
        self.assertAlmostEqual(game.remaining_time, remaining - 0.05)

    def test_last_gum_scores_and_clear_wins_over_timeout(self) -> None:
        game = self.game
        game.pacgums.remain_gums = {self.canvas.cell_center(3, 0)}
        game.pacgums.super_gums.clear()
        step_time = 1 / game.player.movement.speed + 1e-6
        game.remaining_time = step_time
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        eaten = game.update_game(step_time, self.canvas)
        self.assertEqual(eaten, (PacgumEatenEnum.Normal, 0))
        self.assertEqual(game.state, GameState.All_Clear)
        self.assertEqual(game.remaining_time, 0.0)
        self.assertEqual(game.player.score, self.config.points_per_pacgum)
        self.assertEqual(game.player.lives, self.config.lives)

    def test_inactive_states_return_no_gum_event(self) -> None:
        center = self.game.player.movement.center
        remaining = self.game.remaining_time
        for state in GameState:
            if state == GameState.Playing:
                continue
            with self.subTest(state=state):
                self.game.state = state
                self.assertEqual(self.game.update_game(0.1, self.canvas), (PacgumEatenEnum.Neither, 0))
                self.assertEqual(self.game.player.movement.center, center)
                self.assertEqual(self.game.remaining_time, remaining)

    def test_ready_consumes_start_key_before_accepting_movement(self) -> None:
        game = self.game
        game.set_state(GameState.Ready)
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        self.assertEqual(game.state, GameState.Playing)
        self.assertFalse(game.player.movement.moving)
        game.handle_key(KeyEnum.RIGHT, self.canvas)
        self.assertTrue(game.player.movement.moving)

    def test_death_cheat_preserves_lives_but_still_allows_eating_ghosts(self) -> None:
        game = self.game
        game.handle_key(KeyEnum.K, self.canvas)
        self.assertFalse(game.no_collision)
        game.cheat_enabled = True
        game.handle_key(KeyEnum.K, self.canvas)
        self.assertTrue(game.no_collision)
        ghost = Ghost(game.player.movement.cell, BFSStrategy())
        ghost.place_ghost(self.canvas)
        game.ghosts = [ghost]
        game.ghost_frozen = True
        self.assertEqual(game.update_game(0.0, self.canvas), (PacgumEatenEnum.Neither, 0))
        self.assertEqual(game.player.lives, self.config.lives)
        self.assertEqual(game.player.score, 0)
        game.player.is_invincible = True
        game.player.invincible_remain = 5.0
        self.assertEqual(game.update_game(0.0, self.canvas), (PacgumEatenEnum.Neither, 1))
        self.assertEqual(game.player.score, self.config.points_per_ghost)
        self.assertEqual(ghost.respawn_remaining, 5.0)

    def test_timeout_with_gums_remaining_ends_game(self) -> None:
        self.game.remaining_time = 0.1
        self.game.update_game(0.2, self.canvas)
        self.assertEqual(self.game.state, GameState.GameOver)
        self.assertEqual(self.game.player.lives, 0)
        self.assertFalse(self.game.player.is_alive)

    def test_collision_respawns_without_restoring_eaten_gums_or_score(self) -> None:
        game = self.game
        ghost = Ghost(game.player.movement.cell, BFSStrategy())
        ghost.place_ghost(self.canvas)
        game.ghosts = [ghost]
        game.ghost_frozen = True
        game.player.lives, game.player.score = 2, 123
        game.pacgums.remain_gums = {self.canvas.cell_center(1, 0)}
        game.pacgums.super_gums.clear()
        before = set(game.pacgums.remain_gums)
        with redirect_stdout(StringIO()):
            game.update_game(0.0, self.canvas)
        self.assertEqual(game.state, GameState.Ready)
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
        game.state = GameState.Home
        game.home_focusing = 3
        self.assertEqual(game.handle_key(KeyEnum.ENTER, self.canvas),
                         WindowAction.Close)

    def test_key_transition_places_next_level_using_updated_layout(self) -> None:
        self.config.levels = [LevelConfig(width=15, height=15),
                              LevelConfig(width=25, height=15)]
        generator = MazeGenerator(size=(15, 15), seed=42)
        viewer = GameVisualizer(generator, self.config)
        viewer.width, viewer.height = 1000, 800
        viewer._update_layout()
        viewer.canvas = Canvas(
            1000, 800, viewer.cell_size, viewer.margin,
            memoryview(bytearray(1000 * 800 * 4)), 4000, 0,
            viewer.offset_x, viewer.offset_y,
        )
        viewer.game.place_level(viewer.canvas)
        viewer.window_closed = False
        viewer.game.state = GameState.Home
        viewer._on_key(KeyEnum.ENTER)
        self.assertEqual(viewer.game.state, GameState.Ready)
        self.assertFalse(viewer.game.new_level_needs_placement)
        viewer.game.state = GameState.Stage_Clear
        viewer._on_key(32)
        self.assertEqual((viewer.game.maze.cols, viewer.game.maze.rows), (25, 15))
        self.assertFalse(viewer.game.new_level_needs_placement)
        self.assertEqual(viewer.canvas.cell_size, viewer.cell_size)
        self.assertEqual((viewer.canvas.offset_x, viewer.canvas.offset_y),
                         (viewer.offset_x, viewer.offset_y))
        for character in [viewer.game.player, *viewer.game.ghosts]:
            self.assertEqual(character.movement.center,
                             viewer.canvas.cell_center(*character.movement.initial_cell))
            self.assertEqual(character.radius, viewer.cell_size * 0.375)

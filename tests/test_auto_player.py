"""Auto collects reachable gum while avoiding predicted ghost encounters."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from models.models import Config, LevelConfig
from visualize.auto_player import AutoPlayer
from visualize.ghost import Ghost
from visualize.gui import GUIStateEnum
from visualize.maze import Maze
from visualize.controls import KeyEnum
from visualize.maze_visualizer import MazeVisualizer
from visualize.pacgums import Pacgums
from visualize.player import Player
from visualize.strategy import BFSStrategy
from visualize.visualizerutils import VisualizerUtils


def canvas(cols: int, rows: int) -> VisualizerUtils:
    width, height = cols * 20 + 20, rows * 20 + 20
    return VisualizerUtils(width, height, 20, 10,
        memoryview(bytearray(width * height * 4)), width * 4, 0, 10, 10)


def maze_from_edges(cols: int, rows: int,
                    edges: list[tuple[tuple[int, int], tuple[int, int]]]) -> Maze:
    cells = [[15] * cols for _ in range(rows)]
    masks = {(0, -1): (1, 4), (1, 0): (2, 8),
             (0, 1): (4, 1), (-1, 0): (8, 2)}
    for (x, y), (nx, ny) in edges:
        first, second = masks[nx - x, ny - y]
        cells[y][x] &= ~first
        cells[ny][nx] &= ~second
    return Maze(cells)


class AutoPlayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(patch('visualize.maze_visualizer.AudioManager'))
        self.maze = Maze([[13, 5, 5, 5, 7]])
        self.canvas = canvas(5, 1)
        self.player = Player((2, 0))
        self.player.place(self.canvas)
        self.gums = Pacgums(1, 5)
        self.gums.remain_gums = {self.canvas.cell_center(3, 0)}
        self.auto = AutoPlayer()

    def ghost(self, cell: tuple[int, int]) -> Ghost:
        ghost = Ghost(cell, BFSStrategy())
        ghost.place(self.canvas)
        return ghost

    def test_goes_to_nearest_reachable_gum(self) -> None:
        self.gums.remain_gums.add(self.canvas.cell_center(0, 0))
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [], self.canvas), 'E')

    def test_flees_when_ghost_blocks_the_gum(self) -> None:
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [self.ghost((3, 0))], self.canvas), 'W')

    def test_uses_actual_invincible_time_and_ignores_respawning_ghost_until_return(self) -> None:
        ghost = self.ghost((3, 0))
        self.player.is_invincible = True
        self.player.invincible_remain = 5.0
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [ghost], self.canvas), 'E')
        self.player.invincible_remain = 0.01
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [ghost], self.canvas), 'W')
        self.player.is_invincible = False
        ghost.respawn_remaining = 3.0
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [ghost], self.canvas), 'E')

    def test_accounts_for_ghost_already_approaching_between_cells(self) -> None:
        ghost = self.ghost((3, 0))
        ghost.movement.start('W', self.maze, self.canvas)
        ghost.movement.update(0.225, self.canvas)
        self.assertEqual(ghost.cell, (3, 0))
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [ghost], self.canvas), 'W')

    def test_avoids_dead_end_when_enemy_can_block_the_exit(self) -> None:
        maze = maze_from_edges(3, 3, [
            ((0, 1), (1, 1)), ((1, 1), (1, 0)),
            ((1, 1), (2, 1)), ((2, 1), (2, 2)),
            ((2, 2), (1, 2)), ((1, 2), (1, 1)),
        ])
        target = canvas(3, 3)
        player = Player((1, 1)); player.place(target)
        ghost = Ghost((0, 1), BFSStrategy()); ghost.place(target)
        gums = Pacgums(3, 3)
        gums.remain_gums = {target.cell_center(1, 0), target.cell_center(2, 2)}
        self.assertIn(self.auto.choose_direction(maze, player, gums, [ghost], target),
                      ('E', 'S'))

    def test_returns_none_when_no_gum_or_no_route_exists(self) -> None:
        self.gums.remain_gums.clear()
        self.assertIsNone(self.auto.choose_direction(
            self.maze, self.player, self.gums, [], self.canvas))
        maze = Maze([[15, 15]])
        self.gums.remain_gums.add(self.canvas.cell_center(1, 0))
        player = Player((0, 0)); player.place(self.canvas)
        self.assertIsNone(self.auto.choose_direction(
            maze, player, self.gums, [], self.canvas))

    def test_player_chooses_at_arrival_instead_of_continuing_straight(self) -> None:
        maze = maze_from_edges(2, 2, [((0, 0), (1, 0)), ((1, 0), (1, 1))])
        target = canvas(2, 2)
        player = Player((0, 0)); player.place(target)
        gums = Pacgums(2, 2)
        gums.remain_gums = {target.cell_center(1, 0), target.cell_center(1, 1)}
        def choose() -> str | None:
            return self.auto.choose_direction(maze, player, gums, [], target)
        player.update(0.0, maze, target, gums, choose_auto_direction=choose)
        self.assertEqual(player.movement.target_cell, (1, 0))
        player.update(0.125, maze, target, gums, choose_auto_direction=choose)
        self.assertEqual(player.movement.cell, (1, 0))
        self.assertEqual(player.movement.target_cell, (1, 1))
        self.assertEqual(len(gums), 1)

    def test_o_requires_cheats_manual_input_and_cheat_disable_stop_auto(self) -> None:
        with TemporaryDirectory() as directory:
            config = Config(highscore_filename=str(Path(directory) / 'scores.json'),
                            levels=[LevelConfig(width=5, height=1)])
            viewer = MazeVisualizer(self.maze.maze, Mock(), config)
            viewer.canvas = self.canvas
            viewer.game.player.place(self.canvas)
            viewer.closed = False
            viewer.game.state = GUIStateEnum.Playing
            viewer._on_key(KeyEnum.O)
            self.assertFalse(viewer.game.auto_enabled)
            viewer.game.cheat_enabled = True
            viewer._on_key(KeyEnum.O)
            self.assertTrue(viewer.game.auto_enabled)
            viewer._on_key(KeyEnum.LEFT)
            self.assertFalse(viewer.game.auto_enabled)
            viewer._on_key(KeyEnum.O)
            for key in map(ord, '3111696'):
                viewer._on_key(key)
            self.assertFalse(viewer.game.auto_enabled)

    def test_game_loop_supplies_auto_decision_to_player(self) -> None:
        with TemporaryDirectory() as directory:
            config = Config(highscore_filename=str(Path(directory) / 'scores.json'),
                            levels=[LevelConfig(width=5, height=1)])
            viewer = MazeVisualizer(self.maze.maze, Mock(), config)
            viewer.canvas = self.canvas
            viewer.game.player.place(self.canvas)
            viewer.game.ghosts = []
            viewer.game.pacgums.remain_gums = {self.canvas.cell_center(3, 0)}
            viewer.game.player.movement.cell = (2, 0)
            viewer.game.player.place(self.canvas)
            viewer.closed = False
            viewer.game.state = GUIStateEnum.Playing
            viewer.game.auto_enabled = True
            viewer.last_time = 10.0
            with patch.object(viewer, '_draw'), patch(
                'visualize.maze_visualizer.time.monotonic', return_value=10.05
            ):
                viewer._on_loop()
            self.assertGreater(viewer.game.player.movement.center[0],
                               self.canvas.cell_center(2, 0)[0])

    def test_auto_collects_normal_and_super_gums_through_real_game_loop(self) -> None:
        with TemporaryDirectory() as directory:
            config = Config(highscore_filename=str(Path(directory) / 'scores.json'),
                            levels=[LevelConfig(width=5, height=1)])
            viewer = MazeVisualizer(self.maze.maze, Mock(), config)
            viewer.canvas = self.canvas
            viewer.game.player.place(self.canvas)
            viewer.game.ghosts = []
            viewer.game.pacgums.reset(viewer.game.maze, self.canvas, viewer.game.player.movement.cell)
            viewer.closed = False
            viewer.game.state = GUIStateEnum.Playing
            viewer.game.auto_enabled = True
            viewer.last_time = 0.0
            with patch.object(viewer, '_draw'):
                for frame in range(1, 601):
                    with patch('visualize.maze_visualizer.time.monotonic',
                               return_value=frame / 60):
                        viewer._on_loop()
                    x, y = viewer.game.player.movement.cell
                    self.assertTrue(0 <= x < 5 and y == 0)
                    if viewer.game.state != GUIStateEnum.Playing:
                        break
            self.assertEqual(len(viewer.game.pacgums), 0)
            self.assertEqual(viewer.game.state, GUIStateEnum.All_Clear)
            self.assertEqual(viewer.game.player.lives, 3)

    def test_frozen_ghost_remains_an_obstacle(self) -> None:
        ghost = self.ghost((3, 0))
        self.assertEqual(self.auto.choose_direction(
            self.maze, self.player, self.gums, [ghost], self.canvas,
            ghosts_frozen=True), 'W')


class WallhackBoundaryTests(unittest.TestCase):
    def test_wallhack_skips_only_walls_and_keeps_both_bounds_checks(self) -> None:
        maze = Maze([[13, 7]])
        self.assertFalse(maze.can_move(0, 0, 'W', True))
        self.assertFalse(maze.can_move(1, 0, 'E', True))
        self.assertFalse(maze.can_move(-1, 0, 'E', True))
        self.assertFalse(maze.can_move(0, 0, 'invalid', True))
        self.assertTrue(Maze([[15, 15]]).can_move(0, 0, 'E', True))
        self.assertFalse(Maze([[15, 15]]).can_move(0, 0, 'E'))
        # Even an open boundary cell cannot leave the map without wallhack.
        self.assertFalse(Maze([[0]]).can_move(0, 0, 'E'))

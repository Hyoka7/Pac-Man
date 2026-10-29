"""Level resizing keeps positions, radii and pickups in the fixed window."""

from typing import Any, cast

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from mazegenerator import MazeGenerator

from models.models import Config, LevelConfig
from visualize.game import Game
from visualize.ghost import Ghost
from visualize.player import Player
from visualize.gui import GUI, GUIStateEnum
from visualize.maze import Maze
from visualize.maze_visualizer import MazeVisualizer
from visualize.visualizerutils import VisualizerUtils


class LevelLayoutTests(unittest.TestCase):
    def make_viewer(self) -> MazeVisualizer:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        config = Config(
            highscore_filename=str(Path(directory.name) / 'scores.json'),
            lives=4,
            levels=[
                LevelConfig(width=15, height=15, max_time=90),
                LevelConfig(width=25, height=15, max_time=80),
                LevelConfig(width=15, height=25, max_time=70),
            ],
        )
        generator = MazeGenerator(size=(15, 15), seed=42)
        viewer = MazeVisualizer(generator.maze, generator, config)
        viewer.width, viewer.height, viewer.margin = 1000, 800, 100
        viewer._update_layout()
        viewer.canvas = VisualizerUtils(
            1000, 800, viewer.cell_size, 100,
            memoryview(bytearray(4000 * 800)), 4000, 0,
            viewer.offset_x, viewer.offset_y,
        )
        viewer.game.player.place(viewer.canvas)
        for ghost in viewer.game.ghosts:
            ghost.place(viewer.canvas)
        viewer.game.pacgums.reset(viewer.game.maze, viewer.canvas, viewer.game.player.movement.cell)
        return viewer

    def assert_placements_fit(self, viewer: MazeVisualizer) -> None:
        maze, canvas = viewer.game.maze, viewer.canvas
        corners = [(0, 0), (0, maze.rows-1), (maze.cols-1, 0),
                   (maze.cols-1, maze.rows-1)]
        for ghost, corner in zip(viewer.game.ghosts, corners):
            self.assertEqual(ghost.cell, corner)
            self.assertEqual(ghost.movement.center, canvas.cell_center(*corner))
            self.assertEqual(ghost.respawn_remaining, 0.0)
        characters: list[Player | Ghost] = [viewer.game.player, *viewer.game.ghosts]
        for character in characters:
            self.assertAlmostEqual(character.radius, canvas.cell_size * 0.375)
            self.assertFalse(character.movement.moving)
            x, y = character.movement.center
            self.assertGreaterEqual(x-character.radius, 0)
            self.assertLess(x+character.radius, canvas.width)
            self.assertGreaterEqual(y-character.radius, 0)
            self.assertLess(y+character.radius, canvas.height)
        self.assertNotEqual(maze.maze[viewer.game.player.movement.cell[1]][
            viewer.game.player.movement.cell[0]], 15)
        self.assertEqual(viewer.game.pacgums.super_gums,
                         {canvas.cell_center(*cell) for cell in corners})
        self.assertEqual(len(viewer.game.pacgums),
                         sum(cell != 15 for row in maze.maze for cell in row)-1)
        self.assertEqual((canvas.offset_x, canvas.offset_y),
                         (viewer.offset_x, viewer.offset_y))
        self.assertEqual(canvas.cell_size, viewer.cell_size)
        self.assertEqual((canvas.width, canvas.height), (1000, 800))

    def test_mixed_sizes_then_restart_preserve_the_right_state(self) -> None:
        viewer = self.make_viewer()
        strategies = [ghost.strategy for ghost in viewer.game.ghosts]
        viewer.game.player.score, viewer.game.player.lives = 123, 2
        for expected_size, expected_time in (((25, 15), 80), ((15, 25), 70)):
            with self.subTest(size=expected_size):
                viewer.game.player.is_invincible = True
                viewer.game.player.invincible_remain = 3
                for ghost in viewer.game.ghosts:
                    ghost.respawn_remaining = 3.0
                viewer.next_level()
                self.assertEqual((viewer.game.maze.cols, viewer.game.maze.rows), expected_size)
                self.assert_placements_fit(viewer)
                self.assertEqual((viewer.game.player.score, viewer.game.player.lives), (123, 2))
                self.assertEqual(viewer.game.remaining_time, expected_time)
                self.assertFalse(viewer.game.player.is_invincible)
                self.assertEqual([g.strategy for g in viewer.game.ghosts], strategies)
        for ghost in viewer.game.ghosts:
            ghost.respawn_remaining = 3.0
        viewer.restart_game()
        self.assertEqual((viewer.game.level, viewer.game.maze.cols, viewer.game.maze.rows), (1, 15, 15))
        self.assertEqual((viewer.game.player.score, viewer.game.player.lives), (0, 4))
        self.assertEqual(viewer.game.remaining_time, 90)
        self.assert_placements_fit(viewer)

    def test_eaten_ghost_waits_after_reset_and_cannot_score_twice(self) -> None:
        viewer = self.make_viewer()
        viewer.closed = False
        viewer.game.state = GUIStateEnum.Playing
        viewer.last_time = 10.0
        self.enterContext(patch.object(viewer, "_draw", Mock()))
        viewer.game.player.is_invincible = True
        viewer.game.player.invincible_remain = 5.0
        ghost = viewer.game.ghosts[0]
        viewer.game.ghosts = [ghost]
        ghost.movement.cell = viewer.game.player.movement.cell
        ghost.movement.place(viewer.canvas)
        with redirect_stdout(StringIO()), patch(
            'visualize.maze_visualizer.time.monotonic', return_value=10.0
        ):
            viewer._on_loop()
        self.assertEqual(viewer.game.player.score, viewer.game.config.points_per_ghost)
        self.assertEqual(ghost.respawn_remaining, 5.0)
        self.assertEqual(ghost.movement.center, viewer.canvas.cell_center(0, 0))
        with patch('visualize.maze_visualizer.time.monotonic', return_value=10.1):
            viewer._on_loop()
        self.assertEqual(viewer.game.player.score, viewer.game.config.points_per_ghost)
        self.assertAlmostEqual(ghost.respawn_remaining, 4.9)
        self.assertEqual(ghost.movement.center, viewer.canvas.cell_center(0, 0))

    def test_skip_at_last_level_does_not_index_past_settings(self) -> None:
        viewer = self.make_viewer()
        viewer.game.level = viewer.game.max_level
        viewer.game.needs_redraw = False
        original_maze = viewer.game.maze
        viewer.next_level()
        self.assertEqual(viewer.game.state, GUIStateEnum.All_Clear)
        self.assertTrue(viewer.game.needs_redraw)
        self.assertEqual(viewer.game.level, viewer.game.max_level)
        self.assertIs(viewer.game.maze, original_maze)

    def test_viewer_initializes_numeric_cheat_command(self) -> None:
        viewer = self.make_viewer()
        results = [viewer.game.cheathandler.consume(ord(char)) for char in '3111696']
        self.assertEqual(results, [False] * 6 + [True])

    def test_layout_centers_both_axes_and_rejects_unrenderable_cells(self) -> None:
        viewer = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
        viewer.game = cast(Any, Game.__new__(Game))
        viewer.game.level_needs_placement = False
        viewer.canvas = Mock()
        viewer.gui = GUI()
        viewer.width, viewer.height, viewer.margin = 1000, 800, 100
        for cols, rows in ((15, 15), (25, 15), (15, 25)):
            viewer.game.maze = SimpleNamespace(cols=cols, rows=rows)
            viewer._update_layout()
            left, top = viewer.offset_x, viewer.offset_y
            right = viewer.width-left-(cols*viewer.cell_size+1)
            bottom = viewer.height-top-(rows*viewer.cell_size+1)
            self.assertLessEqual(abs(left-right), 1)
            self.assertLessEqual(abs(top-bottom), 1)
            self.assertGreaterEqual(min(left, top), viewer.margin)
        viewer.game.maze = SimpleNamespace(cols=2000, rows=2000)
        with self.assertRaises(ValueError):
            viewer._update_layout()

    def test_large_window_reserves_space_for_invincible_label(self) -> None:
        for width, height in ((800, 600), (2460, 1340), (4000, 2200)):
            with self.subTest(size=(width, height)):
                viewer = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
                viewer.game = cast(Any, Game.__new__(Game))
                viewer.game.level_needs_placement = False
                viewer.canvas = Mock()
                viewer.gui = GUI()
                viewer.width, viewer.height, viewer.margin = width, height, 100
                viewer.game.maze = SimpleNamespace(cols=15, rows=15)
                viewer._update_layout()
                maze_bottom = viewer.offset_y + viewer.game.maze.rows * viewer.cell_size
                bar_y = viewer.gui.bar_y
                with patch('visualize.image_renderer.ImageRenderer.draw_numeric_text') as draw:
                    viewer.gui.invinsible_time(Mock(), width, bar_y, 3.2)
                text_y = draw.call_args.args[2]
                self.assertGreater(text_y, maze_bottom)
                self.assertLessEqual(text_y + viewer.gui.font_size, bar_y)

    def test_walls_and_cell_centers_use_offsets_instead_of_margin(self) -> None:
        canvas = VisualizerUtils(
            100, 80, 20, 2, memoryview(bytearray(400*80)), 400, 0, 30, 25,
        )
        canvas.clear_image()
        Maze([[15]]).draw(canvas, (255, 255, 255), (255, 0, 0))
        self.assertEqual(canvas.cell_center(0, 0), (40.0, 35.0))
        def pixel(x: int, y: int) -> bytes:
            index = y*canvas.line_size+x*4
            return bytes(canvas.img_data[index:index+4])
        self.assertEqual(pixel(30, 25), canvas.color_bytes((255, 255, 255)))
        self.assertEqual(pixel(40, 35), canvas.color_bytes((255, 0, 0)))
        self.assertEqual(pixel(2, 2), canvas.color_bytes((0, 0, 0)))

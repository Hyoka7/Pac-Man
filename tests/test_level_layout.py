"""Level resizing keeps positions, radii and pickups in the fixed window."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from mazegenerator import MazeGenerator

from models.models import Config, LevelConfig
from visualize.gui import GUIStateEnum
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
        viewer.player.place(viewer.canvas)
        for ghost in viewer.ghosts:
            ghost.place(viewer.canvas)
        viewer.pacgums.reset(viewer.maze, viewer.canvas, viewer.player.movement.cell)
        return viewer

    def assert_placements_fit(self, viewer: MazeVisualizer) -> None:
        maze, canvas = viewer.maze, viewer.canvas
        corners = [(0, 0), (0, maze.rows-1), (maze.cols-1, 0),
                   (maze.cols-1, maze.rows-1)]
        for ghost, corner in zip(viewer.ghosts, corners):
            self.assertEqual(ghost.cell, corner)
            self.assertEqual(ghost.movement.center, canvas.cell_center(*corner))
        for character in [viewer.player, *viewer.ghosts]:
            self.assertAlmostEqual(character.radius, canvas.cell_size * 0.375)
            self.assertFalse(character.movement.moving)
            x, y = character.movement.center
            self.assertGreaterEqual(x-character.radius, 0)
            self.assertLess(x+character.radius, canvas.width)
            self.assertGreaterEqual(y-character.radius, 0)
            self.assertLess(y+character.radius, canvas.height)
        self.assertNotEqual(maze.maze[viewer.player.movement.cell[1]][
            viewer.player.movement.cell[0]], 15)
        self.assertEqual(viewer.pacgums.super_gums,
                         {canvas.cell_center(*cell) for cell in corners})
        self.assertEqual(len(viewer.pacgums),
                         sum(cell != 15 for row in maze.maze for cell in row)-1)
        self.assertEqual((canvas.offset_x, canvas.offset_y),
                         (viewer.offset_x, viewer.offset_y))
        self.assertEqual(canvas.cell_size, viewer.cell_size)
        self.assertEqual((canvas.width, canvas.height), (1000, 800))

    def test_mixed_sizes_then_restart_preserve_the_right_state(self) -> None:
        viewer = self.make_viewer()
        strategies = [ghost.strategy for ghost in viewer.ghosts]
        viewer.player.score, viewer.player.lives = 123, 2
        for expected_size, expected_time in (((25, 15), 80), ((15, 25), 70)):
            with self.subTest(size=expected_size):
                viewer.player.is_invincible = True
                viewer.player.invincible_remain = 3
                viewer.next_level()
                self.assertEqual((viewer.maze.cols, viewer.maze.rows), expected_size)
                self.assert_placements_fit(viewer)
                self.assertEqual((viewer.player.score, viewer.player.lives), (123, 2))
                self.assertEqual(viewer.remaining_time, expected_time)
                self.assertFalse(viewer.player.is_invincible)
                self.assertEqual([g.strategy for g in viewer.ghosts], strategies)
        viewer.restart_game()
        self.assertEqual((viewer.level, viewer.maze.cols, viewer.maze.rows), (1, 15, 15))
        self.assertEqual((viewer.player.score, viewer.player.lives), (0, 4))
        self.assertEqual(viewer.remaining_time, 90)
        self.assert_placements_fit(viewer)

    def test_skip_at_last_level_does_not_index_past_settings(self) -> None:
        viewer = self.make_viewer()
        viewer.level = viewer.max_level
        viewer.needs_redraw = False
        original_maze = viewer.maze
        viewer.next_level()
        self.assertEqual(viewer.state, GUIStateEnum.All_Clear)
        self.assertTrue(viewer.needs_redraw)
        self.assertEqual(viewer.level, viewer.max_level)
        self.assertIs(viewer.maze, original_maze)

    def test_layout_centers_both_axes_and_rejects_unrenderable_cells(self) -> None:
        viewer = MazeVisualizer.__new__(MazeVisualizer)
        viewer.width, viewer.height, viewer.margin = 1000, 800, 100
        for cols, rows in ((15, 15), (25, 15), (15, 25)):
            viewer.maze = SimpleNamespace(cols=cols, rows=rows)
            viewer._update_layout()
            left, top = viewer.offset_x, viewer.offset_y
            right = viewer.width-left-(cols*viewer.cell_size+1)
            bottom = viewer.height-top-(rows*viewer.cell_size+1)
            self.assertLessEqual(abs(left-right), 1)
            self.assertLessEqual(abs(top-bottom), 1)
            self.assertGreaterEqual(min(left, top), viewer.margin)
        viewer.maze = SimpleNamespace(cols=2000, rows=2000)
        with self.assertRaises(ValueError):
            viewer._update_layout()

    def test_walls_and_cell_centers_use_offsets_instead_of_margin(self) -> None:
        canvas = VisualizerUtils(
            100, 80, 20, 2, memoryview(bytearray(400*80)), 400, 0, 30, 25,
        )
        canvas.clear_image()
        Maze([[15]]).draw(canvas, (255, 255, 255), (255, 0, 0))
        self.assertEqual(canvas.cell_center(0, 0), (40.0, 35.0))
        def pixel(x, y):
            index = y*canvas.line_size+x*4
            return bytes(canvas.img_data[index:index+4])
        self.assertEqual(pixel(30, 25), canvas.color_bytes((255, 255, 255)))
        self.assertEqual(pixel(40, 35), canvas.color_bytes((255, 0, 0)))
        self.assertEqual(pixel(2, 2), canvas.color_bytes((0, 0, 0)))

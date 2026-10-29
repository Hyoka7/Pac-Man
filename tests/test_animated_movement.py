"""Shared frame-by-frame movement and character integration checks."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from models.models import Config, LevelConfig
from visualize.gui import GUIStateEnum

from visualize import MazeVisualizer
from visualize.ghost import Ghost
from visualize.maze import Maze
from visualize.movement import Movement
from visualize.pacgums import Pacgums
from visualize.player import Player
from visualize.strategy import BFSStrategy
from visualize.visualizerutils import VisualizerUtils


def make_canvas() -> VisualizerUtils:
    """Create an image and layout without opening an MLX window."""
    return VisualizerUtils(137, 137, 32, 20, memoryview(bytearray(548 * 137)), 548, 0, 20, 20)


class AnimatedMovementTests(unittest.TestCase):
    """Verify timing, arrival and shared movement ownership."""

    def setUp(self) -> None:
        """Use a three-cell corridor with walls at both ends."""
        self.maze = Maze([[13, 5, 7]])
        self.canvas = make_canvas()

    def test_animation_keeps_cell_until_arrival(self) -> None:
        """The drawing position moves between cells before logical arrival."""
        motion = Movement((0, 0), speed=2)
        motion.place(self.canvas)
        self.assertTrue(motion.start("E", self.maze, self.canvas))
        self.assertFalse(motion.update(0.25, self.canvas))
        self.assertEqual(motion.center, (52.0, 36.0))
        self.assertEqual(motion.cell, (0, 0))
        self.assertTrue(motion.moving)
        self.assertTrue(motion.update(0.25, self.canvas))
        self.assertEqual(motion.center, (68.0, 36.0))
        self.assertEqual(motion.cell, (1, 0))
        self.assertFalse(motion.moving)
        self.assertFalse(motion.update(0.25, self.canvas))

    def test_blocked_direction_does_not_start(self) -> None:
        """Walls and bounds prevent an animation from starting."""
        motion = Movement((0, 0))
        motion.place(self.canvas)
        for direction in ("N", "W", "S"):
            self.assertFalse(motion.start(direction, self.maze, self.canvas))
        self.assertFalse(motion.moving)
        self.assertEqual(motion.center, (36.0, 36.0))

    def test_start_during_motion_does_not_reset_position(self) -> None:
        """Direction reservations belong to the character, not movement."""
        motion = Movement((0, 0), speed=2)
        motion.start("E", self.maze, self.canvas)
        motion.update(0.125, self.canvas)
        self.assertFalse(motion.start("W", self.maze, self.canvas))
        self.assertEqual(motion.center, (44.0, 36.0))
        self.assertEqual(motion.direction, "E")

    def test_elapsed_time_is_independent_of_frame_count(self) -> None:
        """Equivalent total elapsed time gives the same drawing position."""
        a = Movement((0, 0), speed=2)
        b = Movement((0, 0), speed=2)
        a.start("E", self.maze, self.canvas)
        b.start("E", self.maze, self.canvas)
        a.update(0.1, self.canvas)
        for _ in range(10):
            b.update(0.01, self.canvas)
        self.assertAlmostEqual(a.center[0], b.center[0])

    def test_player_turns_and_consumes_only_on_arrival(self) -> None:
        """A queued turn and pacgum consumption survive the extraction."""
        maze = Maze([[13, 3], [15, 14]])
        player = Player()
        player.movement.speed = 5.0
        gums = Pacgums(maze.rows, maze.cols)
        player.place(self.canvas)
        gums.reset(maze, self.canvas, (0, 0))
        player.request_move("E", maze, self.canvas)
        player.request_move("S", maze, self.canvas)
        player.update(0.1, maze, self.canvas, gums)
        self.assertEqual(player.movement.cell, (0, 0))
        self.assertEqual(len(gums), 2)
        player.update(0.1, maze, self.canvas, gums)
        self.assertEqual(player.movement.cell, (1, 0))
        self.assertEqual(player.movement.direction, "S")
        self.assertTrue(player.movement.moving)
        self.assertEqual(len(gums), 1)

    def test_ghost_uses_intermediate_pixel_positions(self) -> None:
        """A ghost uses the shared animation without eating pacgums."""
        ghost = Ghost((2, 0), BFSStrategy())
        ghost.place(self.canvas)
        ghost.update(0.05, self.maze, self.canvas, (0, 0), eatable=False)
        self.assertEqual(ghost.cell, (2, 0))
        self.assertLess(ghost.movement.center[0], 100.0)
        self.assertGreater(ghost.movement.center[0], 68.0)
        self.canvas.clear_image()
        ghost.draw(self.canvas, eatable=False, eatable_remain=0.0)
        offset = 30 * self.canvas.line_size + 105 * 4
        self.assertEqual(
            bytes(self.canvas.img_data[offset : offset + 4]), bytes([0, 0, 0, 255])
        )
        ghost.update(0.3, self.maze, self.canvas, (0, 0), eatable=False)
        self.assertEqual(ghost.cell, (1, 0))
        self.canvas.clear_image()
        ghost.draw(self.canvas, eatable=False, eatable_remain=0.0)
        offset = 36 * self.canvas.line_size + 68 * 4
        self.assertEqual(
            bytes(self.canvas.img_data[offset : offset + 4]), bytes([0, 0, 255, 255])
        )

    def test_isolated_ghost_stays_still(self) -> None:
        """Direction selection may return None when there is no passage."""
        ghost = Ghost((0, 0), BFSStrategy())
        ghost.place(self.canvas)
        ghost.update(1.0, Maze([[15]]), self.canvas, (1, 0), eatable=False)
        self.assertFalse(ghost.movement.moving)
        self.assertEqual(ghost.cell, (0, 0))

    def test_frame_loop_advances_both_characters(self) -> None:
        """The frame loop passes elapsed time to both animation owners."""
        with TemporaryDirectory() as directory:
            config = Config(
                highscore_filename=str(Path(directory) / "scores.json"),
                levels=[LevelConfig(width=5, height=1)],
            )
            viewer = MazeVisualizer([[13, 5, 5, 5, 7]], Mock(), config)
            viewer.game.state = GUIStateEnum.Playing
            viewer.game.ghosts = [Ghost((0, 0), BFSStrategy())]
            viewer.game.player.movement.speed = 5.0
            viewer.game.ghosts[0].movement.speed = 3.0
            viewer.canvas = self.canvas
            viewer.game.player.place(self.canvas)
            viewer.game.ghosts[0].place(self.canvas)
            viewer.game.pacgums.reset(viewer.game.maze, self.canvas, viewer.game.player.movement.cell)
            draw: Mock = self.enterContext(patch.object(viewer, "_draw"))
            viewer.closed = False
            viewer.last_time = 10.0
            viewer._on_key(65363)
            with patch("visualize.maze_visualizer.time.monotonic", return_value=10.05):
                viewer._on_loop()
            self.assertAlmostEqual(viewer.game.player.movement.center[0], 108.0)
            self.assertAlmostEqual(viewer.game.ghosts[0].movement.center[0], 40.8)
            self.assertEqual(viewer.game.player.movement.cell, (2, 0))
            self.assertEqual(viewer.game.ghosts[0].cell, (0, 0))
            self.assertAlmostEqual(viewer.game.remaining_time, 89.95)
            draw.assert_called_once()



if __name__ == "__main__":
    unittest.main()

"""Trial controls: immediate reversal and a small late-turn window."""

import unittest

from visualize.maze import Maze
from visualize.pacgums import Pacgums
from visualize.player import Player
from visualize.visualizerutils import VisualizerUtils


class PlayerControlTests(unittest.TestCase):
    """Verify responsiveness while keeping corridor and wall constraints."""

    def setUp(self) -> None:
        """Use a junction with a north exit and a corridor to the east."""
        self.maze = Maze([[15, 11, 15], [13, 4, 7]])
        self.canvas = VisualizerUtils(
            137, 105, 32, 20, memoryview(bytearray(548 * 105)), 548, 0
        )
        self.player = Player((1, 1))
        self.player.place(self.canvas)
        self.gums = Pacgums()
        self.gums.reset(self.maze, self.canvas, (1, 1))

    def test_turn_just_after_junction_is_applied_immediately(self) -> None:
        """An input just past the center should not miss the junction."""
        p = self.player
        p.request_move('E', self.maze, self.canvas)
        p.update(0.02, self.maze, self.canvas, self.gums)
        p.request_move('N', self.maze, self.canvas)
        self.assertEqual(p.movement.direction, 'N')
        self.assertEqual(p.movement.center, (68.0, 68.0))
        self.assertEqual(p.movement.target_cell, (1, 0))
        self.assertIsNone(p.reserved_move)

    def test_turn_far_from_center_remains_reserved(self) -> None:
        """Turning in the middle of a cell must not cut through a wall."""
        p = self.player
        p.request_move('E', self.maze, self.canvas)
        p.update(0.06, self.maze, self.canvas, self.gums)
        before = p.movement.center
        p.request_move('N', self.maze, self.canvas)
        self.assertEqual(p.movement.direction, 'E')
        self.assertEqual(p.movement.center, before)
        self.assertEqual(p.reserved_move, 'N')

    def test_blocked_turn_does_not_snap_back(self) -> None:
        """A nearby center is not enough if the requested exit is blocked."""
        p = self.player
        p.request_move('E', self.maze, self.canvas)
        p.update(0.02, self.maze, self.canvas, self.gums)
        before = p.movement.center
        p.request_move('S', self.maze, self.canvas)
        self.assertEqual(p.movement.direction, 'E')
        self.assertEqual(p.movement.center, before)

    def test_reverse_moves_back_without_waiting_or_teleporting(self) -> None:
        """The next frame should move toward the original center."""
        p = self.player
        p.request_move('E', self.maze, self.canvas)
        p.update(0.06, self.maze, self.canvas, self.gums)
        before = p.movement.center
        p.request_move('W', self.maze, self.canvas)
        self.assertEqual(p.movement.center, before)
        self.assertEqual(p.movement.direction, 'W')
        self.assertEqual(p.movement.target_cell, (1, 1))
        p.update(0.01, self.maze, self.canvas, self.gums)
        self.assertLess(p.movement.center[0], before[0])
        self.assertEqual(p.movement.cell, (1, 1))

    def test_reversing_twice_preserves_position(self) -> None:
        """Quick opposite inputs can alternate without a snap to a cell."""
        p = self.player
        p.request_move('E', self.maze, self.canvas)
        p.update(0.06, self.maze, self.canvas, self.gums)
        before = p.movement.center
        p.request_move('W', self.maze, self.canvas)
        p.request_move('E', self.maze, self.canvas)
        self.assertEqual(p.movement.center, before)
        self.assertEqual(p.movement.target_cell, (2, 1))
        self.assertEqual(p.movement.direction, 'E')

    def test_continuing_straight_does_not_snap_back(self) -> None:
        """Key repeat in the current direction must not reset progress."""
        p = self.player
        p.request_move('E', self.maze, self.canvas)
        p.update(0.02, self.maze, self.canvas, self.gums)
        before = p.movement.center
        p.request_move('E', self.maze, self.canvas)
        self.assertEqual(p.movement.center, before)


if __name__ == '__main__':
    unittest.main()

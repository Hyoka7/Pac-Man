"""Ghost movement delegates direction selection to its Strategy instance."""

import unittest

from visualize.ghost import Ghost
from visualize.maze import Maze
from visualize.strategy import BFSStrategy, RandomStrategy
from visualize.visualizerutils import VisualizerUtils


def make_canvas() -> VisualizerUtils:
    """Create the layout used by cell-to-cell movement tests."""
    return VisualizerUtils(
        137, 137, 32, 20, memoryview(bytearray(548 * 137)), 548, 0
    )


class GhostNavigationTests(unittest.TestCase):
    """Verify the current strategy-based navigation, including reversals."""

    def test_bfs_strategy_starts_shortest_detour(self) -> None:
        """The chosen BFS direction feeds the existing smooth animation."""
        maze = Maze([[9, 7, 11], [12, 5, 6]])
        canvas = make_canvas()
        ghost = Ghost((0, 0), BFSStrategy())
        ghost.place(canvas)
        ghost.update(0.1, maze, canvas, (2, 0))
        self.assertEqual(ghost.direction, 'S')
        self.assertEqual(ghost.movement.target_cell, (0, 1))
        self.assertEqual(ghost.cell, (0, 0))
        self.assertGreater(ghost.movement.center[1], 36.0)
        self.assertLess(ghost.movement.center[1], 68.0)

    def test_strategy_may_reverse_to_chase_player(self) -> None:
        """Reverse prevention was removed; the strategy may choose any exit."""
        maze = Maze([[13, 5, 7]])
        canvas = make_canvas()
        ghost = Ghost((0, 0), BFSStrategy())
        ghost.movement.start('E', maze, canvas)
        ghost.movement.update(1 / ghost.movement.speed, canvas)
        ghost.update(0.1, maze, canvas, (0, 0))
        self.assertEqual(ghost.direction, 'W')
        self.assertEqual(ghost.movement.target_cell, (0, 0))

    def test_unreachable_player_does_not_start_animation(self) -> None:
        """A None direction is handled before starting movement."""
        canvas = make_canvas()
        ghost = Ghost((0, 0), BFSStrategy())
        ghost.place(canvas)
        ghost.update(0.1, Maze([[15, 15]]), canvas, (1, 0))
        self.assertFalse(ghost.movement.moving)
        self.assertEqual(ghost.movement.center, (36.0, 36.0))

    def test_isolated_random_ghost_stays_still(self) -> None:
        """The same None handling also applies to RandomStrategy."""
        canvas = make_canvas()
        ghost = Ghost((0, 0), RandomStrategy())
        ghost.place(canvas)
        ghost.update(0.1, Maze([[15]]), canvas, (1, 0))
        self.assertFalse(ghost.movement.moving)

    def test_two_ghosts_can_share_one_bfs_strategy(self) -> None:
        """Movement remains independent while the distance map is shared."""
        maze = Maze([[13, 5, 7]])
        canvas = make_canvas()
        strategy = BFSStrategy()
        left = Ghost((0, 0), strategy)
        right = Ghost((2, 0), strategy)
        for ghost in (left, right):
            ghost.place(canvas)
            ghost.update(0.1, maze, canvas, (1, 0))
        self.assertIs(left.strategy, right.strategy)
        self.assertEqual(left.direction, 'E')
        self.assertEqual(right.direction, 'W')
        self.assertEqual(left.movement.target_cell, (1, 0))
        self.assertEqual(right.movement.target_cell, (1, 0))


if __name__ == '__main__':
    unittest.main()

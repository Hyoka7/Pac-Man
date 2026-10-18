"""All-source BFS runs when the maze is created, before gameplay."""

import unittest

from visualize.maze import Maze
from visualize.strategy import BFSStrategy


class CountingMaze(Maze):
    """Observe actual traversal during construction and strategy requests."""

    def __init__(self, cells: list[list[int]]) -> None:
        """Initialize the counter before Maze performs its startup searches."""
        self.checks = 0
        super().__init__(cells)

    def can_move(self, x: int, y: int, direction: str) -> bool:
        """Count wall checks while using normal maze behavior."""
        self.checks += 1
        return super().can_move(x, y, direction)


class MazeDistanceTests(unittest.TestCase):
    """Verify complete distance tables and no searches while chasing."""

    def test_all_walkable_sources_are_ready_on_construction(self) -> None:
        """Each source already has distances to all its reachable cells."""
        maze = Maze([[13, 5, 7]])
        self.assertEqual(maze.distances, {
            (0, 0): {(0, 0): 0, (1, 0): 1, (2, 0): 2},
            (1, 0): {(1, 0): 0, (0, 0): 1, (2, 0): 1},
            (2, 0): {(2, 0): 0, (1, 0): 1, (0, 0): 2},
        })

    def test_blocked_cells_are_not_sources_or_destinations(self) -> None:
        """The enclosed 42 pattern is excluded from path tables."""
        maze = Maze([[13, 7, 15]])
        self.assertNotIn((2, 0), maze.distances)
        for distances in maze.distances.values():
            self.assertNotIn((2, 0), distances)

    def test_disconnected_components_remain_unreachable(self) -> None:
        """A missing pair must not be interpreted as a zero-length path."""
        maze = Maze([[13, 7, 13, 7]])
        self.assertNotIn((3, 0), maze.distances[(0, 0)])
        self.assertEqual(maze.distances[(2, 0)][(3, 0)], 1)

    def test_player_changes_and_other_strategies_do_not_trigger_bfs(self) -> None:
        """Only up to four neighboring exits are checked during each choice."""
        maze = CountingMaze([[13, 5, 5, 5, 7]])
        self.assertGreater(maze.checks, 0)
        for strategy, player, expected in (
            (BFSStrategy(), (0, 0), 'W'),
            (BFSStrategy(), (4, 0), 'E'),
            (BFSStrategy(), (1, 0), 'W'),
        ):
            before = maze.checks
            self.assertEqual(strategy.choose_direction(maze, (2, 0), player),
                             expected)
            self.assertLessEqual(maze.checks - before, 4)


if __name__ == '__main__':
    unittest.main()

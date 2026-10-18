"""Shortest-path strategies, distance-map caching and unreachable targets."""

import unittest

from visualize.maze import Maze
from visualize.strategy import BFSStrategy, RandomStrategy


class CountingMaze(Maze):
    """Count graph visits without replacing the real maze traversal."""

    def __init__(self, cells: list[list[int]]) -> None:
        """Initialize a maze and its traversal counter."""
        self.checks = 0
        super().__init__(cells)

    def can_move(self, x: int, y: int, direction: str) -> bool:
        """Count and perform the original wall check."""
        self.checks += 1
        return super().can_move(x, y, direction)


class BFSStrategyTests(unittest.TestCase):
    """Verify wall-aware paths using the level's precomputed distance table."""

    def test_takes_detour_instead_of_greedy_dead_end(self) -> None:
        """The tempting east branch is longer than going south first."""
        maze = Maze([[9, 7, 11], [12, 5, 6]])
        self.assertEqual(BFSStrategy().choose_direction(maze, (0, 0), (2, 0)),
                         'S')

    def test_reaches_player_by_shortest_route(self) -> None:
        """Following the distance gradient reaches the player in four moves."""
        maze = Maze([[9, 7, 11], [12, 5, 6]])
        strategy = BFSStrategy()
        cell = (0, 0)
        route = [cell]
        for _ in range(4):
            direction = strategy.choose_direction(maze, cell, (2, 0))
            self.assertIsNotNone(direction)
            self.assertTrue(maze.can_move(*cell, direction))
            cell = maze.next_cell(*cell, direction)
            route.append(cell)
        self.assertEqual(route, [(0, 0), (0, 1), (1, 1), (2, 1), (2, 0)])

    def test_returns_none_when_already_at_player(self) -> None:
        """No step is needed when ghost and player share a cell."""
        self.assertIsNone(BFSStrategy().choose_direction(Maze([[0]]), (0, 0), (0, 0)))

    def test_returns_none_for_unreachable_player(self) -> None:
        """Disconnected cells have no path."""
        self.assertIsNone(BFSStrategy().choose_direction(Maze([[15, 15]]),
                                                        (0, 0), (1, 0)))

    def test_returns_none_for_invalid_coordinates(self) -> None:
        """Out-of-bounds inputs cannot produce a movement direction."""
        strategy = BFSStrategy()
        maze = Maze([[13, 7]])
        self.assertIsNone(strategy.choose_direction(maze, (-1, 0), (1, 0)))
        self.assertIsNone(strategy.choose_direction(maze, (0, 0), (2, 0)))

    def test_reuses_search_for_different_ghosts(self) -> None:
        """Different ghosts reuse the level table without additional searches."""
        maze = CountingMaze([[13, 5, 5, 5, 7]])
        strategy = BFSStrategy()
        self.assertEqual(strategy.choose_direction(maze, (0, 0), (4, 0)), 'E')
        after_first = maze.checks
        self.assertGreater(after_first, 4)
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (4, 0)), 'E')
        self.assertLessEqual(maze.checks - after_first, 4)

    def test_uses_precomputed_distances_after_player_moves(self) -> None:
        """A new target selects a different entry in the same distance table."""
        maze = Maze([[13, 5, 7]])
        strategy = BFSStrategy()
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (0, 0)), 'W')
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (2, 0)), 'E')

    def test_uses_new_levels_distance_table(self) -> None:
        """A new Maze object supplies its own table even at the same target."""
        strategy = BFSStrategy()
        self.assertEqual(strategy.choose_direction(Maze([[13, 7]]),
                                                   (0, 0), (1, 0)), 'E')
        self.assertIsNone(strategy.choose_direction(Maze([[15, 15]]),
                                                    (0, 0), (1, 0)))


class RandomStrategyTests(unittest.TestCase):
    """Random movement still respects walls and handles empty candidates."""

    def test_only_open_direction_is_selected(self) -> None:
        """A one-exit cell has a deterministic random choice."""
        self.assertEqual(RandomStrategy().choose_direction(Maze([[13, 7]]),
                                                          (0, 0), (1, 0)), 'E')

    def test_isolated_cell_returns_none(self) -> None:
        """An empty candidate list must not raise from random.choice."""
        self.assertIsNone(RandomStrategy().choose_direction(Maze([[15]]),
                                                           (0, 0), (1, 0)))


if __name__ == '__main__':
    unittest.main()

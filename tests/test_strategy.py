"""Shortest-path strategies, distance-map caching and unreachable targets."""

import unittest
from unittest.mock import patch

from visualize.maze import Maze
from visualize.strategy import (
    AmbushStrategy, BFSStrategy, BlockStrategy, RandomStrategy, ReverseAmbushStrategy,
)


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
        self.assertEqual(BFSStrategy().choose_direction(maze, (0, 0), (2, 0), player_dir="E"),
                         'S')

    def test_reaches_player_by_shortest_route(self) -> None:
        """Following the distance gradient reaches the player in four moves."""
        maze = Maze([[9, 7, 11], [12, 5, 6]])
        strategy = BFSStrategy()
        cell = (0, 0)
        route = [cell]
        for _ in range(4):
            direction = strategy.choose_direction(maze, cell, (2, 0), player_dir="E")
            assert direction is not None
            self.assertTrue(maze.can_move(*cell, direction))
            cell = maze.next_cell(*cell, direction)
            route.append(cell)
        self.assertEqual(route, [(0, 0), (0, 1), (1, 1), (2, 1), (2, 0)])

    def test_either_equally_short_direction_can_be_selected(self) -> None:
        maze = Maze([[9, 3], [12, 6]])
        strategy = BFSStrategy()
        for index, expected in ((0, 'E'), (-1, 'S')):
            with self.subTest(selection=index), patch(
                'visualize.strategy.random.choice', side_effect=lambda choices: choices[index],
            ):
                direction = strategy.choose_direction(maze, (0, 0), (1, 1), player_dir="E")
                self.assertEqual(direction, expected)
                assert direction is not None
                neighbor = maze.next_cell(0, 0, direction)
                self.assertEqual(maze.distances[neighbor][(1, 1)], 1)

    def test_longer_open_directions_are_excluded_from_random_selection(self) -> None:
        maze = Maze([[9, 1, 3], [8, 0, 2], [12, 4, 6]])

        def select_last_shortest(choices: list[str]) -> str:
            # S and W are open too, but move farther from the target.
            self.assertEqual(set(choices), {'N', 'E'})
            return choices[-1]

        with patch('visualize.strategy.random.choice', side_effect=select_last_shortest):
            direction = BFSStrategy().choose_direction(maze, (1, 1), (2, 0), player_dir="E")
        self.assertEqual(direction, 'E')
        assert direction is not None
        self.assertEqual(maze.distances[maze.next_cell(1, 1, direction)][(2, 0)], 1)

    def test_returns_none_when_already_at_player(self) -> None:
        """No step is needed when ghost and player share a cell."""
        self.assertIsNone(BFSStrategy().choose_direction(Maze([[0]]), (0, 0), (0, 0), player_dir="E"))

    def test_returns_none_for_unreachable_player(self) -> None:
        """Disconnected cells have no path."""
        self.assertIsNone(BFSStrategy().choose_direction(Maze([[15, 15]]),
                                                        (0, 0), (1, 0), player_dir="E"))

    def test_returns_none_for_invalid_coordinates(self) -> None:
        """Out-of-bounds inputs cannot produce a movement direction."""
        strategy = BFSStrategy()
        maze = Maze([[13, 7]])
        self.assertIsNone(strategy.choose_direction(maze, (-1, 0), (1, 0), player_dir="E"))
        self.assertIsNone(strategy.choose_direction(maze, (0, 0), (2, 0), player_dir="E"))

    def test_reuses_search_for_different_ghosts(self) -> None:
        """Different ghosts reuse the level table without additional searches."""
        maze = CountingMaze([[13, 5, 5, 5, 7]])
        strategy = BFSStrategy()
        self.assertEqual(strategy.choose_direction(maze, (0, 0), (4, 0), player_dir="E"), 'E')
        after_first = maze.checks
        self.assertGreater(after_first, 4)
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (4, 0), player_dir="E"), 'E')
        self.assertLessEqual(maze.checks - after_first, 4)

    def test_uses_precomputed_distances_after_player_moves(self) -> None:
        """A new target selects a different entry in the same distance table."""
        maze = Maze([[13, 5, 7]])
        strategy = BFSStrategy()
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (0, 0), player_dir="E"), 'W')
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (2, 0), player_dir="E"), 'E')

    def test_uses_new_levels_distance_table(self) -> None:
        """A new Maze object supplies its own table even at the same target."""
        strategy = BFSStrategy()
        self.assertEqual(strategy.choose_direction(Maze([[13, 7]]),
                                                   (0, 0), (1, 0), player_dir="E"), 'E')
        self.assertIsNone(strategy.choose_direction(Maze([[15, 15]]),
                                                    (0, 0), (1, 0), player_dir="E"))


class AmbushStrategyTests(unittest.TestCase):
    def test_target_ahead_makes_ghost_intercept_instead_of_following(self) -> None:
        maze = Maze([[13, 5, 5, 5, 5, 5, 7]])
        strategy = AmbushStrategy()
        self.assertEqual(strategy.choose_direction(maze, (1, 0), (0, 0), 'E'), 'E')
        self.assertEqual(strategy.choose_direction(maze, (5, 0), (6, 0), 'W'), 'W')

    def test_vertical_player_heading_is_used(self) -> None:
        maze = Maze([[11], [10], [10], [10], [10], [10], [14]])
        strategy = AmbushStrategy()
        self.assertEqual(strategy.choose_direction(maze, (0, 1), (0, 0), 'S'), 'S')
        self.assertEqual(strategy.choose_direction(maze, (0, 5), (0, 6), 'N'), 'N')

    def test_wall_and_map_edge_stop_prediction(self) -> None:
        strategy = AmbushStrategy()
        maze = Maze([[13, 7]])
        self.assertIsNone(strategy.choose_direction(maze, (1, 0), (0, 0), 'E'))
        self.assertEqual(strategy.choose_direction(maze, (0, 0), (1, 0), 'E'), 'E')
        detour = Maze([[9, 7, 11], [12, 5, 6]])
        self.assertEqual(strategy.choose_direction(detour, (2, 0), (1, 0), 'E'), 'S')

    def test_holds_exactly_three_cells_ahead(self) -> None:
        maze = Maze([[13, 5, 5, 5, 5, 5, 7]])
        self.assertIsNone(AmbushStrategy().choose_direction(maze, (3, 0), (0, 0), 'E'))


class ReverseAmbushStrategyTests(unittest.TestCase):
    def test_targets_behind_the_player_in_all_four_directions(self) -> None:
        horizontal = Maze([[13, 5, 5, 5, 5, 5, 7]])
        vertical = Maze([[11], [10], [10], [10], [10], [10], [14]])
        strategy = ReverseAmbushStrategy()
        for maze, ghost, player, heading, expected in (
            (horizontal, (2, 0), (3, 0), 'E', 'W'),
            (horizontal, (4, 0), (3, 0), 'W', 'E'),
            (vertical, (0, 2), (0, 3), 'S', 'N'),
            (vertical, (0, 4), (0, 3), 'N', 'S'),
        ):
            with self.subTest(heading=heading):
                self.assertEqual(strategy.choose_direction(maze, ghost, player, heading), expected)

    def test_blocked_rear_falls_back_to_the_player_cell(self) -> None:
        maze = Maze([[13, 5, 7]])
        self.assertEqual(ReverseAmbushStrategy().choose_direction(
            maze, (2, 0), (0, 0), 'E'), 'W')

    def test_waits_exactly_three_cells_behind(self) -> None:
        maze = Maze([[13, 5, 5, 5, 5, 5, 7]])
        self.assertIsNone(ReverseAmbushStrategy().choose_direction(
            maze, (0, 0), (3, 0), 'E'))


class BlockStrategyTests(unittest.TestCase):
    def test_horizontal_player_heading_targets_north_or_south_exit(self) -> None:
        maze = Maze([[9, 1, 3], [8, 0, 2], [12, 4, 6]])
        # The chosen north exit is east of the ghost, so returning N would be wrong.
        with patch('visualize.strategy.random.choice', side_effect=lambda choices: choices[0]):
            self.assertEqual(BlockStrategy().choose_direction(
                maze, (0, 0), (1, 1), 'E'), 'E')

    def test_vertical_player_heading_targets_east_or_west_exit(self) -> None:
        maze = Maze([[9, 1, 3], [8, 0, 2], [12, 4, 6]])
        with patch('visualize.strategy.random.choice', side_effect=lambda choices: choices[0]):
            self.assertEqual(BlockStrategy().choose_direction(
                maze, (2, 0), (1, 1), 'N'), 'S')

    def test_routes_around_walls_to_the_selected_exit(self) -> None:
        maze = Maze([[9, 7, 11], [12, 5, 6]])
        direction = BlockStrategy().choose_direction(maze, (1, 0), (2, 0), 'E')
        self.assertEqual(direction, 'W')
        self.assertTrue(maze.can_move(1, 0, direction))

    def test_no_side_exit_falls_back_to_direct_chase(self) -> None:
        self.assertEqual(BlockStrategy().choose_direction(
            Maze([[13, 5, 5, 5, 7]]), (4, 0), (0, 0), 'E'), 'W')
        self.assertIsNone(BlockStrategy().choose_direction(
            Maze([[15, 15]]), (0, 0), (1, 0), 'E'))

    def test_waits_when_already_at_the_selected_exit(self) -> None:
        maze = Maze([[9, 1, 3], [8, 0, 2], [12, 4, 6]])
        with patch('visualize.strategy.random.choice', side_effect=lambda choices: choices[0]):
            self.assertIsNone(BlockStrategy().choose_direction(
                maze, (1, 0), (1, 1), 'E'))


class RandomStrategyTests(unittest.TestCase):
    """Random movement still respects walls and handles empty candidates."""

    def test_only_open_direction_is_selected(self) -> None:
        """A one-exit cell has a deterministic random choice."""
        self.assertEqual(RandomStrategy().choose_direction(Maze([[13, 7]]),
                                                          (0, 0), (1, 0), player_dir="E"), 'E')

    def test_isolated_cell_returns_none(self) -> None:
        """An empty candidate list must not raise from random.choice."""
        self.assertIsNone(RandomStrategy().choose_direction(Maze([[15]]),
                                                           (0, 0), (1, 0), player_dir="E"))


if __name__ == '__main__':
    unittest.main()

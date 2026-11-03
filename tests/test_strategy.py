"""Shortest-path strategies, distance-map caching and unreachable targets."""

import unittest
from unittest.mock import patch

from pacman.game.maze import Maze
from pacman.game.strategy import (
    AmbushStrategy, BFSStrategy, FleeBFSStrategy, InkyStrategy, ReverseAmbushStrategy,
)


class BFSStrategyTests(unittest.TestCase):
    """Verify wall-aware paths using the level's precomputed distance table."""

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
                'pacman.game.strategy.random.choice', side_effect=lambda choices: choices[index],
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

        with patch('pacman.game.strategy.random.choice', side_effect=select_last_shortest):
            direction = BFSStrategy().choose_direction(maze, (1, 1), (2, 0), player_dir="E")
        self.assertEqual(direction, 'E')
        assert direction is not None
        self.assertEqual(maze.distances[maze.next_cell(1, 1, direction)][(2, 0)], 1)

    def test_no_step_for_arrival_unreachable_or_invalid_positions(self) -> None:
        strategy = BFSStrategy()
        for label, cells, ghost, player in (
            ('arrived', [[13, 7]], (0, 0), (0, 0)),
            ('unreachable', [[13, 7, 13, 7]], (0, 0), (3, 0)),
            ('invalid ghost', [[13, 7]], (-1, 0), (1, 0)),
            ('invalid target', [[13, 7]], (0, 0), (2, 0)),
        ):
            with self.subTest(case=label):
                self.assertIsNone(strategy.choose_direction(
                    Maze(cells), ghost, player, player_dir='E'))

    def test_explicit_target_overrides_the_personality_goal(self) -> None:
        maze = Maze([[13, 5, 5, 5, 7]])
        # Ambush would head east; the supplied target must send it west.
        self.assertEqual(AmbushStrategy().choose_direction(
            maze, (1, 0), (2, 0), 'E', target=(0, 0)), 'W')

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


class FleeStrategyTests(unittest.TestCase):
    def test_equal_distance_exits_keep_existing_north_first_priority(self) -> None:
        maze = Maze([[9, 1, 3], [8, 0, 2], [12, 4, 6]])
        self.assertEqual(FleeBFSStrategy().choose_direction(
            maze, (1, 1), (1, 1), 'E'), 'N')


class AmbushStrategyTests(unittest.TestCase):
    def test_configurable_lookahead_changes_the_interception_goal(self) -> None:
        maze = Maze([[13, 5, 5, 5, 7]])
        self.assertEqual(AmbushStrategy(lookahead=2).choose_target(
            maze, (4, 0), (0, 0), 'E'), (2, 0))
        self.assertEqual(AmbushStrategy(lookahead=0).choose_target(
            maze, (4, 0), (0, 0), 'E'), (0, 0))

    def test_intercepts_ahead_in_all_four_directions(self) -> None:
        horizontal = Maze([[13, 5, 5, 5, 5, 5, 7]])
        vertical = Maze([[11], [10], [10], [10], [10], [10], [14]])
        strategy = AmbushStrategy()
        for maze, ghost, player, heading in (
            (horizontal, (1, 0), (0, 0), 'E'),
            (horizontal, (5, 0), (6, 0), 'W'),
            (vertical, (0, 1), (0, 0), 'S'),
            (vertical, (0, 5), (0, 6), 'N'),
        ):
            with self.subTest(heading=heading):
                self.assertEqual(strategy.choose_direction(
                    maze, ghost, player, heading), heading)

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


class InkyStrategyTests(unittest.TestCase):
    def test_target_reflects_red_position_across_two_cells_ahead(self) -> None:
        size = 9
        maze = Maze([[
            (1 if y == 0 else 0) | (2 if x == size - 1 else 0)
            | (4 if y == size - 1 else 0) | (8 if x == 0 else 0)
            for x in range(size)] for y in range(size)])
        strategy = InkyStrategy()
        for heading, red, expected in (
            ('N', (4, 4), (4, 0)),
            ('E', (4, 4), (8, 4)),
            ('S', (4, 4), (4, 8)),
            ('W', (4, 4), (0, 4)),
            ('E', (7, 4), (5, 4)),
        ):
            with self.subTest(heading=heading, red=red):
                self.assertEqual(strategy.choose_target(
                    maze, (0, 0), (4, 4), heading, red_pos=red), expected)

    def test_outside_target_projects_to_reachable_cell_and_drives_bfs(self) -> None:
        maze = Maze([[13, 5, 7]])
        strategy = InkyStrategy()
        self.assertEqual(strategy.choose_target(
            maze, (0, 0), (1, 0), 'E', red_pos=(0, 0)), (2, 0))
        self.assertEqual(strategy.choose_direction(
            maze, (0, 0), (1, 0), 'E', red_pos=(0, 0)), 'E')

    def test_projection_excludes_disconnected_cells(self) -> None:
        maze = Maze([[13, 7, 13, 7]])
        self.assertEqual(InkyStrategy().choose_target(
            maze, (0, 0), (2, 0), 'E', red_pos=(3, 0)), (1, 0))

    def test_missing_red_falls_back_to_player(self) -> None:
        maze = Maze([[13, 5, 7]])
        for kwargs in ({}, {'red_pos': None}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(InkyStrategy().choose_target(
                    maze, (0, 0), (1, 0), 'E', **kwargs), (1, 0))

    def test_no_reachable_cells_returns_current_position(self) -> None:
        self.assertEqual(InkyStrategy().choose_target(
            Maze([[15, 15]]), (0, 0), (1, 0), 'E', red_pos=(1, 0)), (0, 0))


if __name__ == '__main__':
    unittest.main()

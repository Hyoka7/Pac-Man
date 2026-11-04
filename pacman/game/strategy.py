"""Direction-selection strategies for ghosts."""

import random
from abc import ABC, abstractmethod
from typing import TypedDict, Unpack

from pacman.game.directions import DIRECTION_OFFSETS, DIRECTIONS, OPPOSITE_DIRECTIONS
from pacman.game.maze import Maze


class StrategyKwargs(TypedDict, total=False):
    red_pos: tuple[int, int] | None


class Strategy(ABC):
    """Choose a ghost's next direction from the current game state."""

    @abstractmethod
    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        target: tuple[int, int] | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> str | None:
        """Return an open direction, or None when no move is available."""
        raise NotImplementedError

    def choose_target(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        **kwargs: Unpack[StrategyKwargs],
    ) -> tuple[int, int]:
        return player_pos


class BFSStrategy(Strategy):
    """Choose shortest-path steps using the maze's precomputed distances."""

    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        target: tuple[int, int] | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> str | None:
        """Choose randomly among steps that reduce the shortest distance by one."""
        if target is None:
            target = self.choose_target(
                maze,
                ghost_pos,
                player_pos,
                player_dir,
                **kwargs,
            )
        best_distance = maze.distances.get(ghost_pos, {}).get(target)
        if best_distance is None or best_distance == 0:
            return None
        candidates: list[str] = []
        for direction in DIRECTIONS:
            if not maze.can_move(*ghost_pos, direction):
                continue
            neighbor = maze.next_cell(*ghost_pos, direction)
            distance = maze.distances.get(neighbor, {}).get(target)
            if distance is not None and distance == best_distance - 1:
                candidates.append(direction)
        return random.choice(candidates) if candidates else None


class AmbushStrategy(BFSStrategy):
    def __init__(self, lookahead: int = 3) -> None:
        self.lookahead = lookahead

    def targets_ahead(
        self, maze: Maze, player_pos: tuple[int, int], player_dir: str
    ) -> list[tuple[int, int]]:
        """List open cells ahead, from nearest to farthest."""
        targets: list[tuple[int, int]] = []
        target = player_pos
        for _ in range(self.lookahead):
            if not maze.can_move(*target, player_dir):
                break
            target = maze.next_cell(*target, player_dir)
            targets.append(target)
        return targets

    def choose_target(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        **kwargs: Unpack[StrategyKwargs],
    ) -> tuple[int, int]:
        targets = self.targets_ahead(maze, player_pos, player_dir)
        return targets[-1] if targets else player_pos


class ReverseAmbushStrategy(AmbushStrategy):
    def choose_target(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        **kwargs: Unpack[StrategyKwargs],
    ) -> tuple[int, int]:
        dir = OPPOSITE_DIRECTIONS[player_dir]
        return super().choose_target(maze, ghost_pos, player_pos, dir, **kwargs)

class InkyStrategy(BFSStrategy):
    def choose_target(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        target: tuple[int, int] | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> tuple[int, int]:
        px, py = player_pos
        dx, dy = DIRECTION_OFFSETS[player_dir]
        ahead_x, ahead_y = px + 2 * dx, py + 2 * dy
        red_pos = kwargs.get("red_pos")
        if red_pos is None:
            return player_pos
        gx, gy = red_pos
        target_x, target_y = 2 * ahead_x - gx, 2 * ahead_y - gy
        reachable = maze.distances.get(ghost_pos, {})
        nearest_reachable = min(
            reachable,
            key=lambda cell: (cell[0] - target_x) ** 2 + (cell[1] - target_y) ** 2,
            default=ghost_pos,
        )
        return nearest_reachable

class FleeBFSStrategy(Strategy):
    """Choose shortest-path steps using the maze's precomputed distances."""

    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
        target: tuple[int, int] | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> str | None:
        """Look up distances without running BFS during gameplay."""
        best_distance = -1
        chosen: str | None = None
        for direction in DIRECTIONS:
            if not maze.can_move(*ghost_pos, direction):
                continue
            neighbor = maze.next_cell(*ghost_pos, direction)
            distance = maze.distances.get(neighbor, {}).get(player_pos)
            if distance is not None and distance > best_distance:
                best_distance = distance
                chosen = direction
        return chosen

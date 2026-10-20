"""Direction-selection strategies for ghosts."""

import random
from abc import ABC, abstractmethod

from .maze import Maze


class Strategy(ABC):
    """Choose a ghost's next direction from the current game state."""

    @abstractmethod
    def choose_direction(
        self, maze: Maze, ghost_pos: tuple[int, int], player_pos: tuple[int, int]
    ) -> str | None:
        """Return an open direction, or None when no move is available."""
        raise NotImplementedError


class RandomStrategy(Strategy):
    """Choose randomly among all open neighboring cells."""

    def choose_direction(
        self, maze: Maze, ghost_pos: tuple[int, int], player_pos: tuple[int, int]
    ) -> str | None:
        """Return a random legal move, or None for an isolated cell."""
        available = []
        for direction in ("N", "S", "E", "W"):
            if maze.can_move(*ghost_pos, direction):
                available.append(direction)
        return random.choice(available) if available else None


class BFSStrategy(Strategy):
    """Choose shortest-path steps using the maze's precomputed distances."""

    def choose_direction(
        self, maze: Maze, ghost_pos: tuple[int, int], player_pos: tuple[int, int]
    ) -> str | None:
        """Look up distances without running BFS during gameplay."""
        best_distance = maze.distances.get(ghost_pos, {}).get(player_pos)
        if best_distance is None or best_distance == 0:
            return None
        chosen: str | None = None
        for direction in ("N", "E", "S", "W"):
            if not maze.can_move(*ghost_pos, direction):
                continue
            neighbor = maze.next_cell(*ghost_pos, direction)
            distance = maze.distances.get(neighbor, {}).get(player_pos)
            if distance is not None and distance < best_distance:
                best_distance = distance
                chosen = direction
        return chosen


class FleeBFSStrategy(Strategy):
    """Choose shortest-path steps using the maze's precomputed distances."""

    def choose_direction(
        self, maze: Maze, ghost_pos: tuple[int, int], player_pos: tuple[int, int]
    ) -> str | None:
        """Look up distances without running BFS during gameplay."""
        best_distance = -1
        chosen: str | None = None
        for direction in ("N", "E", "S", "W"):
            if not maze.can_move(*ghost_pos, direction):
                continue
            neighbor = maze.next_cell(*ghost_pos, direction)
            distance = maze.distances.get(neighbor, {}).get(player_pos)
            if distance is not None and distance > best_distance:
                best_distance = distance
                chosen = direction
        return chosen

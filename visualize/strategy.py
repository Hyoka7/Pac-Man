"""Direction-selection strategies for ghosts."""

import random
from abc import ABC, abstractmethod

from .maze import Maze


class Strategy(ABC):
    """Choose a ghost's next direction from the current game state."""

    @abstractmethod
    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
    ) -> str | None:
        """Return an open direction, or None when no move is available."""
        raise NotImplementedError


class RandomStrategy(Strategy):
    """Choose randomly among all open neighboring cells."""

    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
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
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
    ) -> str | None:
        """Choose randomly among steps that reduce the shortest distance by one."""
        best_distance = maze.distances.get(ghost_pos, {}).get(player_pos)
        if best_distance is None or best_distance == 0:
            return None
        candidates: list[str] = []
        for direction in ("N", "E", "S", "W"):
            if not maze.can_move(*ghost_pos, direction):
                continue
            neighbor = maze.next_cell(*ghost_pos, direction)
            distance = maze.distances.get(neighbor, {}).get(player_pos)
            if distance is not None and distance == best_distance - 1:
                candidates.append(direction)
        return random.choice(candidates) if candidates else None


class AmbushStrategy(BFSStrategy):
    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
    ) -> str | None:
        target = player_pos
        step = 0
        while step < 3 and maze.can_move(*target, player_dir):
            target = maze.next_cell(*target, player_dir)
            step += 1
        return super().choose_direction(
            maze,
            ghost_pos,
            target,
            player_dir,
        )


class ReverseAmbushStrategy(AmbushStrategy):
    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
    ) -> str | None:
        reverse_dir = {
            "N": "S",
            "S": "N",
            "E": "W",
            "W": "E",
        }
        dir = reverse_dir[player_dir]
        return super().choose_direction(maze, ghost_pos, player_pos, dir)


class BlockStrategy(BFSStrategy):
    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
    ) -> str | None:
        can_move_dir = []
        for dir in ["N", "E", "S", "W"]:
            if maze.can_move(*player_pos, dir):
                can_move_dir.append(dir)
        vertical_dir = []
        if player_dir in ("N", "S"):
            for dir in can_move_dir:
                if dir in ("E", "W"):
                    vertical_dir.append(dir)
        if player_dir in ("E", "W"):
            for dir in can_move_dir:
                if dir in ("N", "S"):
                    vertical_dir.append(dir)
        if len(vertical_dir):
            chosen_dir = random.choice(vertical_dir)
            target = maze.next_cell(*player_pos, chosen_dir)
            return super().choose_direction(maze, ghost_pos, target, player_dir)
        else:
            return super().choose_direction(maze, ghost_pos, player_pos, player_dir)


class FleeBFSStrategy(Strategy):
    """Choose shortest-path steps using the maze's precomputed distances."""

    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: tuple[int, int],
        player_pos: tuple[int, int],
        player_dir: str,
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

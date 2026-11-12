"""Direction-selection strategies for ghosts."""

import random
from abc import ABC, abstractmethod
from typing import TypedDict, Unpack

from pacman.game.directions import DIRECTION_OFFSETS, DIRECTIONS, OPPOSITE_DIRECTIONS
from pacman.game.maze import Maze
from pacman.types import CellPosition


class StrategyKwargs(TypedDict, total=False):
    """Optional extra inputs for strategies."""

    red_pos: CellPosition | None


class Strategy(ABC):
    """Choose a ghost's next direction from the current game state."""

    @abstractmethod
    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        target: CellPosition | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> str | None:
        """Return an open direction, or None when no move is available.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            target: Cell to chase; computed with choose_target() when None.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).

        Returns:
            An open direction, or None when no move is available.
        """
        raise NotImplementedError

    def choose_target(
        self,
        maze: Maze,
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        **kwargs: Unpack[StrategyKwargs],
    ) -> CellPosition:
        """Return the cell to chase; the base strategy chases the player.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).

        Returns:
            The player's cell.
        """
        return player_pos


class BFSStrategy(Strategy):
    """Choose shortest-path steps using the maze's precomputed distances."""

    def choose_direction(
        self,
        maze: Maze,
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        target: CellPosition | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> str | None:
        """Pick a random step that shortens the distance to the target.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            target: Cell to chase; computed with choose_target() when None.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).

        Returns:
            A direction one step closer to the target, or None.
        """
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
    """Chase a cell a few steps ahead of the player."""

    def __init__(self, lookahead: int = 3) -> None:
        """Set how many open cells ahead of the player to target.

        Args:
            lookahead: Maximum number of cells to look ahead.
        """
        self.lookahead = lookahead

    def targets_ahead(
        self, maze: Maze, player_pos: CellPosition, player_dir: str
    ) -> list[CellPosition]:
        """List open cells ahead, from nearest to farthest.

        Args:
            maze: Maze used for wall checks.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.

        Returns:
            Open cells ahead of the player, nearest first.
        """
        targets: list[CellPosition] = []
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
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        **kwargs: Unpack[StrategyKwargs],
    ) -> CellPosition:
        """Return the farthest open cell ahead of the player.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).

        Returns:
            The farthest open cell ahead, or the player's cell.
        """
        targets = self.targets_ahead(maze, player_pos, player_dir)
        return targets[-1] if targets else player_pos


class ReverseAmbushStrategy(AmbushStrategy):
    """Chase a cell a few steps behind the player."""

    def choose_target(
        self,
        maze: Maze,
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        **kwargs: Unpack[StrategyKwargs],
    ) -> CellPosition:
        """Return the farthest open cell behind the player.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).

        Returns:
            The farthest open cell behind, or the player's cell.
        """
        dir = OPPOSITE_DIRECTIONS[player_dir]
        return super().choose_target(maze, ghost_pos, player_pos, dir, **kwargs)

class InkyStrategy(BFSStrategy):
    """Flank the player on the opposite side from the red ghost."""

    def choose_target(
        self,
        maze: Maze,
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        target: CellPosition | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> CellPosition:
        """Mirror the red ghost around the cell two steps ahead.

        The mirrored point is snapped to the nearest cell reachable
        from this ghost.

        Returns:
            The reachable target cell, or the player cell without red_pos.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            target: Unused; accepted for interface compatibility.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).
        """
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
        ghost_pos: CellPosition,
        player_pos: CellPosition,
        player_dir: str,
        target: CellPosition | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> str | None:
        """Look up distances without running BFS during gameplay.

        Args:
            maze: Maze used for wall checks.
            ghost_pos: Cell the ghost last reached.
            player_pos: Cell the player last reached.
            player_dir: Direction the player is facing.
            target: Unused; fleeing always uses the player cell.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).

        Returns:
            The direction that maximizes the distance to the player, or None.
        """
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

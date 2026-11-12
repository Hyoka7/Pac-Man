"""Maze walls, navigation and precomputed distances."""

from __future__ import annotations

from collections import deque

from pacman.game.directions import (
    ALL_WALLS,
    DIRECTION_OFFSETS,
    DIRECTIONS,
    WALL_BITS,
)
from pacman.types import CellDistances, CellPosition, MazeDistances, MazeGrid


class Maze:
    """Own a rectangular grid of wall masks."""

    def __init__(self, maze: MazeGrid) -> None:
        """Validate and copy the supplied maze.

        Args:
            maze: Rows of wall bitmasks from the generator.

        Raises:
            ValueError: If the grid is empty, not rectangular or has
                values outside 0..15.
        """
        if not maze or not maze[0]:
            raise ValueError("maze must not be empty")
        self.rows = len(maze)
        self.cols = len(maze[0])
        if any(len(row) != self.cols for row in maze):
            raise ValueError("maze must be rectangular")
        if any(
            type(cell) is not int or not 0 <= cell <= 15 for row in maze for cell in row
        ):
            raise ValueError("each cell must be an integer wall mask (0..15)")
        self.maze: MazeGrid = [row[:] for row in maze]
        self.distances: MazeDistances = {
            (x, y): self._build_distances((x, y))
            for y, row in enumerate(self.maze)
            for x, cell in enumerate(row)
            if cell != ALL_WALLS
        }

    def central_cell(self) -> CellPosition:
        """Return a passage nearest the center, breaking ties in row order.

        Returns:
            The open cell closest to the maze center.

        Raises:
            ValueError: If the maze has no open cell.
        """
        center_x, center_y = self.cols // 2, self.rows // 2
        passages = [
            (x, y)
            for y, row in enumerate(self.maze)
            for x, cell in enumerate(row)
            if cell != ALL_WALLS
        ]
        if not passages:
            raise ValueError("maze has no passage for the player")
        return min(
            passages,
            key=lambda cell: abs(cell[0] - center_x) + abs(cell[1] - center_y),
        )

    def _build_distances(self, start: CellPosition) -> CellDistances:
        """Run BFS from one cell while preparing the level's distance table.

        Args:
            start: Origin cell.

        Returns:
            Step counts from start to every reachable cell.
        """
        distances: CellDistances = {start: 0}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for direction in DIRECTIONS:
                if not self.can_move(*cell, direction):
                    continue
                neighbor = self.next_cell(*cell, direction)
                x, y = neighbor
                if neighbor in distances or self.maze[y][x] == ALL_WALLS:
                    continue
                distances[neighbor] = distances[cell] + 1
                queue.append(neighbor)
        return distances

    def next_cell(self, x: int, y: int, direction: str) -> CellPosition:
        """Return the adjacent cell; walls and bounds are checked separately.

        Args:
            x: Column of the current cell.
            y: Row of the current cell.
            direction: Direction: "N", "E", "S" or "W".

        Returns:
            The neighboring cell in that direction.

        Raises:
            ValueError: If the direction is unknown.
        """
        if direction not in DIRECTION_OFFSETS:
            raise ValueError("direction must be N, E, S or W")
        dx, dy = DIRECTION_OFFSETS[direction]
        return x + dx, y + dy

    def can_move(
        self,
        x: int,
        y: int,
        direction: str,
        wallhack: bool = False,
    ) -> bool:
        """Return whether a cell has an in-bounds passage in a direction.

        Args:
            x: Column of the current cell.
            y: Row of the current cell.
            direction: Direction: "N", "E", "S" or "W".
            wallhack: Ignore walls but still stay inside the maze.

        Returns:
            True when the move stays in bounds and is not blocked.
        """
        if direction not in WALL_BITS:
            return False
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return False
        next_x, next_y = self.next_cell(x, y, direction)
        wall = WALL_BITS[direction]
        return (
            0 <= next_x < self.cols
            and 0 <= next_y < self.rows
            and (wallhack or self.maze[y][x] & wall == 0)
        )

"""Maze walls, navigation and precomputed distances."""

from __future__ import annotations

from collections import deque

from pacman.game.directions import DIRECTION_OFFSETS, DIRECTIONS, WALL_BITS


class Maze:
    """Own a rectangular grid of wall masks."""

    def __init__(self, maze: list[list[int]]) -> None:
        """Validate and copy the supplied maze."""
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
        self.maze = [row[:] for row in maze]
        self.distances = {
            (x, y): self._build_distances((x, y))
            for y, row in enumerate(self.maze)
            for x, cell in enumerate(row)
            if cell != 15
        }

    def central_cell(self) -> tuple[int, int]:
        """Return a passage nearest the center, breaking ties in row order."""
        center_x, center_y = self.cols // 2, self.rows // 2
        passages = [
            (x, y)
            for y, row in enumerate(self.maze)
            for x, cell in enumerate(row)
            if cell != 15
        ]
        if not passages:
            raise ValueError("maze has no passage for the player")
        return min(
            passages,
            key=lambda cell: abs(cell[0] - center_x) + abs(cell[1] - center_y),
        )

    def _build_distances(
        self, start: tuple[int, int]
    ) -> dict[tuple[int, int], int]:
        """Run BFS from one cell while preparing the level's distance table."""
        distances = {start: 0}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for direction in DIRECTIONS:
                if not self.can_move(*cell, direction):
                    continue
                neighbor = self.next_cell(*cell, direction)
                x, y = neighbor
                if neighbor in distances or self.maze[y][x] == 15:
                    continue
                distances[neighbor] = distances[cell] + 1
                queue.append(neighbor)
        return distances

    def next_cell(self, x: int, y: int, direction: str) -> tuple[int, int]:
        """Return the adjacent cell; walls and bounds are checked separately."""
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
        """Return whether a cell has an in-bounds passage in a direction."""
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

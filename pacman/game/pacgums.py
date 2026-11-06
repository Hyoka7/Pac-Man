"""Pacgum placement and consumption."""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from pacman.game.maze import Maze

if TYPE_CHECKING:
    from pacman.visualize.canvas import Canvas


class PacgumEatenEnum(IntEnum):
    Neither = 0
    Normal = 1
    Super = 2


class Pacgums:
    """Own the remaining pacgum centers for one level."""

    def __init__(self, rows: int, cols: int) -> None:
        """Start with no pacgums."""
        self.remain_gums: set[tuple[float, float]] = set()
        self.super_gums: set[tuple[float, float]] = set()
        self.rows: int = rows
        self.cols: int = cols

    def __len__(self) -> int:
        return len(self.remain_gums) + len(self.super_gums)

    def _is_edge(self, x: int, y: int) -> bool:
        return (x == 0 or x == self.cols - 1) and (y == 0 or y == self.rows - 1)

    def reset_pacgums(
        self, maze: Maze, canvas: Canvas, player_pos: tuple[int, int]
    ) -> None:
        """Replace the level's pacgums, excluding walls and the start cell."""
        self.rows = maze.rows
        self.cols = maze.cols
        self.remain_gums = {
            canvas.cell_center(x, y)
            for y, row in enumerate(maze.maze)
            for x, cell in enumerate(row)
            if cell != 15 and (x, y) != player_pos and not self._is_edge(x, y)
        }
        self.super_gums = {
            canvas.cell_center(x, y)
            for y, row in enumerate(maze.maze)
            for x, cell in enumerate(row)
            if cell != 15 and (x, y) != player_pos and self._is_edge(x, y)
        }

    def consume_pacgum(self, center: tuple[float, float]) -> PacgumEatenEnum:
        """Remove the pacgum at an arrived cell center."""
        if center in self.remain_gums:
            self.remain_gums.discard(center)
            return PacgumEatenEnum.Normal
        if center in self.super_gums:
            self.super_gums.discard(center)
            return PacgumEatenEnum.Super
        return PacgumEatenEnum.Neither

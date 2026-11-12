"""Pacgum placement and consumption."""

from __future__ import annotations

from enum import IntEnum

from pacman.game.directions import ALL_WALLS
from pacman.game.maze import Maze
from pacman.types import CellPosition


class PacgumEatenEnum(IntEnum):
    """Kind of pacgum eaten during one update."""

    Neither = 0
    Normal = 1
    Super = 2


class Pacgums:
    """Own the remaining pacgum cells for one level."""

    def __init__(self, rows: int, cols: int) -> None:
        """Start with no pacgums.

        Args:
            rows: Number of maze rows.
            cols: Number of maze columns.
        """
        self.remain_gums: set[CellPosition] = set()
        self.super_gums: set[CellPosition] = set()
        self.rows: int = rows
        self.cols: int = cols

    def __len__(self) -> int:
        """Return the number of normal and super pacgums left.

        Returns:
            The number of pacgums left.
        """
        return len(self.remain_gums) + len(self.super_gums)

    def _is_corner(self, x: int, y: int) -> bool:
        """Return whether a cell is one of the maze's four corners.

        Args:
            x: Cell column.
            y: Cell row.

        Returns:
            True for the four corner cells.
        """
        return x in (0, self.cols - 1) and y in (0, self.rows - 1)

    def reset_pacgums(self, maze: Maze, player_pos: CellPosition) -> None:
        """Replace the level's pacgums, excluding walls and the start cell.

        Args:
            maze: Maze of the new level.
            player_pos: Player start cell, left empty.
        """
        self.rows = maze.rows
        self.cols = maze.cols
        open_cells = {
            (x, y)
            for y, row in enumerate(maze.maze)
            for x, cell in enumerate(row)
            if cell != ALL_WALLS and (x, y) != player_pos
        }
        self.super_gums = {
            cell for cell in open_cells if self._is_corner(*cell)
        }
        self.remain_gums = open_cells - self.super_gums

    def consume_pacgum(self, cell: CellPosition) -> PacgumEatenEnum:
        """Remove the pacgum at an arrived maze cell.

        Args:
            cell: Cell the player just reached.

        Returns:
            The kind of pacgum eaten, or Neither.
        """
        if cell in self.remain_gums:
            self.remain_gums.discard(cell)
            return PacgumEatenEnum.Normal
        if cell in self.super_gums:
            self.super_gums.discard(cell)
            return PacgumEatenEnum.Super
        return PacgumEatenEnum.Neither

"""Pacgum placement, consumption and rendering."""

from enum import IntEnum
from math import ceil, floor

from .maze import Maze
from .visualizerutils import VisualizerUtils


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

    def reset(
        self, maze: Maze, canvas: VisualizerUtils, player_pos: tuple[int, int]
    ) -> None:
        """Replace the level's pacgums, excluding walls and the start cell."""
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

    def consume(self, center: tuple[float, float]) -> PacgumEatenEnum:
        """Remove the pacgum at an arrived cell center."""
        if center in self.remain_gums:
            self.remain_gums.discard(center)
            return PacgumEatenEnum.Normal
        if center in self.super_gums:
            self.super_gums.discard(center)
            return PacgumEatenEnum.Super
        return PacgumEatenEnum.Neither

    def _draw_single_pacgum(
        self, canvas: VisualizerUtils, center_x: float, center_y: float
    ) -> None:
        """Draw one solid white circular pacgum without antialiasing."""
        radius = canvas.cell_size * 0.05

        for y in range(
            max(0, floor(center_y - radius - 0.5)),
            min(canvas.height, ceil(center_y + radius + 0.5)),
        ):
            for x in range(
                max(0, floor(center_x - radius - 0.5)),
                min(canvas.width, ceil(center_x + radius + 0.5)),
            ):
                if not canvas.is_in_circle(
                    x + 0.5, y + 0.5, center_x, center_y, radius
                ):
                    continue
                canvas.draw_pixel(x, y, (255, 255, 255))

    def _draw_single_superpacgum(
        self, canvas: VisualizerUtils, center_x: float, center_y: float
    ) -> None:
        """Draw one solid white circular superpacgum without antialiasing."""
        radius = canvas.cell_size * 0.15

        for y in range(
            max(0, floor(center_y - radius - 0.5)),
            min(canvas.height, ceil(center_y + radius + 0.5)),
        ):
            for x in range(
                max(0, floor(center_x - radius - 0.5)),
                min(canvas.width, ceil(center_x + radius + 0.5)),
            ):
                if not canvas.is_in_circle(
                    x + 0.5, y + 0.5, center_x, center_y, radius
                ):
                    continue
                canvas.draw_pixel(x, y, (255, 255, 0))

    def draw(self, canvas: VisualizerUtils) -> None:
        """Draw only the pacgums that have not been eaten."""
        for x, y in self.remain_gums:
            self._draw_single_pacgum(canvas, x, y)
        for x, y in self.super_gums:
            self._draw_single_superpacgum(canvas, x, y)

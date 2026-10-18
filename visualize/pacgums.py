"""Pacgum placement, consumption and rendering."""

from math import ceil, floor

from .maze import Maze
from .visualizerutils import VisualizerUtils


class Pacgums:
    """Own the remaining pacgum centers for one level."""

    def __init__(self) -> None:
        """Start with no pacgums."""
        self.remain_gums: set[tuple[float, float]] = set()

    def __len__(self) -> int:
        return len(self.remain_gums)

    def reset(
        self, maze: Maze, canvas: VisualizerUtils, player_pos: tuple[int, int]
    ) -> None:
        """Replace the level's pacgums, excluding walls and the start cell."""
        self.remain_gums = {
            canvas.cell_center(x, y)
            for y, row in enumerate(maze.maze)
            for x, cell in enumerate(row)
            if cell != 15 and (x, y) != player_pos
        }

    def consume(self, center: tuple[float, float]) -> bool:
        """Remove the pacgum at an arrived cell center."""
        if center in self.remain_gums:
            self.remain_gums.discard(center)
            return True
        return False

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

    def draw(self, canvas: VisualizerUtils) -> None:
        """Draw only the pacgums that have not been eaten."""
        for x, y in self.remain_gums:
            self._draw_single_pacgum(canvas, x, y)

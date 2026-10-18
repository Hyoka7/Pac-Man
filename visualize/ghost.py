"""Ghost state, ready for future movement and rendering."""

from math import ceil, floor, hypot

from .maze import Maze
from .movement import Movement
from .strategy import Strategy
from .visualizerutils import VisualizerUtils


class Ghost:
    """Store one ghost's cell, appearance and current facing direction."""

    def __init__(
        self,
        cell: tuple[int, int],
        strategy: Strategy,
        color: tuple[int, int, int] = (255, 0, 0),
        direction: str = "E",
    ) -> None:
        """Create a ghost with shared animation state and its own strategy."""
        self.movement = Movement(cell, speed=4.0, direction=direction)
        self.radius: float = 0.0
        self.color = color
        self.strategy = strategy

    @property
    def cell(self) -> tuple[int, int]:
        """Return the last cell center reached by the ghost."""
        return self.movement.cell

    @property
    def direction(self) -> str:
        """Return the direction of the current animation."""
        return self.movement.direction

    def place(self, canvas: VisualizerUtils) -> None:
        """Initialize the shared movement's drawing position."""
        self.movement.place(canvas)
        self.radius = canvas.cell_size * 0.375

    def update(
        self,
        elapsed: float,
        maze: Maze,
        canvas: VisualizerUtils,
        player_cell: tuple[int, int],
    ) -> None:
        """Choose a direction at cell centers and animate the chosen move."""
        if not self.movement.moving:
            if self.cell == player_cell:
                return
            direction = self.strategy.choose_direction(maze, self.cell, player_cell)
            if direction is None:
                return
            self.movement.start(direction, maze, canvas)
        self.movement.update(elapsed, canvas)

    def _in_body(
        self, x: int, y: int, center_x: float, center_y: float, radius: float
    ) -> bool:
        left = center_x - radius
        right = center_x + radius
        lower = center_y
        upper = center_y + radius
        return (left <= x <= right) and (lower <= y <= upper)

    def reset(self, canvas: VisualizerUtils) -> None:
        return self.movement.reset(canvas)

    def draw(self, canvas: VisualizerUtils) -> None:
        """Draw four feet using elliptical cutouts and antialiased edges."""
        center_x, center_y = self.movement.center or canvas.cell_center(*self.cell)
        radius = self.radius
        notch_depth = radius / 3
        notch_half_width = radius / 6
        for y in range(
            max(0, floor(center_y - radius - 0.5)),
            min(canvas.height, ceil(center_y + radius + 0.5)),
        ):
            for x in range(
                max(0, floor(center_x - radius - 0.5)),
                min(canvas.width, ceil(center_x + radius + 0.5)),
            ):
                dx = x + 0.5 - center_x
                dy = y + 0.5 - center_y
                if dy <= 0:
                    # Distance to the head's circular outline.
                    distance = hypot(dx, dy) - radius
                else:
                    # Distance to the sides and bottom; the head-body join
                    # is inside the shape, so it must stay fully colored.
                    distance = max(abs(dx) - radius, dy - radius)
                for notch_x in (-radius / 2, 0.0, radius / 2):
                    # Center each ellipse on the bottom edge so its upper
                    # half removes a rounded notch from the body.
                    ellipse_x = (dx - notch_x) / notch_half_width
                    ellipse_y = (dy - radius) / notch_depth
                    ellipse_radius = hypot(ellipse_x, ellipse_y)
                    gradient = hypot(
                        ellipse_x / notch_half_width, ellipse_y / notch_depth
                    )
                    # Approximate distance in pixels, positive inside the cut.
                    cut_distance = (
                        ellipse_radius * (1.0 - ellipse_radius) / gradient
                        if gradient > 0
                        else min(notch_half_width, notch_depth)
                    )
                    distance = max(distance, cut_distance)
                coverage = max(0.0, min(1.0, 0.5 - distance))
                canvas.draw_pixel_aa(x, y, self.color, coverage)

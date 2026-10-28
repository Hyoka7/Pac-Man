"""Ghost state, ready for future movement and rendering."""

from functools import cache
from math import ceil, hypot

from PIL import Image

from .image_renderer import ImageRenderer
from .maze import Maze
from .movement import Movement
from .strategy import FleeBFSStrategy, Strategy
from .visualizerutils import VisualizerUtils


@cache
def ghost_image(radius: float, color: tuple[int, int, int]) -> Image.Image:
    side = ceil(radius * 2) + 2
    img = Image.new(
        "RGBA",
        (side, side),
        (0, 0, 0, 0),
    )
    center_x, center_y = side / 2, side / 2
    notch_depth = radius / 3
    notch_half_width = radius / 6
    for y in range(side):
        for x in range(side):
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
                gradient = hypot(ellipse_x / notch_half_width, ellipse_y / notch_depth)
                # Approximate distance in pixels, positive inside the cut.
                cut_distance = (
                    ellipse_radius * (1.0 - ellipse_radius) / gradient
                    if gradient > 0
                    else min(notch_half_width, notch_depth)
                )
                distance = max(distance, cut_distance)
            coverage = max(0.0, min(1.0, 0.5 - distance))
            img.putpixel((x, y), (*color, round(coverage * 255)))
    return img


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
        self.respawn_remaining = 0.0
        self.color = color
        self.strategy = strategy
        self.renderer = ImageRenderer()

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
        eatable: bool,
    ) -> None:
        """Choose a direction at cell centers and animate the chosen move."""
        if self.respawn_remaining > 0.0:
            self.respawn_remaining = max(0.0, self.respawn_remaining - elapsed)
            return
        if not self.movement.moving:
            if not eatable:
                if self.cell == player_cell:
                    return
                direction = self.strategy.choose_direction(maze, self.cell, player_cell)
                if direction is None:
                    return
                self.movement.start(direction, maze, canvas)
            else:
                flee = FleeBFSStrategy()
                direction = flee.choose_direction(maze, self.cell, player_cell)
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
        self.radius = canvas.cell_size * 0.375
        self.respawn_remaining = 0.0
        return self.movement.reset(canvas)

    def draw(
        self,
        canvas: VisualizerUtils,
        eatable: bool,
        eatable_remain: float,
    ) -> None:
        """Draw four feet using elliptical cutouts and antialiased edges."""
        if self.respawn_remaining > 1.5:
            return
        elif self.respawn_remaining > 0.0:
            is_visible = int(self.respawn_remaining / 0.20 % 2)
            if not is_visible:
                return
        if eatable:
            if eatable_remain > 1.5:
                color = (0, 0, 128)
            elif int(eatable_remain / 0.20) % 2:
                color = self.color
            else:
                color = (0, 0, 128)
        else:
            color = self.color
        img = ghost_image(self.radius, color)
        center_x, center_y = self.movement.center
        left = round(center_x - img.width / 2)
        top = round(center_y - img.height / 2)
        self.renderer.draw_image(canvas, left, top, img)

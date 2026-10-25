"""Player state, movement, queued turns and rendering."""

from functools import cache
from math import ceil, hypot, radians, tan

from PIL import Image

from .maze import Maze
from .movement import Movement
from .pacgums import PacgumEatenEnum, Pacgums
from .image_renderer import ImageRenderer
from .visualizerutils import VisualizerUtils


@cache
def _player_image(
    radius: float,
    direction: str,
    mouth_step: int,
) -> Image.Image:
    side = ceil(radius * 2) + 2
    img = Image.new(
        "RGBA",
        (side, side),
        (0, 0, 0, 0),
    )
    center_x = side / 2
    center_y = side / 2
    mouth_half_angle = 45 * mouth_step / 10
    mouth_slope = tan(radians(mouth_half_angle))

    def _circle_coverage(x_pixel: float, y_pixel: float) -> float:
        """Fade across a one-pixel band around the circle boundary."""
        distance = hypot(x_pixel - center_x, y_pixel - center_y)
        return max(0.0, min(1.0, radius + 0.5 - distance))

    def _is_in_mouth_horizon(x_pixel: float, y_pixel: float, dir: str) -> bool:
        if mouth_half_angle <= 0:
            return False
        dx = x_pixel - center_x
        dy = y_pixel - center_y
        return (
            abs(dy) <= abs(dx) * mouth_slope and dx > 0
            if dir == "E"
            else abs(dy) <= abs(dx) * mouth_slope and dx < 0
        )

    def _is_in_mouth_vertical(x_pixel: float, y_pixel: float, dir: str) -> bool:
        if mouth_half_angle <= 0:
            return False
        dx = x_pixel - center_x
        dy = y_pixel - center_y
        return (
            abs(dx) <= abs(dy) * mouth_slope and dy > 0
            if dir == "S"
            else abs(dx) <= abs(dy) * mouth_slope and dy < 0
        )

    samples = (0.125, 0.375, 0.625, 0.875)
    for y in range(side):
        for x in range(side):
            circle_coverage = _circle_coverage(x + 0.5, y + 0.5)
            if circle_coverage == 0:
                continue
            if direction in ("E", "W"):
                body_count = sum(
                    not _is_in_mouth_horizon(x + dx, y + dy, direction)
                    for dx in samples
                    for dy in samples
                )
            else:
                body_count = sum(
                    not _is_in_mouth_vertical(x + dx, y + dy, direction)
                    for dx in samples
                    for dy in samples
                )
            coverage = circle_coverage * (body_count / 16)
            if coverage == 0:
                continue
            img.putpixel((x, y), (255, 255, 0, round(coverage * 255)))
    return img


class Player:
    """Own the player independently of the MLX event loop."""

    def __init__(
        self,
        pos: tuple[int, int] = (0, 0),
        initial_lives: int = 3,
        score_normal_gum: int = 10,
        score_super_gum: int = 30,
    ) -> None:
        """Start stopped at a cell, facing east."""
        self.movement = Movement(pos, speed=8.0)
        self.renderer = ImageRenderer()
        self.radius: float = 0.0
        self.ult = False
        self.reserved_move: str | None = None
        self.mouth_half_angle = 45.0  # Degrees; 45 means a 90-degree opening.
        self.mouth_period = 0.3  # Seconds for one open-close cycle.
        self.is_invincible = False
        self.invincible_remain: float = 0.0
        self._mouth_elapsed = self.mouth_period / 2
        self.initial_lives = initial_lives
        self.lives = initial_lives
        self.score = 0
        self.score_normal_gum = score_normal_gum
        self.score_super_gum = score_super_gum
        self.is_alive: bool = True

    def update_mouth(self, elapsed: float) -> None:
        """Animate the mouth independently of player movement."""
        self._mouth_elapsed = (self._mouth_elapsed + elapsed) % self.mouth_period
        phase = self._mouth_elapsed / self.mouth_period
        self.mouth_half_angle = 45.0 * (1.0 - abs(2.0 * phase - 1.0))

    def place(self, canvas: VisualizerUtils) -> None:
        """Initialize the shared movement's drawing position."""
        self.movement.place(canvas)
        self.radius = canvas.cell_size * 0.375

    def request_move(self, direction: str, maze: Maze, canvas: VisualizerUtils) -> None:
        """Queue a turn, or start a cell-to-cell animation when stopped."""
        self.reserved_move = direction
        if self.movement.redirect(direction, maze, canvas):
            self.reserved_move = None

    def update(
        self,
        elapsed: float,
        maze: Maze,
        canvas: VisualizerUtils,
        pacgums: Pacgums,
    ) -> None:
        """Animate one frame and handle player-specific actions on arrival."""
        if self.is_invincible:
            self.invincible_remain = max(0.0, self.invincible_remain - elapsed)
            if self.invincible_remain == 0.0:
                self.is_invincible = False
        if not self.movement.update(elapsed, canvas):
            return
        eat_status = pacgums.consume(canvas.cell_center(*self.movement.cell))
        if eat_status == PacgumEatenEnum.Normal:
            self.score += self.score_normal_gum
        elif eat_status == PacgumEatenEnum.Super:
            self.score += self.score_super_gum
            self.is_invincible = True
            self.invincible_remain = 5.0
        if self.reserved_move is not None and self.movement.start(
            self.reserved_move, maze, canvas
        ):
            self.reserved_move = None
        else:
            self.movement.start(self.movement.direction, maze, canvas)

    def reset(self, canvas: VisualizerUtils) -> None:
        self.movement.reset(canvas)
        self.reserved_move = None
        self.is_alive = True
        self.invincible_remain = 0.0
        self.radius = canvas.cell_size * 0.375
        self.is_invincible = False

    def draw(self, canvas: VisualizerUtils) -> None:
        """Draw the player at its current interpolated center."""
        center_x, center_y = self.movement.center or canvas.cell_center(
            *self.movement.cell
        )
        mouth_step = round(self.mouth_half_angle / 45 * 10)
        img = _player_image(self.radius, self.movement.direction, mouth_step)
        left = round(center_x - img.width / 2)
        top = round(center_y - img.height / 2)
        self.renderer.draw_image(canvas, left, top, img)

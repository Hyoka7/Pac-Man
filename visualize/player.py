"""Player state, movement, queued turns and rendering."""

from collections.abc import Callable
from functools import cache
from math import ceil, radians, tan

from PIL import Image

from .image_renderer import ImageRenderer
from .maze import Maze
from .movement import Movement
from .pacgums import PacgumEatenEnum, Pacgums
from .visualizerutils import VisualizerUtils


@cache
def player_image(
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
    palette = Image.new(
        "RGBA",
        (16, 16),
        (0, 0, 0, 0),
    )

    mouth_angle_half = 45 * mouth_step / 10
    mouth_slope = tan(radians(mouth_angle_half))

    def _is_in_mouth(dx: float, dy: float) -> bool:
        """Return whether a point relative to the center is inside the mouth."""
        if direction == "E":
            forward, across = dx, dy
        elif direction == "W":
            forward, across = -dx, dy
        elif direction == "S":
            forward, across = dy, dx
        else:
            forward, across = -dy, dx
        return (
            mouth_step > 0
            and forward > 0
            and abs(across) <= forward * mouth_slope
        )

    for y in range(16):
        for x in range(16):
            dx = x - 7.5
            dy = y - 7.5
            if dx * dx + dy * dy <= 8 * 8 and not _is_in_mouth(dx, dy):
                palette.putpixel((x, y), (255, 255, 0, 255))
    zoomed = palette.resize((side - 2, side - 2), resample=Image.Resampling.NEAREST)
    img.alpha_composite(zoomed, (1, 1))

    return img


class Player:
    """Own the player independently of the MLX event loop."""

    def __init__(
        self,
        pos: tuple[int, int] = (0, 0),
        initial_lives: int = 3,
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
        *,
        choose_auto_direction: Callable[[], str | None] | None = None,
    ) -> PacgumEatenEnum:
        """Animate, apply power-ups, and report which gum the player ate."""
        if self.is_invincible:
            self.invincible_remain = max(0.0, self.invincible_remain - elapsed)
            if self.invincible_remain == 0.0:
                self.is_invincible = False
        if choose_auto_direction is not None and not self.movement.moving:
            self.reserved_move = None
            direction = choose_auto_direction()
            if direction is not None:
                self.movement.start(direction, maze, canvas)
        if not self.movement.update(elapsed, canvas):
            return PacgumEatenEnum.Neither
        eat_status = pacgums.consume(canvas.cell_center(*self.movement.cell))
        if eat_status == PacgumEatenEnum.Super:
            self.is_invincible = True
            self.invincible_remain = 5.0
        if choose_auto_direction is not None:
            self.reserved_move = None
            direction = choose_auto_direction()
            if direction is not None:
                self.movement.start(direction, maze, canvas)
            return eat_status
        if self.reserved_move is not None and self.movement.start(
            self.reserved_move, maze, canvas
        ):
            self.reserved_move = None
        else:
            self.movement.start(self.movement.direction, maze, canvas)
        return eat_status

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
        img = player_image(self.radius, self.movement.direction, mouth_step)
        left = round(center_x - img.width / 2)
        top = round(center_y - img.height / 2)
        self.renderer.draw_image(canvas, left, top, img)

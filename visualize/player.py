"""Player state, movement, queued turns and rendering."""

from math import ceil, floor, hypot, radians, tan

from .maze import Maze
from .movement import Movement
from .pacgums import Pacgums
from .visualizerutils import VisualizerUtils


class Player:
    """Own the player independently of the MLX event loop."""

    def __init__(self, pos: tuple[int, int] = (0, 0)) -> None:
        """Start stopped at a cell, facing east."""
        self.movement = Movement(pos, speed=8.0)
        self.radius: float = 0.0
        self.ult = False
        self.reserved_move: str | None = None
        self.mouth_half_angle = 45.0  # Degrees; 45 means a 90-degree opening.
        self.mouth_period = 0.3  # Seconds for one open-close cycle.
        self._mouth_elapsed = self.mouth_period / 2
        self.lives = 3
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
    ) -> None:
        """Animate one frame and handle player-specific actions on arrival."""
        if not self.movement.update(elapsed, canvas):
            return
        if pacgums.consume(canvas.cell_center(*self.movement.cell)):
            self.score += 10
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

    def _draw_player(
        self, canvas: VisualizerUtils, center_x: float, center_y: float, dir: str
    ) -> None:
        """Draw the player inside a maze cell."""
        radius = self.radius
        mouth_slope = tan(radians(self.mouth_half_angle))

        def _circle_coverage(x_pixel: float, y_pixel: float) -> float:
            """Fade across a one-pixel band around the circle boundary."""
            distance = hypot(x_pixel - center_x, y_pixel - center_y)
            return max(0.0, min(1.0, radius + 0.5 - distance))

        def _is_in_mouth_horizon(x_pixel: float, y_pixel: float, dir: str) -> bool:
            if self.mouth_half_angle <= 0:
                return False
            dx = x_pixel - center_x
            dy = y_pixel - center_y
            return (
                abs(dy) <= abs(dx) * mouth_slope and dx > 0
                if dir == "E"
                else abs(dy) <= abs(dx) * mouth_slope and dx < 0
            )

        def _is_in_mouth_vertical(x_pixel: float, y_pixel: float, dir: str) -> bool:
            if self.mouth_half_angle <= 0:
                return False
            dx = x_pixel - center_x
            dy = y_pixel - center_y
            return (
                abs(dx) <= abs(dy) * mouth_slope and dy > 0
                if dir == "S"
                else abs(dx) <= abs(dy) * mouth_slope and dy < 0
            )

        samples = (0.125, 0.375, 0.625, 0.875)
        for y in range(
            max(floor(center_y - radius - 0.5), 0),
            min(ceil(center_y + radius + 0.5), canvas.height),
        ):
            for x in range(
                max(0, floor(center_x - radius - 0.5)),
                min(canvas.width, ceil(center_x + radius + 0.5)),
            ):
                circle_coverage = _circle_coverage(x + 0.5, y + 0.5)
                if circle_coverage == 0:
                    continue
                if dir in ("E", "W"):
                    body_count = sum(
                        not _is_in_mouth_horizon(x + dx, y + dy, dir)
                        for dx in samples
                        for dy in samples
                    )
                else:
                    body_count = sum(
                        not _is_in_mouth_vertical(x + dx, y + dy, dir)
                        for dx in samples
                        for dy in samples
                    )
                coverage = circle_coverage * (body_count / 16)
                if coverage == 0:
                    continue
                canvas.draw_pixel_aa(x, y, (255, 255, 0), coverage)

    def draw(self, canvas: VisualizerUtils) -> None:
        """Draw the player at its current interpolated center."""
        center_x, center_y = self.movement.center or canvas.cell_center(
            *self.movement.cell
        )
        self._draw_player(canvas, center_x, center_y, self.movement.direction)

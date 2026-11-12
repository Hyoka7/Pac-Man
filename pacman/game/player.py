"""Player state, movement, queued turns and power-ups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pacman.game.maze import Maze
from pacman.game.movement import Movement
from pacman.game.pacgums import PacgumEatenEnum, Pacgums
from pacman.types import CellPosition

if TYPE_CHECKING:
    from pacman.visualize.canvas import Canvas


class Player:
    """Own the player independently of the MLX event loop."""

    DEFAULT_SPEED = 5.5
    INVINCIBLE_DURATION = 5.0  # Seconds after eating a super pacgum.

    def __init__(
        self,
        pos: CellPosition = (0, 0),
        initial_lives: int = 3,
    ) -> None:
        """Start stopped at a cell, facing east.

        Args:
            pos: Starting cell.
            initial_lives: Lives at the start of a game.
        """
        self.movement = Movement(pos, speed=self.DEFAULT_SPEED)
        self.radius: float = 0.0
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
        """Animate the mouth independently of player movement.

        Args:
            elapsed: Seconds since the previous frame.
        """
        self._mouth_elapsed = (self._mouth_elapsed + elapsed) % self.mouth_period
        phase = self._mouth_elapsed / self.mouth_period
        self.mouth_half_angle = 45.0 * (1.0 - abs(2.0 * phase - 1.0))

    def place_player(self, canvas: Canvas) -> None:
        """Initialize the shared movement's drawing position.

        Args:
            canvas: Canvas holding the current cell layout.
        """
        self.movement.place_movement(canvas)
        self.radius = canvas.cell_size * 0.375

    def request_move(self, direction: str, maze: Maze, canvas: Canvas) -> None:
        """Queue a turn, or start a cell-to-cell animation when stopped.

        Args:
            direction: Requested direction.
            maze: Maze used for wall checks.
            canvas: Canvas holding the current cell layout.
        """
        self.reserved_move = direction
        if self.movement.redirect(direction, maze, canvas):
            self.reserved_move = None

    def update_player(
        self,
        elapsed: float,
        maze: Maze,
        canvas: Canvas,
        pacgums: Pacgums,
    ) -> PacgumEatenEnum:
        """Animate, apply power-ups, and report which gum the player ate.

        Args:
            elapsed: Seconds since the previous frame.
            maze: Maze used for wall checks.
            canvas: Canvas holding the current cell layout.
            pacgums: Pacgums of the current level.

        Returns:
            The kind of pacgum eaten this frame.
        """
        if self.is_invincible:
            self.invincible_remain = max(0.0, self.invincible_remain - elapsed)
            if self.invincible_remain == 0.0:
                self.is_invincible = False
        if not self.movement.update_movement(elapsed, canvas):
            return PacgumEatenEnum.Neither
        eat_status = pacgums.consume_pacgum(self.movement.cell)
        if eat_status == PacgumEatenEnum.Super:
            self.is_invincible = True
            self.invincible_remain = self.INVINCIBLE_DURATION
        if self.reserved_move is not None and self.movement.start(
            self.reserved_move, maze, canvas
        ):
            self.reserved_move = None
        else:
            self.movement.start(self.movement.direction, maze, canvas)
        return eat_status

    def reset_player(self, canvas: Canvas) -> None:
        """Respawn at the initial cell and clear power-ups and queued turns.

        Args:
            canvas: Layout used for the radius and pixel center.
        """
        self.movement.reset_movement(canvas)
        self.reserved_move = None
        self.is_alive = True
        self.invincible_remain = 0.0
        self.radius = canvas.cell_size * 0.375
        self.is_invincible = False

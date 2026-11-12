"""Ghost state, role and movement strategy."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Unpack

from pacman.game.maze import Maze
from pacman.game.movement import Movement
from pacman.game.strategy import FleeBFSStrategy, Strategy, StrategyKwargs
from pacman.types import CellPosition, RGBColor

if TYPE_CHECKING:
    from pacman.visualize.canvas import Canvas


class GhostRole(Enum):
    """Identity of each ghost, used for its color and strategy."""

    RED = auto()
    CYAN = auto()
    PINK = auto()
    ORANGE = auto()


GHOST_COLORS: dict[GhostRole, RGBColor] = {
    GhostRole.RED: (255, 0, 0),
    GhostRole.PINK: (255, 184, 255),
    GhostRole.CYAN: (0, 255, 255),
    GhostRole.ORANGE: (255, 184, 82),
}


class Ghost:
    """Store one ghost's cell, appearance and current facing direction."""

    RESPAWN_DELAY = 5.0  # Seconds before an eaten ghost can move again.

    def __init__(
        self,
        cell: CellPosition,
        strategy: Strategy,
        color: RGBColor = GHOST_COLORS[GhostRole.RED],
        direction: str = "E",
        *,
        role: GhostRole | None = None,
    ) -> None:
        """Create a ghost with shared animation state and its own strategy.

        Args:
            cell: Spawn cell.
            strategy: Chase strategy used while not edible.
            color: Body color.
            direction: Initial facing direction.
            role: Ghost identity, used to find the red ghost.
        """
        self.movement = Movement(cell, speed=4.0, direction=direction)
        self.radius: float = 0.0
        self.respawn_remaining = 0.0
        self.color = color
        self.strategy = strategy
        self.flee_strategy = FleeBFSStrategy()
        self.role = role

    @property
    def cell(self) -> CellPosition:
        """Return the last cell center reached by the ghost.

        Returns:
            The ghost's current cell.
        """
        return self.movement.cell

    @property
    def direction(self) -> str:
        """Return the direction of the current animation.

        Returns:
            The ghost's facing direction.
        """
        return self.movement.direction

    def place_ghost(self, canvas: Canvas) -> None:
        """Initialize the shared movement's drawing position.

        Args:
            canvas: Canvas holding the current cell layout.
        """
        self.movement.place_movement(canvas)
        self.radius = canvas.cell_size * 0.375

    def update_ghost(
        self,
        elapsed: float,
        maze: Maze,
        canvas: Canvas,
        player_cell: CellPosition,
        player_dir: str,
        eatable: bool,
        target: CellPosition | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> None:
        """Choose a direction at cell centers and animate the chosen move.

        Args:
            elapsed: Seconds since the previous frame.
            maze: Maze used for wall checks.
            canvas: Canvas holding the current cell layout.
            player_cell: Cell the player last reached.
            player_dir: Direction the player is facing.
            eatable: Whether the player is invincible, making the ghost flee.
            target: Optional target cell passed to the strategy.
            **kwargs: Extra inputs such as red_pos (see StrategyKwargs).
        """
        if self.respawn_remaining > 0.0:
            self.respawn_remaining = max(0.0, self.respawn_remaining - elapsed)
            return
        if not self.movement.moving:
            if not eatable:
                if self.cell == player_cell:
                    return
                direction = self.strategy.choose_direction(
                    maze,
                    self.cell,
                    player_cell,
                    player_dir,
                    target=target,
                    **kwargs,
                )
                if direction is None:
                    return
                self.movement.start(direction, maze, canvas)
            else:
                direction = self.flee_strategy.choose_direction(
                    maze, self.cell, player_cell, player_dir, **kwargs
                )
                if direction is None:
                    return
                self.movement.start(direction, maze, canvas)
        self.movement.update_movement(elapsed, canvas)

    def reset_ghost(self, canvas: Canvas) -> None:
        """Return the ghost to its spawn cell and cancel respawn waiting.

        Args:
            canvas: Layout used for the radius and pixel center.
        """
        self.radius = canvas.cell_size * 0.375
        self.respawn_remaining = 0.0
        return self.movement.reset_movement(canvas)

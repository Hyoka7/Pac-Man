"""Ghost state, ready for future movement and rendering."""

from typing import Unpack

from game.maze import Maze
from game.movement import Movement
from game.strategy import FleeBFSStrategy, Strategy, StrategyKwargs
from visualize.image_renderer import ImageRenderer
from visualize.sprites import ghost_image
from visualize.visualizerutils import VisualizerUtils


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
        player_dir: str,
        eatable: bool,
        target: tuple[int, int] | None = None,
        **kwargs: Unpack[StrategyKwargs],
    ) -> None:
        """Choose a direction at cell centers and animate the chosen move."""
        if self.respawn_remaining > 0.0:
            self.respawn_remaining = max(0.0, self.respawn_remaining - elapsed)
            return
        if not self.movement.moving:
            if not eatable:
                if self.cell == player_cell:
                    return
                direction = self.strategy.choose_direction(
                    maze, self.cell, player_cell, player_dir, target=target,
                    **kwargs,
                )
                if direction is None:
                    return
                self.movement.start(direction, maze, canvas)
            else:
                flee = FleeBFSStrategy()
                direction = flee.choose_direction(
                    maze, self.cell, player_cell, player_dir, **kwargs
                )
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
        img = ghost_image(self.radius, color, self.direction)
        center_x, center_y = self.movement.center
        left = round(center_x - img.width / 2)
        top = round(center_y - img.height / 2)
        self.renderer.draw_image(canvas, left, top, img)

"""Pixel-coordinate movement shared by players and ghosts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pacman.game.directions import OPPOSITE_DIRECTIONS
from pacman.game.maze import Maze
from pacman.types import CellPosition, PixelPosition

if TYPE_CHECKING:
    from pacman.visualize.canvas import Canvas


class Movement:
    """Own a character's cell, pixel position and cell-to-cell motion."""

    def __init__(
        self,
        cell: CellPosition,
        speed: float = 5.0,
        direction: str = "E",
    ) -> None:
        """Set the initial cell and speed in cells per second.

        Args:
            cell: Starting cell.
            speed: Speed in cells per second.
            direction: Initial facing direction.
        """
        self.cell = cell
        self.initial_cell = cell
        # place() sets the actual pixel coordinates before drawing or movement.
        self.center: PixelPosition = (0.0, 0.0)
        self.target_cell = cell
        self.target: PixelPosition = self.center
        self.direction = direction
        self.speed = speed
        self.moving = False
        self.wallhack = False

    @staticmethod
    def move_towards(
        center: PixelPosition,
        target: PixelPosition,
        distance: float,
    ) -> PixelPosition:
        """Advance along one axis, stopping exactly at the target.

        Coordinates and distance are measured in pixels. The caller chooses a
        reachable neighboring cell and handles what happens on arrival.

        Args:
            center: Current pixel position.
            target: Pixel position on the same row or column.
            distance: Pixels to move this frame.

        Returns:
            The new position, never past the target.

        Raises:
            ValueError: If distance is negative or the target is diagonal.
        """
        if distance < 0:
            raise ValueError("movement distance must be non-negative")
        x, y = center
        target_x, target_y = target
        if x != target_x and y != target_y:
            raise ValueError("movement target must be horizontal or vertical")
        if x < target_x:
            x = min(x + distance, target_x)
        elif x > target_x:
            x = max(x - distance, target_x)
        if y < target_y:
            y = min(y + distance, target_y)
        elif y > target_y:
            y = max(y - distance, target_y)
        return x, y

    def place_movement(self, canvas: Canvas) -> None:
        """Place the character at its cell center once layout is available.

        Args:
            canvas: Canvas holding the current cell layout.
        """
        self.center = canvas.cell_center(*self.cell)
        self.target = self.center
        self.target_cell = self.cell
        self.moving = False

    def start(self, direction: str, maze: Maze, canvas: Canvas) -> bool:
        """Begin an allowed neighboring-cell animation when stopped.

        Args:
            direction: Direction: "N", "E", "S" or "W".
            maze: Maze used for wall checks.
            canvas: Canvas holding the current cell layout.

        Returns:
            True when a move started.
        """
        if self.moving or not maze.can_move(
            *self.cell, direction, self.wallhack
        ):
            return False
        self.center = canvas.cell_center(*self.cell)
        self.target_cell = maze.next_cell(*self.cell, direction)
        self.target = canvas.cell_center(*self.target_cell)
        self.direction = direction
        self.moving = True
        return True

    def update_movement(self, elapsed: float, canvas: Canvas) -> bool:
        """Advance one frame; return True only on arrival at the target cell.

        Args:
            elapsed: Seconds since the previous frame.
            canvas: Canvas holding the current cell layout.

        Returns:
            True only in the frame the target cell is reached.
        """
        if not self.moving:
            return False
        distance = canvas.cell_size * self.speed * elapsed
        self.center = self.move_towards(self.center, self.target, distance)
        if self.center != self.target:
            return False
        self.cell = self.target_cell
        self.moving = False
        return True

    def reset_movement(self, canvas: Canvas) -> None:
        """Move back to the initial cell and stop.

        Args:
            canvas: Layout used to place the pixel center.
        """
        self.cell = self.initial_cell
        self.place_movement(canvas)

    def _cell_distance(self, p1: float, p2: float) -> float:
        """Return the absolute distance between two coordinates.

        Args:
            p1: First coordinate in pixels.
            p2: Second coordinate in pixels.

        Returns:
            The absolute difference.
        """
        return abs(p1 - p2)

    def redirect(self, req_dir: str, maze: Maze, canvas: Canvas) -> bool:
        """Apply a requested direction while stopped or moving.

        Reversing is always allowed; a perpendicular turn is allowed
        near the current cell center when the passage is open.

        Args:
            req_dir: Requested direction ("N", "E", "S" or "W").
            maze: Maze used for wall checks.
            canvas: Layout used for pixel centers.

        Returns:
            True when the direction was applied immediately.
        """
        if not self.moving:
            return self.start(req_dir, maze, canvas)
        if req_dir == self.direction:
            return False
        else:
            if req_dir == OPPOSITE_DIRECTIONS[self.direction]:
                new_target = maze.next_cell(
                    *self.target_cell,
                    req_dir,
                )
                self.target_cell = new_target
                self.target = canvas.cell_center(*new_target)
                self.direction = req_dir
                return True
            diff_x = self._cell_distance(
                self.center[0], canvas.cell_center(*self.cell)[0]
            )
            diff_y = self._cell_distance(
                self.center[1], canvas.cell_center(*self.cell)[1]
            )
            # 交差点曲がり判定幅：小さいほど厳密
            allowed_distance = canvas.cell_size / 4
            if (
                diff_x <= allowed_distance
                and diff_y <= allowed_distance
                and maze.can_move(*self.cell, req_dir, self.wallhack)
            ):
                self.moving = False
                return self.start(req_dir, maze, canvas)
            return False

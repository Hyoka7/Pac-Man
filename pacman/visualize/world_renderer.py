"""Draw game entities without storing rendering services in their state."""

from math import ceil, floor

from pacman.game.ghost import Ghost
from pacman.game.maze import Maze
from pacman.game.pacgums import Pacgums
from pacman.game.player import Player
from pacman.types import RGBColor
from pacman.visualize.canvas import Canvas
from pacman.visualize.image_renderer import ImageRenderer
from pacman.visualize.sprites import ghost_image, player_image


class WorldRenderer:
    RESPAWN_BLINK_DURATION = 1.5
    INVINCIBLE_BLINK_DURATION = 1.5
    BLINK_INTERVAL = 0.2  # Seconds per visible/color phase.

    def __init__(self) -> None:
        self.images = ImageRenderer()

    def draw_player(self, player: Player, canvas: Canvas) -> None:
        """Draw the player at its current interpolated center."""
        center_x, center_y = player.movement.center
        mouth_step = round(player.mouth_half_angle / 45 * 10)
        img = player_image(player.radius, player.movement.direction, mouth_step)
        left = round(center_x - img.width / 2)
        top = round(center_y - img.height / 2)
        self.images.draw_image(canvas, left, top, img)

    def draw_ghost(
        self,
        ghost: Ghost,
        canvas: Canvas,
        eatable: bool,
        eatable_remain: float,
    ) -> None:
        """Draw the ghost with its existing respawn and power-up flashes."""
        if ghost.respawn_remaining > self.RESPAWN_BLINK_DURATION:
            return
        elif ghost.respawn_remaining > 0.0:
            is_visible = int(ghost.respawn_remaining / self.BLINK_INTERVAL % 2)
            if not is_visible:
                return
        if eatable:
            if eatable_remain > self.INVINCIBLE_BLINK_DURATION:
                color = (0, 0, 128)
            elif int(eatable_remain / self.BLINK_INTERVAL) % 2:
                color = ghost.color
            else:
                color = (0, 0, 128)
        else:
            color = ghost.color
        img = ghost_image(ghost.radius, color, ghost.direction)
        center_x, center_y = ghost.movement.center
        left = round(center_x - img.width / 2)
        top = round(center_y - img.height / 2)
        self.images.draw_image(canvas, left, top, img)

    def draw_maze(
        self,
        maze: Maze,
        canvas: Canvas,
        wall_color: RGBColor,
        landmark_color: RGBColor,
    ) -> None:
        """Draw the maze and enclosed 42 cells."""

        def _draw_line(x0: int, y0: int, x1: int, y1: int) -> None:
            canvas.fill_cell(x0, y0, x1 + 1, y1 + 1, wall_color)

        for y, row in enumerate(maze.maze):
            for x, cell in enumerate(row):
                x0 = canvas.offset_x + x * canvas.cell_size
                y0 = canvas.offset_y + y * canvas.cell_size
                x1 = x0 + canvas.cell_size
                y1 = y0 + canvas.cell_size
                if cell == 15:
                    canvas.fill_cell(x0, y0, x1, y1, landmark_color)
                if cell & 1:
                    _draw_line(x0, y0, x1, y0)
                if cell & 2:
                    _draw_line(x1, y0, x1, y1)
                if cell & 4:
                    _draw_line(x0, y1, x1, y1)
                if cell & 8:
                    _draw_line(x0, y0, x0, y1)

    def _draw_gum(
        self,
        canvas: Canvas,
        center_x: float,
        center_y: float,
        radius: float,
        color: RGBColor,
    ) -> None:
        """Draw a clipped solid circle using the existing pixel-center test."""
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
                canvas.draw_pixel(x, y, color)

    def draw_pacgums(self, pacgums: Pacgums, canvas: Canvas) -> None:
        """Draw only the pacgums that have not been eaten."""
        for x, y in pacgums.remain_gums:
            center_x, center_y = canvas.cell_center(x, y)
            self._draw_gum(
                canvas, center_x, center_y, canvas.cell_size * 0.05, (255, 255, 255)
            )
        for x, y in pacgums.super_gums:
            center_x, center_y = canvas.cell_center(x, y)
            self._draw_gum(
                canvas, center_x, center_y, canvas.cell_size * 0.15, (255, 255, 0)
            )

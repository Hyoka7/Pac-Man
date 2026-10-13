"""Render a maze of wall bitmasks using MiniLibX."""

from __future__ import annotations

import time
from math import ceil, floor, hypot


class MazeVisualizer:
    """Display walls and fill enclosed '42' cells (wall mask 15)."""

    def __init__(self, maze: list[list[int]]) -> None:
        if not maze or not maze[0]:
            raise ValueError("maze must not be empty")
        self.rows = len(maze)
        self.cols = len(maze[0])
        if any(len(row) != self.cols for row in maze):
            raise ValueError("maze must be rectangular")
        if any(
            type(cell) is not int or not 0 <= cell <= 15 for row in maze for cell in row
        ):
            raise ValueError("each cell must be an integer wall mask (0..15)")
        self.maze = [row[:] for row in maze]
        self.cmodes = [
            ((126, 249, 255), (255, 92, 138), (145, 255, 174)),
            ((89, 196, 255), (255, 204, 92), (77, 255, 218)),
            ((255, 167, 92), (255, 80, 120), (255, 231, 128)),
            ((255, 183, 213), (255, 92, 147), (204, 178, 255)),
            ((112, 224, 151), (255, 194, 92), (173, 255, 108)),
            ((0, 240, 255), (255, 45, 190), (247, 255, 0)),
            ((190, 168, 255), (255, 145, 200), (132, 224, 255)),
            ((255, 112, 67), (255, 213, 79), (255, 171, 145)),
            ((185, 230, 255), (110, 168, 255), (225, 255, 255)),
            ((128, 255, 214), (255, 148, 180), (211, 255, 140)),
            ((165, 148, 255), (255, 196, 82), (104, 214, 255)),
            ((224, 230, 238), (255, 105, 105), (112, 224, 178)),
        ]
        self.cm = 0
        self.closed = True
        self.player_pos = (0, 0)
        self.move_to = (0, 0)
        self.move_to_cell = (0, 0)
        self.player_dir = "E"
        self.moving = False
        self.ult = False
        self.move_speed = 5
        self.last_time = time.monotonic()

    def _color_bytes(self, color: tuple[int, int, int]) -> bytes:
        """Encode an opaque RGB color in the image's byte order."""
        r, g, b = color
        if self.img_format == 0:
            return bytes([b, g, r, 255])
        return bytes([255, r, g, b])

    def _cell_center(self, x: int, y: int) -> tuple[float, float]:
        """Convert a maze cell to its center in screen pixels."""
        center_x = self.margin + (x + 0.5) * self.cell_size
        center_y = self.margin + (y + 0.5) * self.cell_size
        return (center_x, center_y)

    def _clear_image(self) -> None:
        """Clear the image buffer to opaque black."""
        row_blank = self._color_bytes((0, 0, 0)) * self.width
        for y in range(self.height):
            idx = y * self.line_size
            self.img_data[idx : idx + len(row_blank)] = row_blank

    def _fill_cell(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        color: tuple[int, int, int],
    ) -> None:
        """Fill a clipped rectangle, excluding its right and bottom edges."""
        start_x = max(0, min(x0, self.width))
        end_x = max(0, min(x1, self.width))
        start_y = max(0, min(y0, self.height))
        end_y = max(0, min(y1, self.height))
        if start_x >= end_x or start_y >= end_y:
            return
        row_segment = self._color_bytes(color) * (end_x - start_x)
        for y in range(start_y, end_y):
            idx = y * self.line_size + start_x * self.bytes_per_pixel
            self.img_data[idx : idx + len(row_segment)] = row_segment

    def _line(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Draw an inclusive horizontal or vertical wall into the buffer."""
        self._fill_cell(x0, y0, x1 + 1, y1 + 1, self.cmodes[self.cm][0])

    def _draw_player(self, center_x: float, center_y: float, dir: str) -> None:
        """Draw the player inside a maze cell."""
        radius = self.cell_size * 0.375

        def _circle_coverage(x_pixel: float, y_pixel: float) -> float:
            """Fade across a one-pixel band around the circle boundary."""
            distance = hypot(x_pixel - center_x, y_pixel - center_y)
            return max(0.0, min(1.0, radius + 0.5 - distance))

        def _is_in_mouth_horizon(x_pixel: float, y_pixel: float, dir: str) -> bool:
            dx = x_pixel - center_x
            dy = y_pixel - center_y
            return (
                abs(dy) <= abs(dx) and dx > 0
                if dir == "E"
                else abs(dy) <= abs(dx) and dx < 0
            )

        def _is_in_mouth_vertical(x_pixel: float, y_pixel: float, dir: str) -> bool:
            dx = x_pixel - center_x
            dy = y_pixel - center_y
            return (
                abs(dx) <= abs(dy) and dy > 0
                if dir == "S"
                else abs(dx) <= abs(dy) and dy < 0
            )

        samples = (0.125, 0.375, 0.625, 0.875)
        for y in range(
            max(floor(center_y - radius - 0.5), 0),
            min(ceil(center_y + radius + 0.5), self.height),
        ):
            for x in range(
                max(0, floor(center_x - radius - 0.5)),
                min(self.width, ceil(center_x + radius + 0.5)),
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
                pixel_start = y * self.line_size + x * self.bytes_per_pixel
                pixel_end = pixel_start + self.bytes_per_pixel
                background = self.img_data[pixel_start:pixel_end]
                if self.img_format == 0:
                    b, g, r, _ = background
                else:
                    _, r, g, b = background
                color = (
                    round(r * (1 - coverage) + 255 * coverage),
                    round(g * (1 - coverage) + 255 * coverage),
                    round(b * (1 - coverage)),
                )
                self.img_data[pixel_start:pixel_end] = self._color_bytes(color)

    def _draw(self, _param: object = None) -> None:
        if self.closed:
            return
        self._clear_image()
        for y, row in enumerate(self.maze):
            for x, cell in enumerate(row):
                x0 = self.margin + x * self.cell_size
                y0 = self.margin + y * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                if cell == 15:
                    self._fill_cell(x0, y0, x1, y1, self.cmodes[self.cm][1])
                if cell & 1:
                    self._line(x0, y0, x1, y0)
                if cell & 2:
                    self._line(x1, y0, x1, y1)
                if cell & 4:
                    self._line(x0, y1, x1, y1)
                if cell & 8:
                    self._line(x0, y0, x0, y1)
        self._draw_player(self.player_center_x, self.player_center_y, self.player_dir)
        self.m.mlx_put_image_to_window(self.p, self.win, self.img, 0, 0)

    def _close(self, _param: object = None) -> None:
        if self.closed:
            return
        self.closed = True
        self.m.mlx_destroy_image(self.p, self.img)
        self.m.mlx_destroy_window(self.p, self.win)
        self.m.mlx_loop_exit(self.p)

    def _on_loop(self, _param: object) -> None:
        """Calculate the frame's movement distance and advance the player."""
        del _param
        prev_time = self.last_time
        self.last_time = time.monotonic()
        moving_pace = self.cell_size * self.move_speed * (self.last_time - prev_time)
        self._move_player(moving_pace)

    def _move_player(self, moving_pace: float) -> None:
        """Advance toward the target by a distance measured in pixels."""
        if self.moving:
            if self.player_dir == "N":
                self.player_center_y = max(
                    self.move_to[1], self.player_center_y - moving_pace
                )
                self._draw()

            elif self.player_dir == "S":
                self.player_center_y = min(
                    (self.move_to[1], self.player_center_y + moving_pace),
                )
                self._draw()
            elif self.player_dir == "W":
                self.player_center_x = max(
                    self.player_center_x - moving_pace, self.move_to[0]
                )
                self._draw()
            elif self.player_dir == "E":
                self.player_center_x = min(
                    (self.player_center_x + moving_pace, self.move_to[0]),
                )
                self._draw()
            if (self.player_center_x, self.player_center_y) == self.move_to:
                self.player_pos = self.move_to_cell
                if self._can_move(*self.player_pos, self.player_dir):
                    self.move_to_cell = self._next_cell(
                        *self.player_pos, self.player_dir
                    )
                    self.move_to = self._cell_center(*self.move_to_cell)
                    self.moving = True
                else:
                    self.moving = False

    def _next_cell(self, x: int, y: int, direction: str) -> tuple[int, int]:
        """Return the adjacent cell; walls and bounds are checked separately."""
        offsets = {
            "N": (0, -1),
            "E": (1, 0),
            "S": (0, 1),
            "W": (-1, 0),
        }
        if direction not in offsets:
            raise ValueError("direction must be N, E, S or W")
        dx, dy = offsets[direction]
        return x + dx, y + dy

    def _can_move(self, x: int, y: int, direction: str) -> bool:
        """Return whether a cell has an in-bounds passage in a direction."""
        directions = {
            "N": 1,
            "E": 2,
            "S": 4,
            "W": 8,
        }
        if direction not in directions:
            return False
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return False
        next_x, next_y = self._next_cell(x, y, direction)
        wall = directions[direction]
        return (
            0 <= next_x < self.cols
            and 0 <= next_y < self.rows
            and self.maze[y][x] & wall == 0
        )

    def _on_key(self, key: int, _param: object = None) -> None:
        del _param
        if self.closed:
            return
        if key == 65307:  # Escape (X11)
            self._close()
        if key == 117:
            if self.ult:
                self.move_speed = 5
            else:
                self.move_speed = 10
            self.ult = not self.ult
        elif key in (99, 67):  # C / Shift+C (X11)
            self.cm = (self.cm + 1) % len(self.cmodes)
            self._draw()
        elif self.moving:
            return
        elif key == 65361 or key == 97:
            center_x, center_y = self.player_pos
            if self._can_move(center_x, center_y, "W"):
                self.player_dir = "W"
                self.moving = True
                self.move_to_cell = self._next_cell(center_x, center_y, "W")
                self.player_center_x, self.player_center_y = self._cell_center(
                    *self.player_pos
                )
                self.move_to = self._cell_center(
                    *self._next_cell(center_x, center_y, "W")
                )
                self._draw()
        elif key == 65362 or key == 119:
            center_x, center_y = self.player_pos
            if self._can_move(center_x, center_y, "N"):
                self.moving = True
                self.move_to = self._cell_center(
                    *self._next_cell(center_x, center_y, "N")
                )
                self.move_to_cell = self._next_cell(center_x, center_y, "N")
                self.player_dir = "N"
                self.player_center_x, self.player_center_y = self._cell_center(
                    *self.player_pos
                )
                self._draw()
        elif key == 65363 or key == 100:
            center_x, center_y = self.player_pos
            if self._can_move(center_x, center_y, "E"):
                self.moving = True
                self.move_to = self._cell_center(
                    *self._next_cell(center_x, center_y, "E")
                )
                self.player_dir = "E"
                self.move_to_cell = self._next_cell(center_x, center_y, "E")
                self.player_center_x, self.player_center_y = self._cell_center(
                    *self.player_pos
                )
                self._draw()
        elif key == 65364 or key == 115:
            center_x, center_y = self.player_pos
            if self._can_move(center_x, center_y, "S"):
                self.moving = True
                self.move_to = self._cell_center(
                    *self._next_cell(center_x, center_y, "S")
                )
                self.player_dir = "S"
                self.move_to_cell = self._next_cell(center_x, center_y, "S")
                self.player_center_x, self.player_center_y = self._cell_center(
                    *self.player_pos
                )
                self._draw()
        print(key, self.player_pos)
        # Left: 65361
        # Up: 65362
        # Right: 65363
        # Down: 65364

    def run(self) -> None:
        """Open the window and display the maze until it is closed."""
        from mlx import Mlx

        self.m = Mlx()
        self.p = self.m.mlx_init()
        if self.p is None:
            raise RuntimeError("MLX initialization failed")

        _, screen_width, screen_height = self.m.mlx_get_screen_size(self.p)
        self.margin = 20
        self.cell_size = min(
            32,
            (screen_width - 100 - 2 * self.margin - 1) // self.cols,
            (screen_height - 100 - 2 * self.margin - 1) // self.rows,
        )

        if self.cell_size < 1:
            raise ValueError("maze is too large for the screen")
        self.player_center_x, self.player_center_y = self._cell_center(*self.player_pos)
        self.width = self.cols * self.cell_size + 2 * self.margin + 1
        self.height = self.rows * self.cell_size + 2 * self.margin + 1
        self.win = self.m.mlx_new_window(self.p, self.width, self.height, "Maze Viewer")
        if self.win is None:
            raise RuntimeError("MLX window creation failed")
        self.img = self.m.mlx_new_image(self.p, self.width, self.height)
        if self.img is None:
            self.m.mlx_destroy_window(self.p, self.win)
            raise RuntimeError("MLX image creation failed")
        self.closed = False
        try:
            self.img_data, bpp, self.line_size, self.img_format = (
                self.m.mlx_get_data_addr(self.img)
            )
            self.bytes_per_pixel = bpp // 8
            if bpp != 32 or self.img_format not in (0, 1):
                raise RuntimeError("Unsupported MLX image format")
            self.m.mlx_loop_hook(self.p, self._on_loop, None)
            self.m.mlx_key_hook(self.win, self._on_key, None)
            self.m.mlx_expose_hook(self.win, self._draw, None)
            self.m.mlx_hook(self.win, 33, 0, self._close, None)
            self._draw()
            self.m.mlx_loop(self.p)
        finally:
            self._close()

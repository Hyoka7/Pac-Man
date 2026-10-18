"""Shared image-buffer drawing and screen-coordinate conversion."""


class VisualizerUtils:
    """Own the image buffer and layout used by all renderers."""

    def __init__(
        self,
        width: int,
        height: int,
        cell_size: int,
        margin: int,
        img_data: memoryview,
        line_size: int,
        img_format: int,
    ) -> None:
        """Attach a 32-bit MLX buffer to a screen layout."""
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.margin = margin
        self.img_data = img_data
        self.line_size = line_size
        self.img_format = img_format
        self.bytes_per_pixel = 4

    def color_bytes(self, color: tuple[int, int, int]) -> bytes:
        """Encode an opaque RGB color in the image's byte order."""
        r, g, b = color
        if self.img_format == 0:
            return bytes([b, g, r, 255])
        return bytes([255, r, g, b])

    def draw_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        """Paint one pixel with a solid color, ignoring off-screen points."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        pixel_start = y * self.line_size + x * self.bytes_per_pixel
        pixel_end = pixel_start + self.bytes_per_pixel
        self.img_data[pixel_start:pixel_end] = self.color_bytes(color)

    def draw_pixel_aa(
        self,
        x: int,
        y: int,
        color: tuple[int, int, int],
        coverage: float,
    ) -> None:
        """Blend a pixel with its background using coverage from 0 to 1.

        Shape rendering calculates coverage; this method writes the result.
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        coverage = max(0.0, min(1.0, coverage))
        if coverage == 0:
            return
        if coverage == 1:
            self.draw_pixel(x, y, color)
            return
        pixel_start = y * self.line_size + x * self.bytes_per_pixel
        pixel_end = pixel_start + self.bytes_per_pixel
        background = self.img_data[pixel_start:pixel_end]
        if self.img_format == 0:
            b, g, r, _ = background
        else:
            _, r, g, b = background
        blended = (
            round(r * (1 - coverage) + color[0] * coverage),
            round(g * (1 - coverage) + color[1] * coverage),
            round(b * (1 - coverage) + color[2] * coverage),
        )
        self.draw_pixel(x, y, blended)

    def cell_center(self, x: int, y: int) -> tuple[float, float]:
        """Convert a maze cell to its center in screen pixels."""
        center_x = self.margin + (x + 0.5) * self.cell_size
        center_y = self.margin + (y + 0.5) * self.cell_size
        return (center_x, center_y)

    def clear_image(self) -> None:
        """Clear the image buffer to opaque black."""
        row_blank = self.color_bytes((0, 0, 0)) * self.width
        for y in range(self.height):
            idx = y * self.line_size
            self.img_data[idx : idx + len(row_blank)] = row_blank

    def is_in_circle(
        self,
        x_pixel: float,
        y_pixel: float,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> bool:
        """Return whether a point lies inside or on the circle."""
        dx = x_pixel - center_x
        dy = y_pixel - center_y
        return dx**2 + dy**2 <= radius**2

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
        row_segment = self.color_bytes(color) * (end_x - start_x)
        for y in range(start_y, end_y):
            idx = y * self.line_size + start_x * self.bytes_per_pixel
            self.img_data[idx : idx + len(row_segment)] = row_segment

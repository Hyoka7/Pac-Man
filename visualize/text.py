"""Draw Pillow text into the same image buffer as the game."""

from functools import cache

from PIL import Image, ImageDraw, ImageFont

from .visualizerutils import VisualizerUtils


@cache
def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


@cache
def _text_image(
    text: str,
    color: tuple[int, int, int],
    size: int,
) -> Image.Image:
    """Keep only the glyph bounds, including antialiased transparent edges."""
    font = _font(size)
    left, top, right, bottom = font.getbbox(text)
    image = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((-left, -top), text, fill=(*color, 255), font=font)
    return image


class TextRenderer:
    """Generate, measure and composite cached text images onto a canvas."""

    def _font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return _font(size)

    def _text_image(
        self,
        text: str,
        color: tuple[int, int, int],
        size: int,
    ) -> Image.Image:
        return _text_image(text, color, size)

    def text_size(self, text: str, size: int = 20) -> tuple[int, int]:
        """Return the width and height needed for a single line of text."""
        return self._text_image(text, (255, 255, 255), size).size

    def draw_image(
        self, canvas: VisualizerUtils, x: int, y: int, image: Image.Image
    ) -> None:

        row_bytes = []
        width, height = image.size
        left = max(0, x)
        top = max(0, y)
        right = min(canvas.width, x + width)
        bottom = min(canvas.height, y + height)
        if left >= right or top >= bottom:
            return
        image = image.crop(
            (
                left - x,
                top - y,
                right - x,
                bottom - y,
            )
        )
        x, y = left, top
        width, height = image.size
        for row in range(height):
            start = (y + row) * canvas.line_size + x * 4
            end = start + width * 4
            background_row = bytes(canvas.img_data[start:end])
            row_bytes.append(background_row)
        background_all = b"".join(row_bytes)
        mode = "BGRA" if canvas.img_format == 0 else "ARGB"
        background = Image.frombytes(
            "RGBA",
            (width, height),
            background_all,
            "raw",
            mode,
        )
        background.alpha_composite(image)
        if canvas.img_format == 0:
            result = background.tobytes("raw", "BGRA")
        else:
            r, g, b, a = background.split()
            result = Image.merge("RGBA", (a, r, g, b)).tobytes()
        for row in range(height):
            start = (y + row) * canvas.line_size + x * 4
            source_start = row * width * 4
            canvas.img_data[start : start + width * 4] = result[
                source_start : source_start + width * 4
            ]

    def draw_text(
        self,
        canvas: VisualizerUtils,
        x: int,
        y: int,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        size: int = 20,
    ) -> None:
        """Blend a text image at its top-left position without native text calls."""
        if not text:
            return
        image = self._text_image(text, color, size)
        self.draw_image(canvas, x, y, image)

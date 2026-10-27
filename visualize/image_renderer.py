"""Composite Pillow images and cached text into the game buffer."""

from functools import cache
from typing import cast

from PIL import Image, ImageDraw, ImageFont

from .visualizerutils import VisualizerUtils


@cache
def _font(size: int) -> ImageFont.FreeTypeFont:
    return cast(ImageFont.FreeTypeFont, ImageFont.load_default(size=size))


@cache
def _text_image(
    text: str,
    color: tuple[int, int, int],
    size: int,
) -> Image.Image:
    """Keep only the glyph bounds, including antialiased transparent edges."""
    font = _font(size)
    ascent, descent = font.getmetrics()
    left, _, right, _ = font.getbbox(text)
    image = Image.new("RGBA", (int(right - left), ascent + descent), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((-left, 0), text, fill=(*color, 255), font=font)
    return image


class ImageRenderer:
    """Generate, measure and composite cached text images onto a canvas."""

    def __init__(self) -> None:
        self.numeric_cache: dict[
            str, tuple[str, tuple[int, int, int], int, Image.Image]
        ] = {}

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
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

        row_bytes: list[bytes] = []
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

    def _split(self, text: str) -> list[str]:
        num_state = False
        splitted = []
        s = ""
        for c in text:
            if num_state:
                if c.isnumeric() or c == ".":
                    splitted.append(c)
                else:
                    num_state = False
                    s += c
            else:
                if c.isnumeric() or c == ".":
                    num_state = True
                    if len(s):
                        splitted.append(s)
                    splitted.append(c)
                    s = ""
                else:
                    s += c
        if len(s):
            splitted.append(s)
        return splitted

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

    def numeric_text_image(
        self,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        size: int = 20,
        *,
        slot: str = "hud",
    ) -> Image.Image:
        """Get the latest composed image for measurement and drawing."""
        cached = self.numeric_cache.get(slot)
        if cached is not None and (text, color, size) == cached[:3]:
            return cached[3]
        if not text:
            ascent, descent = self._font(size).getmetrics()
            return Image.new("RGBA", (0, ascent + descent), (0, 0, 0, 0))
        parts = self._split(text)
        imgs = [_text_image(part, color, size) for part in parts]
        width = sum(img.width for img in imgs)
        image = Image.new("RGBA", (width, imgs[0].height), (0, 0, 0, 0))
        offset_x = 0
        for img in imgs:
            image.alpha_composite(img, dest=(offset_x, 0))
            offset_x += img.width
        self.numeric_cache[slot] = (text, color, size, image)
        return image

    def draw_numeric_text(
        self,
        canvas: VisualizerUtils,
        x: int,
        y: int,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        size: int = 20,
        *,
        slot: str = "hud",
    ) -> None:
        if not text:
            return
        image = self.numeric_text_image(text, color, size, slot=slot)
        self.draw_image(canvas, x, y, image)

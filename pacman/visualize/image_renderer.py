"""Composite Pillow images and cached text into the game buffer."""

from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pacman.types import RGBColor
from pacman.visualize.canvas import Canvas

type NumericTextCacheEntry = tuple[str, RGBColor, int, Image.Image]
"""Cached text, RGB color, font size and the resulting composed image."""


@cache
def _font(size: int) -> ImageFont.FreeTypeFont:
    """Load the bundled pixel font at a size, cached per size.

    Args:
        size: Font size in pixels.

    Returns:
        The FreeType font.

    Raises:
        OSError: If the font file cannot be loaded.
    """
    return ImageFont.truetype(
        Path(__file__).resolve().parents[2]
        / "assets/fonts/PressStart2P-Regular.ttf",
        size=size,
    )


@cache
def _text_image(
    text: str,
    color: RGBColor,
    size: int,
) -> Image.Image:
    """Keep only the glyph bounds, including antialiased transparent edges.

    Args:
        text: Text to render.
        color: RGB color.
        size: Font size in pixels.

    Returns:
        A transparent RGBA image cropped to the glyphs' width.
    """
    font = _font(size)
    ascent, descent = font.getmetrics()
    left, _, right, _ = font.getbbox(text)
    image = Image.new(
        "RGBA", (int(right - left), ascent + descent), (0, 0, 0, 0)
    )
    ImageDraw.Draw(image).text((-left, 0), text, fill=(*color, 255), font=font)
    return image


class ImageRenderer:
    """Generate, measure and composite cached text images onto a canvas."""

    def __init__(self) -> None:
        """Prepare the per-slot cache for numeric text images."""
        self.numeric_cache: dict[str, NumericTextCacheEntry] = {}

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        """Return the cached bundled font at a size.

        Args:
            size: Font size in pixels.

        Returns:
            The FreeType font.
        """
        return _font(size)

    def text_image(
        self,
        text: str,
        color: RGBColor,
        size: int,
    ) -> Image.Image:
        """Return the cached RGBA image of a text string.

        Args:
            text: Text to render.
            color: RGB color.
            size: Font size in pixels.

        Returns:
            A transparent RGBA image of the text.
        """
        return _text_image(text, color, size)

    def text_size(self, text: str, size: int = 20) -> tuple[int, int]:
        """Return the width and height needed for a single line of text.

        Args:
            text: Text to render.
            size: Font size in pixels.

        Returns:
            The width and height in pixels.
        """
        return self.text_image(text, (255, 255, 255), size).size

    def draw_image(
        self,
        canvas: Canvas,
        dest_x: int,
        dest_y: int,
        image: Image.Image,
    ) -> None:
        """Alpha-composite an RGBA image onto the canvas buffer.

        The visible area is cropped, blended with the existing pixels
        and written back row by row in the buffer's byte order.

        Args:
            canvas: Destination canvas.
            dest_x: Left edge in pixels; may be off-screen.
            dest_y: Top edge in pixels; may be off-screen.
            image: RGBA image to draw.
        """
        row_bytes: list[bytes] = []
        bytes_per_pixel = canvas.bytes_per_pixel
        width, height = image.size
        left = max(0, dest_x)
        top = max(0, dest_y)
        right = min(canvas.width, dest_x + width)
        bottom = min(canvas.height, dest_y + height)
        if left >= right or top >= bottom:
            return
        image = image.crop(
            (
                left - dest_x,
                top - dest_y,
                right - dest_x,
                bottom - dest_y,
            )
        )
        dest_x, dest_y = left, top
        width, height = image.size
        for row in range(height):
            start = (
                dest_y + row
            ) * canvas.line_size + dest_x * bytes_per_pixel
            end = start + width * bytes_per_pixel
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
            start = (
                dest_y + row
            ) * canvas.line_size + dest_x * bytes_per_pixel
            source_start = row * width * bytes_per_pixel
            row_size = width * bytes_per_pixel
            canvas.img_data[start:start + row_size] = result[
                source_start:source_start + row_size
            ]

    def _split(self, text: str) -> list[str]:
        """Split text into digit or dot characters and other runs.

        Returns:
            Parts such as ["Score:", "1", "2"] so digit images are reused.

        Args:
            text: Text to split.
        """
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
        canvas: Canvas,
        x: int,
        y: int,
        text: str,
        color: RGBColor = (255, 255, 255),
        size: int = 20,
    ) -> None:
        """Blend a text image with its top-left corner at (x, y).

        Args:
            canvas: Destination canvas.
            x: Left edge in pixels.
            y: Top edge in pixels.
            text: Text to render.
            color: RGB color.
            size: Font size in pixels.
        """
        if not text:
            return
        image = self.text_image(text, color, size)
        self.draw_image(canvas, x, y, image)

    def numeric_text_image(
        self,
        text: str,
        color: RGBColor = (255, 255, 255),
        size: int = 20,
        slot: str = "hud",
    ) -> Image.Image:
        """Get the latest composed image for measurement and drawing.

        Args:
            text: Text to render.
            color: RGB color.
            size: Font size in pixels.
            slot: Cache slot for this text, such as "hud" or "invincible".

        Returns:
            The composed RGBA image, reused while the text is unchanged.
        """
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
        canvas: Canvas,
        x: int,
        y: int,
        text: str,
        color: RGBColor = (255, 255, 255),
        size: int = 20,
        *,
        slot: str = "hud",
    ) -> None:
        """Draw text whose digits change often, reusing cached images.

        Args:
            canvas: Destination canvas.
            x: Left edge in pixels.
            y: Top edge in pixels.
            text: Text to render.
            color: RGB color.
            size: Font size in pixels.
            slot: Cache slot for this text, such as "hud" or "invincible".
        """
        if not text:
            return
        image = self.numeric_text_image(text, color, size, slot=slot)
        self.draw_image(canvas, x, y, image)

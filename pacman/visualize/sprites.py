"""Cached pixel sprites shared by character and menu rendering."""

from functools import cache
from math import ceil, hypot, radians, tan

from PIL import Image

from pacman.types import RGBColor


@cache
def player_image(
    radius: float,
    direction: str,
    mouth_step: int,
) -> Image.Image:
    side = ceil(radius * 2)
    palette = Image.new(
        "RGBA",
        (16, 16),
        (0, 0, 0, 0),
    )

    mouth_angle_half = 45 * mouth_step / 10
    mouth_slope = tan(radians(mouth_angle_half))

    def _is_in_mouth(dx: float, dy: float) -> bool:
        """Return whether a point relative to the center is inside the mouth."""
        if direction == "E":
            forward, across = dx, dy
        elif direction == "W":
            forward, across = -dx, dy
        elif direction == "S":
            forward, across = dy, dx
        else:
            forward, across = -dy, dx
        return (
            mouth_step > 0
            and forward > 0
            and abs(across) <= forward * mouth_slope
        )

    for y in range(16):
        for x in range(16):
            dx = x - 7.5
            dy = y - 7.5
            if dx * dx + dy * dy <= 8 * 8 and not _is_in_mouth(dx, dy):
                palette.putpixel((x, y), (255, 255, 0, 255))
    return palette.resize((side, side), resample=Image.Resampling.NEAREST)


@cache
def ghost_image(
    radius: float,
    color: RGBColor,
    direction: str,
) -> Image.Image:
    side = ceil(radius * 2) + 2
    img = Image.new(
        "RGBA",
        (side, side),
        (0, 0, 0, 0),
    )
    palette = Image.new(
        "RGBA",
        (16, 16),
        (0, 0, 0, 0),
    )
    center_x, center_y = 8.0, 8.0
    sprite_radius = 8.0
    notch_depth = 2.0
    notch_half_width = 1.0
    for y in range(16):
        for x in range(16):
            dx = x + 0.5 - center_x
            dy = y + 0.5 - center_y
            if dy <= 0:
                if hypot(dx, dy) <= sprite_radius:
                    palette.putpixel((x, y), (*color, 255))
                continue
            distance = max(abs(dx) - sprite_radius, dy - sprite_radius)
            if distance > 0:
                continue
            in_notch = False
            for notch_x in (-sprite_radius / 2, 0.0, sprite_radius / 2):
                if (
                    abs(dx - notch_x) <= notch_half_width
                    and dy >= sprite_radius - notch_depth
                ):
                    in_notch = True
                    break
            if not in_notch:
                palette.putpixel((x, y), (*color, 255))

    def range_putpixel(
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        img: Image.Image,
        color: tuple[
            int,
            int,
            int,
            int,
        ],
    ) -> None:
        for y in range(start_y, end_y + 1):
            for x in range(start_x, end_x + 1):
                img.putpixel((x, y), color)

    blackeye_start = {
        "E": (2, 1),
        "W": (0, 1),
        "N": (1, 0),
        "S": (1, 2),
    }
    range_putpixel(3, 5, 6, 8, palette, (255, 255, 255, 255))
    range_putpixel(9, 5, 12, 8, palette, (255, 255, 255, 255))
    left_blackeye_start_x, left_blackeye_start_y = (
        3 + blackeye_start[direction][0],
        5 + blackeye_start[direction][1],
    )
    range_putpixel(
        left_blackeye_start_x,
        left_blackeye_start_y,
        left_blackeye_start_x + 1,
        left_blackeye_start_y + 1,
        palette,
        (0, 0, 0, 255),
    )
    right_blackeye_start_x, right_blackeye_start_y = (
        9 + blackeye_start[direction][0],
        5 + blackeye_start[direction][1],
    )
    range_putpixel(
        right_blackeye_start_x,
        right_blackeye_start_y,
        right_blackeye_start_x + 1,
        right_blackeye_start_y + 1,
        palette,
        (0, 0, 0, 255),
    )

    zoomed = palette.resize((side - 2, side - 2), resample=Image.Resampling.NEAREST)
    img.alpha_composite(zoomed, (1, 1))
    return img

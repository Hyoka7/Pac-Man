"""Cached pixel sprites shared by character and menu rendering."""

from functools import cache
from math import ceil, hypot, radians, tan

from PIL import Image

from pacman.types import RGBAColor, RGBColor


@cache
def player_image(
    radius: float,
    direction: str,
    mouth_step: int,
) -> Image.Image:
    """Return the player sprite with an open mouth.

    Args:
        radius: Player radius in pixels.
        direction: Facing direction ("N", "E", "S" or "W").
        mouth_step: Mouth opening from 0 (closed) to 10 (45 degrees).

    Returns:
        A 16x16 pixel-art image scaled to the player's diameter.
    """
    side = ceil(radius * 2)
    palette = Image.new(
        "RGBA",
        (16, 16),
        (0, 0, 0, 0),
    )

    mouth_angle_half = 45 * mouth_step / 10
    mouth_slope = tan(radians(mouth_angle_half))

    def _is_in_mouth(dx: float, dy: float) -> bool:
        """Return whether a point relative to the center is inside the mouth.

        Args:
            dx: Horizontal offset from the sprite center.
            dy: Vertical offset from the sprite center.

        Returns:
            True when the point lies in the mouth wedge.
        """
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
    """Return a ghost sprite with eyes looking in a direction.

    Args:
        radius: Ghost radius in pixels.
        color: Body color.
        direction: Direction the pupils look toward.

    Returns:
        A 16x16 pixel-art image scaled to the ghost's diameter.
    """
    side = ceil(radius * 2)
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
        color: RGBAColor,
    ) -> None:
        """Fill an inclusive rectangle of the sprite with one color.

        Args:
            start_x: Left column, inclusive.
            start_y: Top row, inclusive.
            end_x: Right column, inclusive.
            end_y: Bottom row, inclusive.
            img: Sprite image to modify.
            color: RGBA color.
        """
        for y in range(start_y, end_y + 1):
            for x in range(start_x, end_x + 1):
                img.putpixel((x, y), color)

    eye_size = 4
    eye_top_y = 5
    left_eye_x = 3
    right_eye_x = 9
    pupil_size = 2
    pupil_right_x = eye_size - pupil_size
    pupil_bottom_y = eye_size - pupil_size
    pupil_center_x = pupil_right_x // 2
    pupil_center_y = pupil_bottom_y // 2
    pupil_offsets = {
        "E": (pupil_right_x, pupil_center_y),
        "W": (0, pupil_center_y),
        "N": (pupil_center_x, 0),
        "S": (pupil_center_x, pupil_bottom_y),
    }
    pupil_offset_x, pupil_offset_y = pupil_offsets[direction]
    for eye_left in (left_eye_x, right_eye_x):
        range_putpixel(
            eye_left,
            eye_top_y,
            eye_left + eye_size - 1,
            eye_top_y + eye_size - 1,
            palette,
            (255, 255, 255, 255),
        )
        pupil_left = eye_left + pupil_offset_x
        pupil_top = eye_top_y + pupil_offset_y
        range_putpixel(
            pupil_left,
            pupil_top,
            pupil_left + pupil_size - 1,
            pupil_top + pupil_size - 1,
            palette,
            (0, 0, 0, 255),
        )

    return palette.resize((side, side), resample=Image.Resampling.NEAREST)

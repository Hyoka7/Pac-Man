"""Pixel sprites retain hard edges, proportions and four ghost feet."""

import unittest

from PIL import Image

from visualize.ghost import ghost_image
from visualize.player import player_image


class PixelSpriteTests(unittest.TestCase):
    def test_sprites_have_only_opaque_or_transparent_pixels(self) -> None:
        for radius in (8, 12.5, 24):
            images = [ghost_image(radius, (0, 0, 128))]
            images.extend(player_image(radius, direction, step)
                          for direction in "EWNS" for step in (0, 5, 10))
            for image in images:
                with self.subTest(radius=radius, size=image.size):
                    self.assertEqual(set(image.getchannel("A").get_flattened_data()),
                                     {0, 255})
                    self.assertIsNone(image.crop((0, 0, image.width, 1)).getbbox())

    def test_integer_scale_repeats_each_source_pixel(self) -> None:
        for make in (lambda r: player_image(r, "E", 10),
                     lambda r: ghost_image(r, (255, 0, 0))):
            small = make(8).crop((1, 1, 17, 17))
            large = make(24)
            self.assertEqual(large.size, (50, 50))
            expected = small.resize((48, 48), Image.Resampling.NEAREST)
            self.assertEqual(large.crop((1, 1, 49, 49)).tobytes(),
                             expected.tobytes())

    def test_ghost_is_symmetric_with_four_feet(self) -> None:
        image = ghost_image(8, (255, 0, 0))
        alpha = image.getchannel("A")
        self.assertEqual(alpha.tobytes(),
                         alpha.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes())
        row = [image.getpixel((x, 16))[3] > 0 for x in range(image.width)]
        feet = sum(filled and (x == 0 or not row[x - 1])
                   for x, filled in enumerate(row))
        self.assertEqual(feet, 4)

    def test_ghost_eyes_have_white_backgrounds_and_black_pupils(self) -> None:
        image = ghost_image(8, (255, 0, 0))
        for left in (3, 9):
            for y in range(5, 9):
                for x in range(left, left + 4):
                    expected = ((0, 0, 0, 255) if x >= left + 2 and y >= 7
                                else (255, 255, 255, 255))
                    self.assertEqual(image.getpixel((x + 1, y + 1)), expected)

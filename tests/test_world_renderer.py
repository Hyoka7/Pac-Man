"""Pacgum rendering preserves sizes, colors and clipping in both image formats."""

import unittest

from pacman.game.pacgums import Pacgums
from pacman.visualize.visualizerutils import VisualizerUtils
from pacman.visualize.world_renderer import WorldRenderer


class PacgumRenderingTests(unittest.TestCase):
    def test_normal_and_super_gums_keep_exact_pixel_footprints(self) -> None:
        normal = {(x, y) for x in (9, 10) for y in (9, 10)}
        large = {(x, y) for y in (7, 12) for x in range(28, 32)}
        large |= {(x, y) for y in range(8, 12) for x in range(27, 33)}
        for img_format in (0, 1):
            with self.subTest(img_format=img_format):
                canvas = VisualizerUtils(40, 20, 20, 0,
                    memoryview(bytearray(160 * 20)), 160, img_format, 0, 0)
                canvas.clear_image()
                gums = Pacgums(1, 2)
                gums.remain_gums = {(10.0, 10.0)}
                gums.super_gums = {(30.0, 10.0)}
                WorldRenderer().draw_pacgums(gums, canvas)
                white = bytes((255, 255, 255, 255))
                yellow = bytes((0, 255, 255, 255) if img_format == 0 else (255, 255, 255, 0))
                background = bytes((0, 0, 0, 255) if img_format == 0 else (255, 0, 0, 0))
                for y in range(20):
                    for x in range(40):
                        offset = y * 160 + x * 4
                        expected = white if (x, y) in normal else yellow if (x, y) in large else background
                        self.assertEqual(bytes(canvas.img_data[offset:offset + 4]), expected)

    def test_clipped_supergum_preserves_scanline_padding(self) -> None:
        expected = {(x, y) for y in (0, 1) for x in range(3)} | {(0, 2), (1, 2)}
        canvas = VisualizerUtils(8, 6, 20, 0,
            memoryview(bytearray([37] * (40 * 6))), 40, 0, 0, 0)
        canvas.clear_image()
        gums = Pacgums(1, 1)
        gums.super_gums = {(0.0, 0.0)}
        WorldRenderer().draw_pacgums(gums, canvas)
        for y in range(6):
            self.assertEqual(bytes(canvas.img_data[y * 40 + 32:(y + 1) * 40]), bytes([37] * 8))
            for x in range(8):
                offset = y * 40 + x * 4
                color = bytes((0, 255, 255, 255) if (x, y) in expected else (0, 0, 0, 255))
                self.assertEqual(bytes(canvas.img_data[offset:offset + 4]), color)

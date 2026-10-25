"""Pillow text blends into the image before the single native presentation."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image, ImageFont

from visualize.gui import GUI, GUIStateEnum
from visualize.maze_visualizer import MazeVisualizer
from visualize.visualizerutils import VisualizerUtils
from visualize.image_renderer import ImageRenderer

text_renderer = ImageRenderer()


def canvas(width=800, height=600, img_format=0):
    return VisualizerUtils(width, height, 20, 0,
        memoryview(bytearray(width * height * 4)), width * 4, img_format, 0, 0)


class TextRenderingTests(unittest.TestCase):
    def test_lowercase_names_digits_and_capitals_share_one_baseline(self):
        for size in (20, 40):
            font = ImageFont.load_default(size=size)
            ascent, descent = font.getmetrics()
            images = [text_renderer._text_image(text, (255, 255, 255), size)
                      for text in ('moae', 'ABC', '1234567', 'kyonaha')]
            self.assertEqual([img.height for img in images], [ascent+descent]*4)
            bottoms = [img.getbbox()[3] for img in images]
            self.assertEqual(bottoms[0], bottoms[1])
            self.assertEqual(bottoms[1], bottoms[2])
            self.assertGreater(bottoms[3], bottoms[0])

    def test_text_preserves_background_and_blends_yellow_edges_in_both_formats(self):
        for fmt in (0, 1):
            target = canvas(200, 80, fmt)
            target.fill_rect(0, 0, 200, 80, (16, 25, 48))
            text_renderer.draw_text(target, 10, 10, 'Pac-Man', (255, 216, 74), 32)
            colors = set()
            for y in range(80):
                for x in range(200):
                    data = target.img_data[y*target.line_size+x*4:][:4]
                    b, g, r, _ = data if fmt == 0 else (data[3], data[2], data[1], data[0])
                    colors.add((r, g, b))
            self.assertIn((16, 25, 48), colors)
            self.assertIn((255, 216, 74), colors)
            self.assertTrue(any(16 < r < 255 for r, _, _ in colors))

    def test_long_text_is_not_cut_at_old_400_pixel_width_and_clips_offscreen(self):
        target = canvas(1000, 80)
        text_renderer.draw_text(target, 0, 0, 'W' * 30, size=32)
        self.assertTrue(any(
            any(target.img_data[y*target.line_size+500*4:y*target.line_size+900*4])
            for y in range(80)
        ))
        before = len(target.img_data)
        text_renderer.draw_text(target, -20, -5, 'edge', size=32)
        self.assertEqual(len(target.img_data), before)

    def test_image_composition_blends_rgba_and_preserves_row_padding(self):
        overlay = Image.new('RGBA', (2, 2))
        overlay.putpixel((0, 0), (255, 0, 0, 255))
        overlay.putpixel((1, 0), (255, 255, 0, 0))
        overlay.putpixel((0, 1), (216, 125, 48, 128))
        overlay.putpixel((1, 1), (0, 0, 255, 255))
        for fmt in (0, 1):
            with self.subTest(fmt=fmt):
                data = bytearray([37] * 24)
                target = VisualizerUtils(2, 2, 1, 0, memoryview(data), 12, fmt, 0, 0)
                target.fill_rect(0, 0, 2, 2, (16, 25, 48))
                text_renderer.draw_image(target, 0, 0, overlay)
                expected = [(255, 0, 0), (16, 25, 48), (116, 75, 48), (0, 0, 255)]
                for index, (r, g, b) in enumerate(expected):
                    start = (index // 2) * 12 + (index % 2) * 4
                    encoded = bytes([b, g, r, 255] if fmt == 0 else [255, r, g, b])
                    self.assertEqual(data[start:start+4], encoded)
                self.assertEqual(data[8:12], bytes([37]*4))
                self.assertEqual(data[20:24], bytes([37]*4))

    def test_image_clipping_keeps_the_correct_source_pixels(self):
        overlay = Image.new('RGBA', (2, 2), (255, 0, 0, 255))
        overlay.putpixel((1, 1), (0, 0, 255, 255))
        target = canvas(2, 2)
        target.clear_image()
        text_renderer.draw_image(target, -1, -1, overlay)
        self.assertEqual(bytes(target.img_data[:4]), bytes([255, 0, 0, 255]))
        self.assertEqual(bytes(target.img_data[4:8]), bytes([0, 0, 0, 255]))
        before = bytes(target.img_data)
        for x, y in ((5, 5), (-5, -5), (2, 0), (0, 2)):
            text_renderer.draw_image(target, x, y, overlay)
            self.assertEqual(bytes(target.img_data), before)

    def test_every_screen_presents_completed_text_once_without_native_strings_or_sync(self):
        v = MazeVisualizer.__new__(MazeVisualizer)
        v.closed = False
        v.width, v.height = 800, 600
        v.canvas = canvas()
        v.gui = GUI()
        v.gui.update_layout(v.width, v.height)
        v.p = v.win = v.img = 1
        v.cm = 0
        v.cmodes = [((0, 0, 0), (0, 0, 0), (0, 0, 0))]
        v.maze, v.pacgums = Mock(), Mock()
        v.ghosts = []
        v.player = SimpleNamespace(is_invincible=True, invincible_remain=3,
            draw=Mock(), score=123, lives=3)
        v.level, v.remaining_time = 1, 30
        v.cheat_enabled = True
        v.player_name = 'Player'
        v.home_focusing = v.ranking_page = 0
        v.score_manager = SimpleNamespace(scores=SimpleNamespace(scores=[]))
        for state in GUIStateEnum:
            with self.subTest(state=state):
                v.state = state
                v.m = Mock()
                presented = []
                v.m.mlx_put_image_to_window.side_effect = lambda *args: presented.append(bytes(v.canvas.img_data))
                v._draw()
                self.assertEqual(len(presented), 1)
                self.assertEqual(presented[0], bytes(v.canvas.img_data))
                self.assertTrue(any(presented[0]))
                v.m.mlx_string_put.assert_not_called()
                v.m.mlx_sync.assert_not_called()

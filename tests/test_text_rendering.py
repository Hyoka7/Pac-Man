"""Pillow text blends into the image before the single native presentation."""

from typing import Any, cast
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image, ImageFont

from visualize.gui import GUI, GUIStateEnum
from visualize.maze_visualizer import MazeVisualizer
from visualize.visualizerutils import VisualizerUtils
from visualize.image_renderer import ImageRenderer

text_renderer = ImageRenderer()


def canvas(width: int = 800, height: int = 600, img_format: int = 0) -> VisualizerUtils:
    return VisualizerUtils(width, height, 20, 0,
        memoryview(bytearray(width * height * 4)), width * 4, img_format, 0, 0)


class TextRenderingTests(unittest.TestCase):
    def test_numeric_text_reuses_image_but_redraws_on_a_cleared_canvas(self) -> None:
        renderer = ImageRenderer()
        target = canvas()
        label = 'Lv:1 Score:120 Life:3 Time:89.9 CHEAT ON'
        renderer.draw_numeric_text(target, 10, 10, label)
        cached = renderer.numeric_cache['hud'][3]
        pixels = bytes(target.img_data)
        target.img_data[:] = bytes(len(target.img_data))
        with patch.object(renderer, '_split', wraps=renderer._split) as split:
            renderer.draw_numeric_text(target, 10, 10, label)
        split.assert_not_called()
        self.assertIs(renderer.numeric_cache['hud'][3], cached)
        self.assertEqual(bytes(target.img_data), pixels)
        self.assertTrue(any(pixels))

    def test_numeric_text_rebuilds_when_text_color_or_size_changes(self) -> None:
        renderer = ImageRenderer()
        target = canvas()
        for text, color, size in (
            ('Time:89.9', (255, 255, 255), 20),
            ('Time:89.8', (255, 255, 255), 20),
            ('Time:89.8', (255, 216, 74), 20),
            ('Time:89.8', (255, 216, 74), 40),
        ):
            previous = renderer.numeric_cache.get('hud')
            renderer.draw_numeric_text(target, 10, 10, text, color, size)
            self.assertIn('hud', renderer.numeric_cache)
            self.assertIsNot(
                renderer.numeric_cache['hud'][3],
                previous[3] if previous is not None else None,
            )

    def test_numeric_slots_reuse_independently_and_replace_only_changed_slot(self) -> None:
        renderer = ImageRenderer()
        target = canvas()
        renderer.draw_numeric_text(target, 0, 0, 'Time:89.9', slot='hud')
        renderer.draw_numeric_text(target, 0, 40, 'Invincible 4.9', slot='invincible')
        hud = renderer.numeric_cache['hud'][3]
        invincible = renderer.numeric_cache['invincible'][3]
        with patch.object(renderer, '_split', wraps=renderer._split) as split:
            renderer.draw_numeric_text(target, 0, 0, 'Time:89.9', slot='hud')
            renderer.draw_numeric_text(target, 0, 40, 'Invincible 4.9', slot='invincible')
        split.assert_not_called()
        renderer.draw_numeric_text(target, 0, 0, 'Time:89.8', slot='hud')
        self.assertIsNot(renderer.numeric_cache['hud'][3], hud)
        self.assertIs(renderer.numeric_cache['invincible'][3], invincible)
        self.assertEqual(len(renderer.numeric_cache), 2)

    def test_invincible_timer_is_centered_and_reuses_its_own_slot(self) -> None:
        gui = GUI()
        gui.update_layout(800, 600)
        renderer = gui.text_renderer
        target = canvas()
        gui.draw_stats(target, 20, 15, 1, 0, 3, 89.9, False)
        hud = renderer.numeric_cache['hud'][3]
        with patch.object(renderer, 'text_size', side_effect=AssertionError(
            'Timer measurement must not cache a whole changing string'
        )):
            gui.invinsible_time(target, 800, gui.bar_y, 4.9)
        timer = renderer.numeric_cache['invincible'][3]
        with patch.object(renderer, 'draw_image') as draw:
            gui.invinsible_time(target, 800, gui.bar_y, 4.9)
        draw.assert_called_once_with(
            target, (800 - timer.width) // 2,
            gui.bar_y - gui.text_height - gui.text_gap, timer,
        )
        self.assertIs(renderer.numeric_cache['hud'][3], hud)
        self.assertIs(renderer.numeric_cache['invincible'][3], timer)

    def test_numeric_image_is_shared_between_measurement_and_drawing(self) -> None:
        renderer = ImageRenderer()
        for text in ('', 'Invincible 4.9', 'Lv:1 Score:120 Time:89.9'):
            with self.subTest(text=text):
                image = renderer.numeric_text_image(text, size=20)
                if not text:
                    self.assertEqual(image.width, 0)
                    continue
                with patch.object(renderer, '_split', wraps=renderer._split) as split:
                    renderer.draw_numeric_text(canvas(), 0, 0, text)
                split.assert_not_called()
                self.assertIs(image, renderer.numeric_cache['hud'][3])

    def test_centered_timer_splits_once_on_change_and_never_on_reuse(self) -> None:
        gui = GUI()
        gui.update_layout(800, 600)
        renderer = gui.text_renderer
        with patch.object(renderer, '_split', wraps=renderer._split) as split:
            gui.invinsible_time(canvas(), 800, gui.bar_y, 4.9)
            split.assert_called_once_with('Invincible 4.9')
            split.reset_mock()
            gui.invinsible_time(canvas(), 800, gui.bar_y, 4.9)
            split.assert_not_called()
            gui.invinsible_time(canvas(), 800, gui.bar_y, 4.8)
            split.assert_called_once_with('Invincible 4.8')

    def test_lowercase_names_digits_and_capitals_share_one_baseline(self) -> None:
        for size in (20, 40):
            font = cast(ImageFont.FreeTypeFont, ImageFont.load_default(size=size))
            ascent, descent = font.getmetrics()
            images = [text_renderer._text_image(text, (255, 255, 255), size)
                      for text in ('moae', 'ABC', '1234567', 'kyonaha')]
            self.assertEqual([img.height for img in images], [ascent+descent]*4)
            bottoms: list[int] = []
            for img in images:
                bounds = img.getbbox()
                assert bounds is not None
                bottoms.append(bounds[3])
            self.assertEqual(bottoms[0], bottoms[1])
            self.assertEqual(bottoms[1], bottoms[2])
            self.assertGreater(bottoms[3], bottoms[0])

    def test_text_preserves_background_and_blends_yellow_edges_in_both_formats(self) -> None:
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

    def test_long_text_is_not_cut_at_old_400_pixel_width_and_clips_offscreen(self) -> None:
        target = canvas(1000, 80)
        text_renderer.draw_text(target, 0, 0, 'W' * 30, size=32)
        self.assertTrue(any(
            any(target.img_data[y*target.line_size+500*4:y*target.line_size+900*4])
            for y in range(80)
        ))
        before = len(target.img_data)
        text_renderer.draw_text(target, -20, -5, 'edge', size=32)
        self.assertEqual(len(target.img_data), before)

    def test_image_composition_blends_rgba_and_preserves_row_padding(self) -> None:
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

    def test_image_clipping_keeps_the_correct_source_pixels(self) -> None:
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

    def test_every_screen_presents_completed_text_once_without_native_strings_or_sync(self) -> None:
        v = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
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
        v.home_focusing = 0
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

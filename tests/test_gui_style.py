"""The GUI palette and panels are rendered into the real image buffer."""

import unittest
from unittest.mock import Mock, patch
from PIL import ImageFont

from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import ScoreEntry
from visualize.visualizerutils import VisualizerUtils


def make_canvas(width: int, height: int, img_format: int = 0) -> VisualizerUtils:
    return VisualizerUtils(
        width, height, 20, 20,
        memoryview(bytearray(width * height * 4)), width * 4, img_format, 0, 0,
    )


def pixel(canvas: VisualizerUtils, x: int, y: int) -> tuple[int, int, int]:
    index = y * canvas.line_size + x * 4
    data = canvas.img_data[index:index+4]
    if canvas.img_format == 0:
        blue, green, red, _ = data
    else:
        _, red, green, blue = data
    return red, green, blue


class RectangleTests(unittest.TestCase):
    def test_clear_can_make_visible_pixels_transparent_without_touching_padding(self):
        for img_format in (0, 1):
            with self.subTest(img_format=img_format):
                image = bytearray([37] * 24 * 4)
                canvas = VisualizerUtils(
                    5, 4, 20, 0, memoryview(image), 24, img_format, 0, 0,
                )
                canvas.clear_image(transparent=True)
                for y in range(4):
                    self.assertEqual(image[y*24:y*24+20], bytes(20))
                    self.assertEqual(image[y*24+20:y*24+24], bytes([37] * 4))
                canvas.clear_image()
                for y in range(4):
                    self.assertEqual(pixel(canvas, 0, y), (0, 0, 0))
                    alpha = image[y*24+(3 if img_format == 0 else 0)]
                    self.assertEqual(alpha, 255)

    def test_rectangle_clips_edges_and_preserves_row_padding_in_both_formats(self):
        cases = [
            ((-2, -1, 4, 3), {(0, 0), (1, 0), (0, 1), (1, 1)}),
            ((3, 2, 9, 9), {(3, 2), (4, 2), (3, 3), (4, 3)}),
            ((-10, 1, 2, 2), set()),
            ((0, 0, 0, 3), set()),
            ((0, 0, -2, 3), set()),
        ]
        for img_format in (0, 1):
            for rectangle, expected in cases:
                with self.subTest(img_format=img_format, rectangle=rectangle):
                    image = bytearray([7] * 24 * 4)
                    canvas = VisualizerUtils(
                        5, 4, 20, 0, memoryview(image), 24, img_format, 0, 0,
                    )
                    self.assertTrue(callable(getattr(canvas, "fill_rect", None)))
                    canvas.fill_rect(*rectangle, (16, 32, 48))
                    encoded = (bytes([48, 32, 16, 255]) if img_format == 0
                               else bytes([255, 16, 32, 48]))
                    for y in range(4):
                        for x in range(5):
                            actual = image[y*24+x*4:y*24+x*4+4]
                            self.assertEqual(actual, encoded if (x, y) in expected
                                             else bytes([7] * 4))
                        self.assertEqual(image[y*24+20:y*24+24], bytes([7] * 4))


class GUIStyleTests(unittest.TestCase):
    def setUp(self):
        patcher = patch('visualize.text.TextRenderer.draw_text')
        self.draw_text = patcher.start()
        self.addCleanup(patcher.stop)

    def test_home_highlights_only_selected_item_and_title(self):
        for focusing, selected in enumerate(('Start', 'Instruction', 'Ranking')):
            self.draw_text.reset_mock()
            GUI().home(Mock(), 800, 600, [], focusing)
            calls = [c.args for c in self.draw_text.call_args_list]
            for _, _, _, text, color, _ in calls:
                self.assertEqual(color, (255, 216, 74) if text in
                    ('PAC-MAN', '> '+selected) else (255, 255, 255))

    def test_backdrop_covers_static_screen_and_centers_bordered_panel(self):
        gui = GUI()
        self.assertTrue(callable(getattr(gui, "draw_backdrop", None)))
        canvas = make_canvas(800, 600)
        gui.draw_backdrop(canvas, GUIStateEnum.Home)
        self.assertEqual(pixel(canvas, 0, 0), (8, 13, 28))
        self.assertEqual(pixel(canvas, 90, 90), (73, 194, 221))
        self.assertEqual(pixel(canvas, 709, 509), (73, 194, 221))
        self.assertEqual(pixel(canvas, 400, 300), (16, 25, 48))
        self.assertEqual(pixel(canvas, 710, 510), (8, 13, 28))

    def test_static_text_blocks_fit_inside_panels(self):
        gui = GUI()
        self.assertTrue(callable(getattr(gui, "draw_backdrop", None)))
        scores = [ScoreEntry(name="LONGEST_NAME", score=1234567)] * 10
        screens = [
            (GUIStateEnum.Home, gui.home, (scores, 0)),
            (GUIStateEnum.Ranking, gui.ranking, (scores,)),
            (GUIStateEnum.Instruction, gui.instruction, ()),
            (GUIStateEnum.GameOver, gui.gameover, (1234567, "LONGEST_NAME")),
            (GUIStateEnum.All_Clear, gui.all_clear, (1234567, "LONGEST_NAME")),
            (GUIStateEnum.Stage_Clear, gui.stage_clear, ()),
        ]
        for state, renderer, args in screens:
            with self.subTest(state=state):
                canvas, mlx = make_canvas(800, 600), Mock()
                gui.draw_backdrop(canvas, state)
                self.draw_text.reset_mock()
                renderer(canvas, 800, 600, *args)
                for call in self.draw_text.call_args_list:
                    _, x, y, text, _, size = call.args
                    left, top, right, bottom = ImageFont.load_default(size=size).getbbox(text)
                    self.assertEqual(pixel(canvas, x, y), (16, 25, 48))
                    self.assertEqual(pixel(canvas, x+right-left-1, y+bottom-top-1),
                                     (16, 25, 48))

    def test_backdrop_leaves_live_maze_and_pause_buffer_unchanged(self):
        gui = GUI()
        self.assertTrue(callable(getattr(gui, "draw_backdrop", None)))
        canvas = make_canvas(8, 6)
        canvas.img_data[:] = bytes([37]) * len(canvas.img_data)
        for state in (GUIStateEnum.Playing, GUIStateEnum.Pause):
            gui.draw_backdrop(canvas, state)
            self.assertEqual(bytes(canvas.img_data), bytes([37]) * 8 * 6 * 4)

    def test_small_backdrop_and_partial_pause_panel_clip_to_the_image(self):
        gui = GUI()
        self.assertTrue(callable(getattr(gui, "draw_backdrop", None)))
        canvas = make_canvas(40, 30)
        gui.draw_backdrop(canvas, GUIStateEnum.Ranking)
        self.assertEqual(pixel(canvas, 0, 0), (8, 13, 28))
        canvas.clear_image()
        gui.background(canvas, -5, -5, 20, 20)
        self.assertEqual(pixel(canvas, 0, 0), (16, 25, 48))
        self.assertEqual(pixel(canvas, 14, 14), (73, 194, 221))
        self.assertEqual(pixel(canvas, 15, 15), (0, 0, 0))

    def test_power_bar_shrinks_toward_center_and_clamps_remaining_time(self):
        gui = GUI()
        canvas = make_canvas(40, 10)
        gui.draw_invincible_bar(canvas, 10, 3, 20, 4, 2.5, 5.0)
        self.assertEqual(pixel(canvas, 10, 3), (31, 44, 67))
        self.assertEqual(pixel(canvas, 14, 3), (31, 44, 67))
        self.assertEqual(pixel(canvas, 15, 3), (255, 216, 74))
        self.assertEqual(pixel(canvas, 24, 6), (255, 216, 74))
        self.assertEqual(pixel(canvas, 25, 6), (31, 44, 67))
        gui.draw_invincible_bar(canvas, 10, 3, 20, 4, 10.0, 5.0)
        self.assertEqual(pixel(canvas, 9, 3), (0, 0, 0))
        self.assertEqual(pixel(canvas, 30, 3), (0, 0, 0))
        gui.draw_invincible_bar(canvas, 10, 3, 20, 4, -1.0, 5.0)
        self.assertEqual(pixel(canvas, 20, 3), (31, 44, 67))


if __name__ == "__main__":
    unittest.main()

"""The GUI palette and panels are rendered into the real image buffer."""

import unittest
from unittest.mock import Mock

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
    def test_long_static_screen_waits_for_each_text_row(self):
        mlx = Mock()
        scores = [ScoreEntry(name='ABCDEFGHIJKL', score=1234567)] * 10
        GUI().ranking(mlx, 1, 2, 800, 600, scores)
        calls = mlx.method_calls
        self.assertTrue(calls)
        for index in range(0, len(calls), 2):
            self.assertEqual(calls[index][0], 'mlx_string_put')
            self.assertEqual(calls[index+1][0], 'mlx_sync')
            self.assertEqual(calls[index+1].args, (1, 3, 2))

    def test_short_name_screen_keeps_text_in_one_batch(self):
        mlx = Mock()
        GUI().gameover(mlx, 1, 2, 800, 600, 9999999999, 'ABCDEFGHIJKL')
        self.assertEqual(mlx.mlx_string_put.call_count, 4)
        mlx.mlx_sync.assert_not_called()

    def test_home_menu_partial_render_matches_full_layout_and_fits_native_batch(self):
        gui = GUI()
        self.assertTrue(callable(getattr(gui, "home_menu", None)))
        options = ("Game Start", "Instruction", "Highscore Ranking")
        for count in (0, 2, 5, 8):
            scores = [ScoreEntry(name=f"p{i}", score=100-i) for i in range(count)]
            positions = None
            for focusing in range(3):
                with self.subTest(scores=count, focusing=focusing):
                    full, partial = Mock(), Mock()
                    gui.home(full, 1, 2, 800, 600, scores, focusing)
                    gui.home_menu(partial, 1, 2, 800, 600, scores, focusing)
                    expected = [
                        call.args for call in full.mlx_string_put.call_args_list
                        if any(option in call.args[-1] for option in options)
                    ]
                    actual = [
                        call.args for call in partial.mlx_string_put.call_args_list
                    ]
                    self.assertEqual(actual, expected)
                    self.assertEqual(len(actual), 3)
                    self.assertLess(1+sum(len(call[-1]) for call in actual), 64)
                    current_positions = [(call[2], call[3]) for call in actual]
                    if positions is None:
                        positions = current_positions
                    else:
                        self.assertEqual(current_positions, positions)
                    for index, call in enumerate(actual):
                        prefix = "> " if index == focusing else "  "
                        self.assertEqual(call[-1][:2], prefix)

    def test_home_menu_background_only_erases_menu_rows_inside_panel(self):
        gui = GUI()
        self.assertTrue(callable(getattr(gui, "draw_home_menu_background", None)))
        options = ("Game Start", "Instruction", "Highscore Ranking")
        for count in (0, 2, 5, 8):
            with self.subTest(scores=count):
                scores = [ScoreEntry(name=f"p{i}", score=100-i) for i in range(count)]
                canvas, mlx = make_canvas(800, 600), Mock()
                canvas.fill_rect(0, 0, 800, 600, (12, 34, 56))
                gui.draw_home_menu_background(canvas, scores)
                gui.home(mlx, 1, 2, 800, 600, scores, 0)
                for call in mlx.mlx_string_put.call_args_list:
                    _, _, x, y, _, text = call.args
                    if any(option in text for option in options):
                        self.assertEqual(pixel(canvas, x, y), (16, 25, 48))
                        self.assertEqual(pixel(canvas, x+len(text)*10-1, y+19),
                                         (16, 25, 48))
                    else:
                        self.assertEqual(pixel(canvas, x, y), (12, 34, 56))
                self.assertEqual(pixel(canvas, 90, 90), (12, 34, 56))
                self.assertEqual(pixel(canvas, 709, 509), (12, 34, 56))

    def test_home_highlights_only_selected_item_and_title(self):
        options = ("Game Start", "Instruction", "Highscore Ranking")
        gui = GUI()
        for focusing, selected in enumerate(options):
            with self.subTest(focusing=focusing):
                mlx = Mock()
                gui.home(mlx, 1, 2, 800, 600, [ScoreEntry(name="A", score=1)],
                         focusing)
                calls = [call.args for call in mlx.mlx_string_put.call_args_list]
                marked = [call for call in calls if call[-1].startswith("> ")]
                self.assertEqual(len(marked), 1)
                self.assertIn(selected, marked[0][-1])
                yellow = marked[0][-2]
                self.assertNotEqual(yellow, 0xFFFFFFFF)
                # The installed MLX 2 text API interprets packed colors as ABGR.
                self.assertGreater(yellow & 255, 200)
                self.assertGreater((yellow >> 8) & 255, 150)
                self.assertLess((yellow >> 16) & 255, 100)
                for call in calls:
                    if call[-1] == "PAC-MAN":
                        self.assertEqual(call[-2], yellow)
                    elif not call[-1].startswith("> "):
                        self.assertEqual(call[-2], 0xFFFFFFFF)

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
                renderer(mlx, 1, 2, 800, 600, *args)
                for call in mlx.mlx_string_put.call_args_list:
                    _, _, x, y, _, text = call.args
                    self.assertEqual(pixel(canvas, x, y), (16, 25, 48))
                    self.assertEqual(pixel(canvas, x+len(text)*10-1, y+19),
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

"""Decorative home sprites are centered, separated and outside the menu."""

import unittest
from unittest.mock import patch

from visualize.gui import GUI
from visualize.visualizerutils import VisualizerUtils


def canvas(width: int, height: int) -> VisualizerUtils:
    return VisualizerUtils(width, height, 20, 0,
        memoryview(bytearray(width * height * 4)), width * 4, 0, 0, 0)


class HomeCharactersTests(unittest.TestCase):
    def test_five_sprites_have_gaps_and_share_a_centered_row(self) -> None:
        gui = GUI()
        gui.update_layout(800, 600)
        target = canvas(800, 600)
        with patch.object(gui.text_renderer, 'draw_image',
                          wraps=gui.text_renderer.draw_image) as draw:
            gui._draw_home_characters(target, 800, 220)
        calls = [call.args for call in draw.call_args_list]
        self.assertEqual(len(calls), 5)
        for _, _, y, _ in calls:
            self.assertEqual(y, 220)
        for previous, current in zip(calls, calls[1:]):
            self.assertEqual(current[1] - previous[1] - previous[3].width, gui.text_gap)
        left = calls[0][1]
        right = calls[-1][1] + calls[-1][3].width
        self.assertLessEqual(abs(left - (800 - right)), 1)
        self.assertTrue(any(target.img_data))

    def test_home_calls_sprite_row_between_title_and_start(self) -> None:
        for width, height in ((480, 320), (800, 600), (2460, 1340), (720, 1280)):
            with self.subTest(size=(width, height)):
                gui = GUI()
                gui.update_layout(width, height)
                target = canvas(width, height)
                with patch.object(gui, '_draw_home_characters',
                                  wraps=gui._draw_home_characters) as characters, patch.object(
                    gui.text_renderer, 'draw_image', wraps=gui.text_renderer.draw_image,
                ) as images, patch.object(
                    gui.text_renderer, 'draw_text', wraps=gui.text_renderer.draw_text,
                ) as texts:
                    gui.home(target, width, height, [], 0)
                characters.assert_called_once()
                _, _, sprite_y = characters.call_args.args
                title = images.call_args_list[0].args
                bounds = title[3].getbbox()
                assert bounds is not None
                self.assertLessEqual(title[2] + bounds[3], sprite_y)
                start = next(call.args for call in texts.call_args_list if call.args[3] == 'Start')
                self.assertLessEqual(sprite_y + int(gui.font_size) + 2, start[2])
                self.assertLessEqual(abs(title[1] - (width - title[1] - title[3].width)), 1)

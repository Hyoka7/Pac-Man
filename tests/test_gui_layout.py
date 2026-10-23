"""Pillow metrics keep text blocks and pause labels inside their panels."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PIL import ImageFont

from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import ScoreEntry
from visualize.maze_visualizer import MazeVisualizer


def dimensions(text, size=20):
    left, top, right, bottom = ImageFont.load_default(size=size).getbbox(text)
    return right-left, bottom-top


class GUILayoutTests(unittest.TestCase):
    def setUp(self):
        self.gui = GUI()
        patcher = patch('visualize.text.TextRenderer.draw_text')
        self.draw_text = patcher.start()
        self.addCleanup(patcher.stop)

    def assert_centered_block(self, width, height):
        bounds = []
        for call in self.draw_text.call_args_list:
            _, x, y, text, _, size = call.args
            w, h = dimensions(text, size)
            self.assertLessEqual(abs(x - (width-x-w)), 1)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(y+h, height)
            bounds.append((y, y+h))
        self.assertTrue(bounds)
        top, bottom = min(b[0] for b in bounds), max(b[1] for b in bounds)
        self.assertLessEqual(abs(top-(height-bottom)), 1)

    def test_single_line_centers_actual_glyph_width(self):
        for width in (600, 801):
            for text in ('Home Demo', 'I', 'WWWiii'):
                self.draw_text.reset_mock()
                self.gui._put_string_center(Mock(), width, 123, text)
                _, x, y, drawn, color, size = self.draw_text.call_args.args
                w, _ = dimensions(text, size)
                self.assertLessEqual(abs(x-(width-x-w)), 1)
                self.assertEqual((y, drawn, color), (123, text, (255, 255, 255)))

    def test_static_screens_center_the_complete_block(self):
        scores = [ScoreEntry(name='LONGEST_NAME', score=1234567)] * 10
        screens = [
            (self.gui.home, (scores, 0)),
            (self.gui.ranking, ([],)), (self.gui.gameover, (1234567, 'LONGEST_NAME')),
            (self.gui.all_clear, (1234567, 'LONGEST_NAME')),
            (self.gui.stage_clear, ()), (self.gui.pause, ()), (self.gui.instruction, ()),
        ]
        for width, height in ((800, 600), (1001, 801)):
            for renderer, args in screens:
                with self.subTest(screen=renderer.__name__, size=(width, height)):
                    self.draw_text.reset_mock()
                    renderer(Mock(), width, height, *args)
                    self.assert_centered_block(width, height)

    def test_home_shows_only_menu_with_one_selected_item(self):
        scores = [ScoreEntry(name=f'player{i}', score=i) for i in range(8)]
        for focusing, selected in enumerate(('Start', 'Instruction', 'Ranking')):
            self.draw_text.reset_mock()
            self.gui.home(Mock(), 800, 600, scores, focusing)
            strings = [c.args[3] for c in self.draw_text.call_args_list]
            self.assertIn('PAC-MAN', strings)
            self.assertIn('Up/Down: Select  Enter: OK', strings)
            marked = [text for text in strings if text.startswith('> ')]
            self.assertEqual(marked, ['> '+selected])
            self.assertFalse(any('player' in text for text in strings))

    def test_power_time_is_centered_above_bar(self):
        self.gui.invinsible_time(Mock(), 801, 600, 3.25)
        _, x, y, text, _, size = self.draw_text.call_args.args
        w, _ = dimensions(text, size)
        self.assertEqual((text, y), ('Invincible 3.2', 530))
        self.assertLessEqual(abs(x-(801-x-w)), 1)

    def test_pause_background_contains_pause_labels(self):
        v = MazeVisualizer.__new__(MazeVisualizer)
        v.closed = False
        v.state = GUIStateEnum.Pause
        v.canvas, v.m = Mock(), Mock()
        v.gui = Mock(wraps=GUI())
        v.p = v.win = v.img = 1
        v.width, v.height = 800, 600
        v.cmodes = [((255, 255, 255), (255, 0, 0), (0, 0, 0))]
        v.cm = 0
        v.maze, v.pacgums = Mock(), Mock()
        v.ghosts = []
        v.player = SimpleNamespace(is_invincible=False, draw=Mock(), score=100, lives=3)
        v.level, v.remaining_time, v.cheat_enabled = 1, 30, False
        v._draw()
        _, x, y, width, height = v.gui.background.call_args.args
        calls = [c.args for c in self.draw_text.call_args_list
                 if c.args[3] in {'PAUSED', 'P: Resume', 'H: Back to home'}]
        self.assertEqual(len(calls), 3)
        for _, tx, ty, text, _, size in calls:
            w, h = dimensions(text, size)
            self.assertGreaterEqual(tx, x)
            self.assertLessEqual(tx+w, x+width)
            self.assertGreaterEqual(ty, y)
            self.assertLessEqual(ty+h, y+height)

    def test_ranking_columns_align_with_proportional_font(self):
        scores = [ScoreEntry(name='iii', score=8), ScoreEntry(name='WWW', score=1234567)]
        self.gui.ranking(Mock(), 800, 600, scores)
        positions = {c.args[3]: c.args[1] for c in self.draw_text.call_args_list}
        self.assertEqual(positions['iii'], positions['WWW'])
        left = min(positions['1.'], positions['2.'])
        right = positions['1234567'] + dimensions('1234567')[0]
        self.assertLessEqual(abs(left-(800-right)), 1)
        self.assertEqual(positions['8']+dimensions('8')[0],
                         positions['1234567']+dimensions('1234567')[0])

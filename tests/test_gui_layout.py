"""Pillow metrics keep text blocks and pause labels inside their panels."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PIL import ImageFont

from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import ScoreEntry
from visualize.maze_visualizer import MazeVisualizer


def dimensions(text, size=20):
    font = ImageFont.load_default(size=size)
    left, _, right, _ = font.getbbox(text)
    ascent, descent = font.getmetrics()
    return right-left, ascent+descent


class GUILayoutTests(unittest.TestCase):
    def setUp(self):
        self.gui = GUI()
        self.gui.update_layout(800, 600)
        patcher = patch('visualize.image_renderer.ImageRenderer.draw_text')
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
                    self.gui.update_layout(width, height)
                    renderer(Mock(), width, height, *args)
                    self.assert_centered_block(width, height)

    def test_scaled_screens_keep_long_text_inside_their_panels(self):
        scores = [ScoreEntry(name='WWWWWWWWWWWW', score=9999999999)] * 10
        screens = [
            (GUIStateEnum.Home, self.gui.home, (scores, 0)),
            (GUIStateEnum.Ranking, self.gui.ranking, (scores,)),
            (GUIStateEnum.Instruction, self.gui.instruction, ()),
            (GUIStateEnum.GameOver, self.gui.gameover, (9999999999, 'WWWWWWWWWWWW')),
            (GUIStateEnum.All_Clear, self.gui.all_clear, (9999999999, 'WWWWWWWWWWWW')),
            (GUIStateEnum.Stage_Clear, self.gui.stage_clear, ()),
            (GUIStateEnum.Pause, self.gui.pause, ()),
        ]
        for width, height in ((480, 320), (800, 600), (1280, 720),
                              (2460, 1340), (720, 1280), (4000, 2200)):
            self.gui.update_layout(width, height)
            for state, renderer, args in screens:
                with self.subTest(state=state, size=(width, height)):
                    canvas = Mock(width=width, height=height)
                    self.draw_text.reset_mock()
                    with patch.object(self.gui, 'background', wraps=self.gui.background) as background:
                        if state == GUIStateEnum.Pause:
                            self.gui.draw_pause_background(canvas)
                        else:
                            self.gui.draw_backdrop(canvas, state)
                    _, x, y, panel_width, panel_height = background.call_args.args
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(x+panel_width, width)
                    self.assertLessEqual(y+panel_height, height)
                    renderer(canvas, width, height, *args)
                    for call in self.draw_text.call_args_list:
                        _, tx, ty, text, _, size = call.args
                        tw, th = dimensions(text, size)
                        self.assertGreaterEqual(tx, x+self.gui.border_width)
                        self.assertGreaterEqual(ty, y+self.gui.border_width)
                        self.assertLessEqual(tx+tw, x+panel_width-self.gui.border_width)
                        self.assertLessEqual(ty+th, y+panel_height-self.gui.border_width)

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
        self.gui.invinsible_time(Mock(), 801, 560, 3.25)
        _, x, y, text, _, size = self.draw_text.call_args.args
        w, _ = dimensions(text, size)
        self.assertEqual((text, y), ('Invincible 3.2', 530))
        self.assertLessEqual(abs(x-(801-x-w)), 1)

    def test_pause_background_contains_pause_labels(self):
        v = MazeVisualizer.__new__(MazeVisualizer)
        v.closed = False
        v.state = GUIStateEnum.Pause
        v.canvas, v.m = Mock(width=1600, height=1200), Mock()
        v.gui = GUI()
        v.gui.update_layout(1600, 1200)
        v.gui.background = Mock(wraps=v.gui.background)
        v.p = v.win = v.img = 1
        v.width, v.height = 1600, 1200
        v.cmodes = [((255, 255, 255), (255, 0, 0), (0, 0, 0))]
        v.cm = 0
        v.maze, v.pacgums = Mock(), Mock()
        v.ghosts = []
        v.player = SimpleNamespace(is_invincible=False, draw=Mock(), score=100, lives=3)
        v.level, v.remaining_time, v.cheat_enabled = 1, 30, False
        v._draw()
        _, x, y, width, height = v.gui.background.call_args.args
        self.assertLessEqual(abs(x-(v.width-x-width)), 1)
        self.assertLessEqual(abs(y-(v.height-y-height)), 1)
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

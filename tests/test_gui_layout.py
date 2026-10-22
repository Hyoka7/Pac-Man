"""Text blocks stay centered and readable at different window sizes."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import ScoreEntry
from visualize.maze_visualizer import MazeVisualizer


class GUILayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gui = GUI()

    def text_calls(self, mlx: Mock) -> list[tuple]:
        return [call.args for call in mlx.mlx_string_put.call_args_list]

    def assert_centered_block(
        self, calls: list[tuple], width: int, height: int,
    ) -> None:
        self.assertTrue(calls)
        for call in calls:
            _, _, x, y, _, text = call
            with self.subTest(text=text):
                right_margin = width - x - len(text) * 10
                self.assertLessEqual(abs(x - right_margin), 1)
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(y + 20, height)
        top = min(call[3] for call in calls)
        bottom = max(call[3] for call in calls) + 20
        self.assertLessEqual(abs(top - (height - bottom)), 1)

    def test_single_line_uses_font_width_for_odd_and_even_windows(self) -> None:
        for width in (600, 801):
            for text in ("Home Demo", "I", "A much longer title"):
                with self.subTest(width=width, text=text):
                    mlx = Mock()
                    self.gui._put_string_center(mlx, 1, 2, width, 123, text)
                    _, _, x, y, color, drawn = self.text_calls(mlx)[0]
                    self.assertEqual((y, color, drawn), (123, 0xFFFFFFFF, text))
                    self.assertLessEqual(abs(x - (width-x-len(text)*10)), 1)

    def test_static_screens_center_the_complete_block(self) -> None:
        scores = [
            ScoreEntry(name="LONGEST_NAME", score=1234567),
            ScoreEntry(name="A", score=42),
        ]
        screens = [
            (self.gui.home, (scores,)),
            (self.gui.ranking, (scores * 5,)),
            (self.gui.ranking, ([],)),
            (self.gui.gameover, (1234567, "LONGEST_NAME")),
            (self.gui.all_clear, (1234567, "LONGEST_NAME")),
            (self.gui.stage_clear, ()),
            (self.gui.pause, ()),
            (self.gui.instruction, ()),
        ]
        for width, height in ((800, 600), (1001, 801)):
            for renderer, args in screens:
                with self.subTest(screen=renderer.__name__, size=(width, height)):
                    mlx = Mock()
                    renderer(mlx, 1, 2, width, height, *args)
                    self.assert_centered_block(self.text_calls(mlx), width, height)

    def test_home_preserves_top_five_and_operation_prompts(self) -> None:
        scores = [ScoreEntry(name=f"p{i}", score=100-i) for i in range(8)]
        mlx = Mock()
        self.gui.home(mlx, 1, 2, 800, 600, scores)
        strings = [call[-1] for call in self.text_calls(mlx)]
        self.assertIn("Home Demo", strings)
        self.assertIn("I: Instruction", strings)
        self.assertIn("H: Highscore Ranking", strings)
        self.assertIn("Enter: Game Start!", strings)
        for score in scores[:5]:
            self.assertTrue(any(score.name in text for text in strings))
        self.assertFalse(any("p5" in text for text in strings))

    def test_ranking_columns_align_for_different_name_and_score_lengths(self) -> None:
        scores = [ScoreEntry(name="LONGEST_NAME", score=1234567)]
        scores.extend(ScoreEntry(name="A", score=3) for _ in range(9))
        mlx = Mock()
        self.gui.ranking(mlx, 1, 2, 800, 600, scores)
        rows = [call[-1] for call in self.text_calls(mlx) if ". " in call[-1]]
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(set(map(len, rows))), 1)
        self.assertEqual(rows[0].index("LONGEST_NAME"), rows[-1].index("A"))
        self.assertEqual(rows[0].index("1234567") + 7, rows[-1].index("3") + 1)

    def test_power_time_is_centered_above_the_bar(self) -> None:
        mlx = Mock()
        self.gui.invinsible_time(mlx, 1, 2, 801, 600, 3.25)
        _, _, x, y, _, text = self.text_calls(mlx)[0]
        self.assertEqual(text, "Invincible 3.2")
        self.assertLessEqual(abs(x - (801-x-len(text)*10)), 1)
        self.assertEqual(y, 530)

    def test_pause_background_contains_all_pause_text(self) -> None:
        viewer = MazeVisualizer.__new__(MazeVisualizer)
        viewer.closed = False
        viewer.state = GUIStateEnum.Pause
        viewer.canvas = Mock()
        viewer.m = Mock()
        viewer.gui = Mock(wraps=GUI())
        viewer.p = viewer.win = viewer.img = 1
        viewer.width, viewer.height = 800, 600
        viewer.cmodes = [((255, 255, 255), (255, 0, 0), (0, 0, 0))]
        viewer.cm = 0
        viewer.maze = Mock()
        viewer.pacgums = Mock()
        viewer.ghosts = []
        viewer.player = SimpleNamespace(
            is_invincible=False, draw=Mock(), score=100, lives=3,
        )
        viewer.level, viewer.remaining_time = 1, 30.0
        viewer.cheat_enabled = False
        viewer._draw()
        _, x, y, width, height = viewer.gui.background.call_args.args
        self.assertLessEqual(abs(x-(viewer.width-x-width)), 1)
        self.assertLessEqual(abs(y-(viewer.height-y-height)), 1)
        labels = {"PAUSED", "P: Resume", "H: Back to home"}
        calls = [call for call in self.text_calls(viewer.m) if call[-1] in labels]
        self.assertEqual(len(calls), 3)
        for _, _, text_x, text_y, _, text in calls:
            self.assertGreaterEqual(text_x, x)
            self.assertLessEqual(text_x+len(text)*10, x+width)
            self.assertGreaterEqual(text_y, y)
            self.assertLessEqual(text_y+20, y+height)


if __name__ == "__main__":
    unittest.main()

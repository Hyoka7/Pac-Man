"""Home rendering should persist until its content needs refreshing."""

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from visualize.cheating import CheatHandler
from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import HighscoreManager, ScoreEntry
from visualize.maze_visualizer import KeyEnum, MazeVisualizer


class HomeRedrawTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch('visualize.text.TextRenderer.draw_text')
        self.draw_text = patcher.start()
        self.addCleanup(patcher.stop)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.viewer = MazeVisualizer.__new__(MazeVisualizer)
        v = self.viewer
        v.closed = False
        v.cheathandler = CheatHandler(list(map(ord, 'harnakam')))
        v.cheat_enabled = False
        v.state = GUIStateEnum.Home
        v.home_focusing = 0
        v.ranking_page = 0
        v.needs_redraw = True
        v.last_time = monotonic()
        v.canvas = Mock(width=600, height=600)
        v.m = Mock()
        v.gui = Mock()
        v.p = v.win = v.img = 1
        v.width = v.height = 600
        v.player = SimpleNamespace(
            is_invincible=False, score=120, lives=3,
            draw=Mock(), update=Mock(), update_mouth=Mock(),
        )
        v.maze = Mock()
        v.pacgums = MagicMock()
        v.pacgums.__len__.return_value = 1
        v.ghosts = []
        v.cmodes = [((255, 255, 255), (255, 0, 0), (0, 0, 0))]
        v.cm = 0
        v.level = 1
        v.remaining_time = 42.0
        v.player_name = "Alice"
        v.score_manager = HighscoreManager(
            str(Path(self.directory.name) / "scores.json")
        )

    def test_initial_draw_is_not_repeated_by_idle_loops(self) -> None:
        v = self.viewer
        v._draw()
        for _ in range(3):
            v._on_loop()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.gui.home.assert_called_once()
        self.assertFalse(v.needs_redraw)
        self.assertGreater(v.last_time, 0.0)

    def test_home_arrows_cycle_selection_and_request_redraw(self) -> None:
        v = self.viewer
        for initial, key, expected in (
            (0, KeyEnum.UP, 2),
            (1, KeyEnum.UP, 0),
            (2, KeyEnum.UP, 1),
            (0, KeyEnum.DOWN, 1),
            (1, KeyEnum.DOWN, 2),
            (2, KeyEnum.DOWN, 0),
        ):
            with self.subTest(initial=initial, key=key):
                v.home_focusing = initial
                v.needs_redraw = False
                v._on_key(key)
                self.assertEqual(v.home_focusing, expected)
                self.assertTrue(v.needs_redraw)

    def test_return_after_score_save_refreshes_home_once(self) -> None:
        v = self.viewer
        v._draw()
        v.state = GUIStateEnum.GameOver
        v._on_key(KeyEnum.ENTER)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)
        scores = v.gui.home.call_args.args[-2]
        self.assertEqual(v.gui.home.call_args.args[-1], v.home_focusing)
        self.assertEqual((scores[0].name, scores[0].score), ("Alice", 120))

    def test_expose_can_redraw_an_unchanged_home(self) -> None:
        v = self.viewer
        v._draw()
        v._draw()  # Same callback registered with mlx_expose_hook.
        self.assertEqual(v.gui.home.call_count, 2)

    def test_stage_clear_draws_once_then_remains_idle(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Stage_Clear
        v.needs_redraw = True
        v._on_loop()
        v._on_loop()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.gui.stage_clear.assert_called_once()

    def test_enter_activates_the_focused_home_option(self) -> None:
        v = self.viewer
        v.restart_game = Mock()
        for focusing, expected in (
            (0, GUIStateEnum.Playing),
            (1, GUIStateEnum.Instruction),
            (2, GUIStateEnum.Ranking),
        ):
            with self.subTest(focusing=focusing):
                v.state = GUIStateEnum.Home
                v.home_focusing = focusing
                v.needs_redraw = False
                v.restart_game.reset_mock()
                v._on_key(KeyEnum.ENTER)
                if focusing == 0:
                    v.restart_game.assert_called_once()
                else:
                    v.restart_game.assert_not_called()
                    self.assertEqual(v.state, expected)
                    self.assertTrue(v.needs_redraw)

    def test_home_focus_change_rebuilds_complete_frame(self) -> None:
        v = self.viewer
        v.gui = Mock(wraps=GUI())
        v.score_manager.scores.scores = [
            ScoreEntry(name=f'player{i}', score=100-i) for i in range(5)
        ]
        v._draw()
        v.m.reset_mock()
        self.draw_text.reset_mock()
        v.gui.reset_mock()
        v.canvas.reset_mock()
        v._on_key(KeyEnum.DOWN)
        v._on_loop()
        v.gui.home.assert_called_once()
        v.gui.draw_backdrop.assert_called_once()
        v.canvas.clear_image.assert_called_once_with()
        strings = [call.args[3] for call in self.draw_text.call_args_list]
        self.assertGreater(len(strings), 3)
        self.assertTrue(any(
            text.startswith('> ') and 'Instruction' in text for text in strings
        ))
        v._on_loop()
        v.m.mlx_put_image_to_window.assert_called_once()

    def test_home_arrow_before_first_draw_still_paints_the_whole_screen(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.DOWN)
        v._on_loop()
        v.gui.home.assert_called_once()
        self.assertEqual(v.gui.home.call_args.args[-1], 1)
        v.canvas.clear_image.assert_called_once_with()

    def test_expose_after_partial_update_restores_the_whole_screen(self) -> None:
        v = self.viewer
        v._draw()
        v._on_key(KeyEnum.DOWN)
        v._on_loop()
        v.gui.home.assert_called()
        v.gui.reset_mock()
        v.canvas.reset_mock()
        v._draw()  # Expose must rebuild the full frame after transparent clearing.
        v.canvas.clear_image.assert_called_once_with()
        v.gui.draw_backdrop.assert_called_once_with(v.canvas, GUIStateEnum.Home)
        v.gui.home.assert_called_once()

    def test_stage_clear_transition_requests_a_draw(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Playing
        v.needs_redraw = False
        v.pacgums.__len__.return_value = 0
        v.max_level = 2
        v._on_loop()
        self.assertEqual(v.state, GUIStateEnum.Stage_Clear)
        v.gui.stage_clear.assert_called_once()
        v._on_loop()
        v.gui.stage_clear.assert_called_once()

    def test_pause_draws_once_without_updating_game(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Playing
        v.needs_redraw = False
        v._on_key(KeyEnum.P)
        self.assertTrue(v.needs_redraw)
        for _ in range(3):
            v._on_loop()
        v.gui.pause.assert_called_once()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.player.update.assert_not_called()
        self.assertEqual(v.remaining_time, 42.0)

    def test_expose_can_redraw_pause(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Pause
        v._draw()
        self.assertFalse(v.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.pause.call_count, 2)

    def test_pause_to_home_refreshes_home(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Pause
        v.needs_redraw = False
        v._on_key(KeyEnum.H)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.home.assert_called_once()

    def test_resume_keeps_updating_and_drawing(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Pause
        v.needs_redraw = False
        v._on_key(KeyEnum.P)
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.player.update.call_count, 2)
        self.assertEqual(v.m.mlx_put_image_to_window.call_count, 2)

    def test_instructions_draw_once_and_enter_returns_home(self) -> None:
        v = self.viewer
        v._draw()
        v._on_key(KeyEnum.I)
        self.assertEqual(v.state, GUIStateEnum.Instruction)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.instruction.assert_called_once()
        v.player.update.assert_not_called()
        self.assertEqual(v.remaining_time, 42.0)
        v._on_key(KeyEnum.RIGHT)
        self.assertFalse(v.needs_redraw)
        v._on_key(KeyEnum.ENTER)
        self.assertEqual(v.state, GUIStateEnum.Home)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)

    def test_instructions_can_redraw_on_expose(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Instruction
        v._draw()
        self.assertFalse(v.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.instruction.call_count, 2)

    def test_ranking_draws_once_and_enter_returns_home(self) -> None:
        v = self.viewer
        v._draw()
        v._on_key(KeyEnum.H)
        self.assertEqual(v.state, GUIStateEnum.Ranking)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.ranking.assert_called_once_with(
            v.canvas, v.width, v.height, v.score_manager.scores.scores, 0,
        )
        v.player.update.assert_not_called()
        self.assertEqual(v.remaining_time, 42.0)
        v._on_key(KeyEnum.ENTER)
        self.assertEqual(v.state, GUIStateEnum.Home)
        self.assertTrue(v.needs_redraw)
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)

    def test_ranking_can_redraw_on_expose(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Ranking
        v._draw()
        self.assertFalse(v.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.ranking.call_count, 2)

    def test_ranking_arrows_change_pages_and_stop_at_bounds(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Ranking
        v.ranking_page = 0
        v.score_manager.scores.scores = [
            ScoreEntry(name=f'p{i}', score=100-i) for i in range(23)
        ]
        for key, expected in (
            (KeyEnum.LEFT, 0), (KeyEnum.RIGHT, 1), (KeyEnum.RIGHT, 2),
            (KeyEnum.RIGHT, 2), (KeyEnum.LEFT, 1), (KeyEnum.LEFT, 0),
        ):
            with self.subTest(key=key, page=expected):
                previous = v.ranking_page
                v.needs_redraw = False
                v._on_key(key)
                self.assertEqual(v.ranking_page, expected)
                self.assertEqual(v.needs_redraw, previous != expected)

    def test_ranking_later_pages_keep_absolute_ranks(self) -> None:
        scores = [ScoreEntry(name=f'p{i}', score=100-i) for i in range(23)]
        for page, first, last, count in ((1, 11, 20, 10), (2, 21, 23, 3)):
            with self.subTest(page=page):
                mlx = Mock()
                self.draw_text.reset_mock()
                GUI().ranking(mlx, 800, 600, scores, page)
                strings = [c.args[3] for c in self.draw_text.call_args_list]
                ranks = [text for text in strings if text.endswith('.')]
                self.assertEqual(len(ranks), count)
                self.assertEqual(ranks[0], f'{first}.')
                self.assertEqual(ranks[-1], f'{last}.')
                self.assertTrue(any(f'{page+1}/3' in text for text in strings))

    def test_empty_and_single_page_rankings_do_not_move(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Ranking
        for count in (0, 1, 10):
            v.score_manager.scores.scores = [
                ScoreEntry(name='Player', score=100) for _ in range(count)
            ]
            for key in (KeyEnum.LEFT, KeyEnum.RIGHT):
                v.ranking_page = 0
                v.needs_redraw = False
                v._on_key(key)
                self.assertEqual(v.ranking_page, 0)
                self.assertFalse(v.needs_redraw)

    def test_reopening_ranking_starts_at_first_page(self) -> None:
        v = self.viewer
        v.state = GUIStateEnum.Ranking
        v.ranking_page = 2
        v._on_key(KeyEnum.ENTER)
        v.home_focusing = 2
        v._on_key(KeyEnum.ENTER)
        self.assertEqual(v.state, GUIStateEnum.Ranking)
        self.assertEqual(v.ranking_page, 0)

    def test_ranking_renders_only_top_ten_and_handles_empty_list(self) -> None:
        scores = [ScoreEntry(name=f'p{i}', score=100-i) for i in range(12)]
        for entries in ([], scores):
            with self.subTest(size=len(entries)):
                m = Mock()
                self.draw_text.reset_mock()
                GUI().ranking(m, 800, 600, entries)
                strings = [call.args[3] for call in self.draw_text.call_args_list]
                self.assertEqual(strings[0], 'Highscore Ranking')
                if entries:
                    ranks = [text for text in strings if text.endswith('.')]
                    self.assertEqual(ranks, [f'{rank}.' for rank in range(1, 11)])
                    self.assertIn('p0', strings)
                    self.assertIn('p9', strings)
                    self.assertNotIn('p10', strings)
                else:
                    self.assertIn('No scores yet', strings)
                self.assertTrue(any('Left/Right: Page' in text for text in strings))
                self.assertTrue(any('Enter: Home' in text for text in strings))

    def test_name_entry_frame_uses_one_image_without_native_text(self) -> None:
        """Name and score edits no longer add native text drawing commands."""
        v = self.viewer
        v.gui = GUI()
        v.player.invincible_remain = 3.25
        for state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            for name in ('', 'A', 'ABCDEFGHIJKL'):
                for score in (0, 1234567, 9999999999):
                    for invincible in (False, True):
                        with self.subTest(
                            state=state, name=name, score=score,
                            invincible=invincible,
                        ):
                            v.state = state
                            v.player_name = name
                            v.player.score = score
                            v.player.is_invincible = invincible
                            v.m.reset_mock()
                            self.draw_text.reset_mock()
                            v.canvas.reset_mock()
                            v._draw()
                            strings = [
                                call.args[3]
                                for call in self.draw_text.call_args_list
                            ]
                            self.assertTrue(any(str(score) in text for text in strings))
                            self.assertTrue(any('name' in text.lower() for text in strings))
                            if name:
                                self.assertTrue(any(name in text for text in strings))
                            v.m.mlx_put_image_to_window.assert_called_once()
                            v.m.mlx_string_put.assert_not_called()
                            v.m.mlx_sync.assert_not_called()

    def test_name_edits_redraw_once_then_remain_idle(self) -> None:
        v = self.viewer
        v.gui = GUI()
        for state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            for key, expected_name in (
                (ord('B'), 'AliceB'), (KeyEnum.BACKSPACE, 'Alic'),
            ):
                with self.subTest(state=state, key=key):
                    v.state = state
                    v.player_name = 'Alice'
                    v.needs_redraw = False
                    v.m.reset_mock()
                    self.draw_text.reset_mock()
                    v._on_key(key)
                    self.assertEqual(v.player_name, expected_name)
                    self.assertTrue(v.needs_redraw)
                    v._on_loop()
                    strings = [
                        call.args[3]
                        for call in self.draw_text.call_args_list
                    ]
                    self.assertTrue(any(expected_name in text for text in strings))
                    self.assertFalse(v.needs_redraw)
                    for _ in range(2):
                        v._on_loop()
                    v.m.mlx_put_image_to_window.assert_called_once()

    def test_power_bar_and_timer_only_appear_during_play_or_pause(self) -> None:
        v = self.viewer
        v.gui = Mock(wraps=GUI())
        v.player.invincible_remain = 3.25
        for state in GUIStateEnum:
            for invincible in (False, True):
                with self.subTest(state=state, invincible=invincible):
                    v.state = state
                    v.player.is_invincible = invincible
                    v.m.reset_mock()
                    self.draw_text.reset_mock()
                    v.gui.reset_mock()
                    v.canvas.reset_mock()
                    v._draw()
                    expected = (
                        invincible
                        and state in (GUIStateEnum.Playing, GUIStateEnum.Pause)
                    )
                    strings = [
                        call.args[3]
                        for call in self.draw_text.call_args_list
                    ]
                    self.assertEqual(
                        any(text.startswith('Invincible ') for text in strings),
                        expected,
                    )
                    self.assertEqual(v.gui.draw_invincible_bar.call_count, int(expected))

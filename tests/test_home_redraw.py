"""Home rendering should persist until its content needs refreshing."""

from typing import Any, cast

from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import ImageFont

from visualize.game import Game
from visualize.cheating import CheatHandler
from visualize.gui import GUI, GUIStateEnum
from visualize.highscore import HighscoreManager, ScoreEntry
from visualize.controls import KeyEnum
from visualize.maze_visualizer import MazeVisualizer

FONT_PATH = Path(__file__).resolve().parents[1] / "assets/fonts/PressStart2P-Regular.ttf"


class HomeRedrawTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch('visualize.image_renderer.ImageRenderer.draw_text')
        self.draw_text = patcher.start()
        self.addCleanup(patcher.stop)
        image_patcher = patch('visualize.image_renderer.ImageRenderer.draw_image')
        self.draw_image = image_patcher.start()
        self.addCleanup(image_patcher.stop)
        hud_patcher = patch(
            'visualize.image_renderer.ImageRenderer.draw_numeric_text',
            new=self.draw_text,
        )
        hud_patcher.start()
        self.addCleanup(hud_patcher.stop)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.viewer = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
        self.viewer.audio = Mock()
        self.viewer.game = cast(Any, Game.__new__(Game))
        self.viewer.game.level_needs_placement = False
        self.viewer.game.no_collision = False
        self.viewer.canvas = Mock()
        v = self.viewer
        v.closed = False
        v.game.shift_keys = set()
        v.game.cheathandler = CheatHandler(list(map(ord, '3111696')))
        v.game.cheat_enabled = False
        v.game.auto_enabled = False
        v.game.ghost_frozen = False
        v.game.score_multiplier = 1
        v.game.pacgum_points = {}
        v.game.state = GUIStateEnum.Home
        v.game.home_focusing = 0
        v.game.needs_redraw = True
        v.last_time = monotonic()
        v.canvas = Mock(width=600, height=600)
        v.m = Mock()
        v.gui = Mock(bar_width=200, bar_height=10, bar_y=570, hud_x=20, hud_y=15)
        v.p = v.win = v.img = 1
        v.width = v.height = 600
        v.game.player = SimpleNamespace(
            is_invincible=False, score=120, lives=3,
            draw=Mock(), update=Mock(), update_mouth=Mock(),
        )
        v.game.maze = Mock()
        v.game.pacgums = MagicMock()
        v.game.pacgums.__len__.return_value = 1
        v.game.ghosts = []
        v.cmodes = [((255, 255, 255), (255, 0, 0), (0, 0, 0))]
        v.cm = 0
        v.game.level = 1
        v.game.remaining_time = 42.0
        v.game.player_name = "Alice"
        v.game.score_manager = HighscoreManager(
            str(Path(self.directory.name) / "scores.json")
        )

    def test_invincible_bar_scales_and_keeps_its_center(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Playing
        v.game.player.is_invincible = True
        v.game.player.invincible_remain = 2.5
        v.gui = GUI()
        for width, height, track, remaining in (
            (800, 600, (300, 570, 200, 10), (350, 570, 100, 10)),
            (1600, 1200, (600, 1140, 400, 20), (700, 1140, 200, 20)),
        ):
            with self.subTest(size=(width, height)):
                v.width, v.height = width, height
                v.canvas = Mock(width=width, height=height)
                v.gui.update_layout(width, height)
                v._draw()
                calls = v.canvas.fill_rect.call_args_list
                self.assertEqual(calls[0].args[:4], track)
                self.assertEqual(calls[1].args[:4], remaining)

    def test_scaled_footer_and_hud_fit_between_maze_and_window_edges(self) -> None:
        v = self.viewer
        v.gui = GUI()
        v.game.state = GUIStateEnum.Playing
        v.game.player.is_invincible = True
        v.game.player.invincible_remain = 2.5
        v.game.maze.cols = v.game.maze.rows = 15
        for width, height in ((800, 600), (1280, 720), (2460, 1340),
                              (4000, 2200), (720, 1280)):
            with self.subTest(size=(width, height)):
                v.width, v.height = width, height
                v.canvas = Mock(width=width, height=height)
                v._update_layout()
                self.draw_text.reset_mock()
                v._draw()
                x, bar_y, bar_width, bar_height = v.canvas.fill_rect.call_args_list[0].args[:4]
                padding = v.gui.font_size
                self.assertGreaterEqual(x, padding)
                self.assertLessEqual(x+bar_width, width-padding)
                self.assertLessEqual(bar_y+bar_height, height-padding)
                calls = [c.args for c in self.draw_text.call_args_list]
                timer = next(c for c in calls if c[3].startswith('Invincible '))
                hud = next(c for c in calls if c[3].startswith('Lv:'))
                ascent, descent = ImageFont.truetype(FONT_PATH, size=v.gui.font_size).getmetrics()
                line_height = ascent+descent
                gap = max(1, round(padding/4))
                maze_bottom = v.offset_y + v.game.maze.rows*v.cell_size
                self.assertGreaterEqual(timer[2]-maze_bottom, padding)
                self.assertLessEqual(timer[2]+line_height+gap, bar_y)
                self.assertLessEqual(hud[2]+line_height+padding, v.offset_y)

    def test_initial_draw_is_not_repeated_by_idle_loops(self) -> None:
        v = self.viewer
        v._draw()
        for _ in range(3):
            v._on_loop()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.gui.home.assert_called_once()
        self.assertFalse(v.game.needs_redraw)
        self.assertGreater(v.last_time, 0.0)

    def test_home_arrows_cycle_selection_and_request_redraw(self) -> None:
        v = self.viewer
        for initial, key, expected in (
            (0, KeyEnum.UP, 3),
            (1, KeyEnum.UP, 0),
            (2, KeyEnum.UP, 1),
            (3, KeyEnum.UP, 2),
            (0, KeyEnum.DOWN, 1),
            (1, KeyEnum.DOWN, 2),
            (2, KeyEnum.DOWN, 3),
            (3, KeyEnum.DOWN, 0),
        ):
            with self.subTest(initial=initial, key=key):
                v.game.home_focusing = initial
                v.game.needs_redraw = False
                v._on_key(key)
                self.assertEqual(v.game.home_focusing, expected)
                self.assertTrue(v.game.needs_redraw)

    def test_return_after_score_save_refreshes_home_once(self) -> None:
        v = self.viewer
        v._draw()
        v.game.state = GUIStateEnum.GameOver
        v._on_key(KeyEnum.ENTER)
        self.assertTrue(v.game.needs_redraw)
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)
        scores = v.gui.home.call_args.args[-2]
        self.assertEqual(v.gui.home.call_args.args[-1], v.game.home_focusing)
        self.assertEqual((scores[0].name, scores[0].score), ("Alice", 120))

    def test_expose_can_redraw_an_unchanged_home(self) -> None:
        v = self.viewer
        v._draw()
        v._draw()  # Same callback registered with mlx_expose_hook.
        self.assertEqual(v.gui.home.call_count, 2)

    def test_stage_clear_draws_once_then_remains_idle(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Stage_Clear
        v.game.needs_redraw = True
        v._on_loop()
        v._on_loop()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.gui.stage_clear.assert_called_once()

    def test_enter_activates_the_focused_home_option(self) -> None:
        v = self.viewer
        v.game.restart_game = Mock()
        for focusing, expected in (
            (0, GUIStateEnum.Playing),
            (1, GUIStateEnum.Instruction),
            (2, GUIStateEnum.Ranking),
        ):
            with self.subTest(focusing=focusing):
                v.game.state = GUIStateEnum.Home
                v.game.home_focusing = focusing
                v.game.needs_redraw = False
                v.game.restart_game.reset_mock()
                v._on_key(KeyEnum.ENTER)
                if focusing == 0:
                    v.game.restart_game.assert_called_once()
                else:
                    v.game.restart_game.assert_not_called()
                    self.assertEqual(v.game.state, expected)
                    self.assertTrue(v.game.needs_redraw)

    def test_exit_menu_closes_resources_once_and_stops_redrawing(self) -> None:
        v = self.viewer
        v.game.home_focusing = 3
        v._on_key(KeyEnum.ENTER)
        self.assertTrue(v.closed)
        v._close()
        v._on_loop()
        v._draw()
        v.m.mlx_destroy_image.assert_called_once_with(v.p, v.img)
        v.m.mlx_destroy_window.assert_called_once_with(v.p, v.win)
        v.m.mlx_loop_exit.assert_called_once_with(v.p)
        v.m.mlx_put_image_to_window.assert_not_called()
        v.game.player.update.assert_not_called()

    def test_home_focus_change_rebuilds_complete_frame(self) -> None:
        v = self.viewer
        gui = GUI()
        gui.update_layout(800, 600)
        v.gui = Mock(wraps=gui, bar_width=gui.bar_width, bar_height=gui.bar_height,
                     hud_x=gui.hud_x, hud_y=gui.hud_y, bar_y=gui.bar_y)
        v.game.score_manager.scores.scores = [
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
        self.assertIn('Instruction', strings)
        self.assertIn('>', strings)
        selected = next(call.args for call in self.draw_text.call_args_list
                        if call.args[3] == 'Instruction')
        marker = next(call.args for call in self.draw_text.call_args_list
                      if call.args[3] == '>')
        self.assertEqual(selected[2], marker[2])
        self.assertEqual(selected[4], gui.ACCENT_COLOR)
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
        v.game.state = GUIStateEnum.Playing
        v.game.needs_redraw = False
        v.game.pacgums.__len__.return_value = 0
        v.game.max_level = 2
        v._on_loop()
        self.assertEqual(v.game.state, GUIStateEnum.Stage_Clear)
        v.gui.stage_clear.assert_called_once()
        v._on_loop()
        v.gui.stage_clear.assert_called_once()

    def test_pause_draws_once_without_updating_game(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Playing
        v.game.needs_redraw = False
        v._on_key(KeyEnum.P)
        self.assertTrue(v.game.needs_redraw)
        for _ in range(3):
            v._on_loop()
        v.gui.pause.assert_called_once()
        v.m.mlx_put_image_to_window.assert_called_once()
        v.game.player.update.assert_not_called()
        self.assertEqual(v.game.remaining_time, 42.0)

    def test_expose_can_redraw_pause(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Pause
        v._draw()
        self.assertFalse(v.game.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.pause.call_count, 2)

    def test_pause_to_home_refreshes_home(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Pause
        v.game.needs_redraw = False
        v._on_key(KeyEnum.H)
        self.assertTrue(v.game.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.home.assert_called_once()

    def test_resume_keeps_updating_and_drawing(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Pause
        v.game.needs_redraw = False
        v._on_key(KeyEnum.P)
        v._on_loop()
        v._on_loop()
        self.assertEqual(v.game.player.update.call_count, 2)
        self.assertEqual(v.m.mlx_put_image_to_window.call_count, 2)

    def test_instructions_draw_once_and_enter_returns_home(self) -> None:
        v = self.viewer
        v._draw()
        v._on_key(KeyEnum.I)
        self.assertEqual(v.game.state, GUIStateEnum.Instruction)
        self.assertTrue(v.game.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.instruction.assert_called_once()
        v.game.player.update.assert_not_called()
        self.assertEqual(v.game.remaining_time, 42.0)
        v._on_key(KeyEnum.RIGHT)
        self.assertFalse(v.game.needs_redraw)
        v._on_key(KeyEnum.ENTER)
        self.assertEqual(v.game.state, GUIStateEnum.Home)
        self.assertTrue(v.game.needs_redraw)
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)

    def test_instructions_can_redraw_on_expose(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Instruction
        v._draw()
        self.assertFalse(v.game.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.instruction.call_count, 2)

    def test_ranking_draws_once_and_enter_returns_home(self) -> None:
        v = self.viewer
        v._draw()
        v._on_key(KeyEnum.H)
        self.assertEqual(v.game.state, GUIStateEnum.Ranking)
        self.assertTrue(v.game.needs_redraw)
        v._on_loop()
        v._on_loop()
        v.gui.ranking.assert_called_once_with(
            v.canvas, v.width, v.height, v.game.score_manager.scores.scores,
        )
        v.game.player.update.assert_not_called()
        self.assertEqual(v.game.remaining_time, 42.0)
        v._on_key(KeyEnum.ENTER)
        self.assertEqual(v.game.state, GUIStateEnum.Home)
        self.assertTrue(v.game.needs_redraw)
        v._on_loop()
        self.assertEqual(v.gui.home.call_count, 2)

    def test_ranking_can_redraw_on_expose(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Ranking
        v._draw()
        self.assertFalse(v.game.needs_redraw)
        v._draw()
        self.assertEqual(v.gui.ranking.call_count, 2)

    def test_ranking_arrows_do_not_change_the_screen_or_request_redraw(self) -> None:
        v = self.viewer
        v.game.state = GUIStateEnum.Ranking
        v.game.score_manager.scores.scores = [
            ScoreEntry(name=f'p{i}', score=100-i) for i in range(23)
        ]
        for key in (KeyEnum.LEFT, KeyEnum.RIGHT):
            with self.subTest(key=key):
                v.game.needs_redraw = False
                v._on_key(key)
                self.assertEqual(v.game.state, GUIStateEnum.Ranking)
                self.assertFalse(v.game.needs_redraw)

    def test_ranking_renders_only_top_ten_and_handles_empty_list(self) -> None:
        scores = [ScoreEntry(name=f'p{i}', score=100-i) for i in range(12)]
        for entries in ([], scores):
            with self.subTest(size=len(entries)):
                m = Mock()
                self.draw_text.reset_mock()
                gui = GUI()
                gui.update_layout(800, 600)
                gui.ranking(m, 800, 600, entries)
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
                self.assertIn('C: Clear  Enter: Home', strings)
                self.assertFalse(any('Page' in text or 'Left/Right' in text for text in strings))

    def test_name_entry_frame_uses_one_image_without_native_text(self) -> None:
        """Name and score edits no longer add native text drawing commands."""
        v = self.viewer
        v.gui = GUI()
        v.gui.update_layout(v.width, v.height)
        v.game.player.invincible_remain = 3.25
        for state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            for name in ('', 'A', 'ABCDEFGHIJ'):
                for score in (0, 1234567, 9999999999):
                    for invincible in (False, True):
                        with self.subTest(
                            state=state, name=name, score=score,
                            invincible=invincible,
                        ):
                            v.game.state = state
                            v.game.player_name = name
                            v.game.player.score = score
                            v.game.player.is_invincible = invincible
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
        v.gui.update_layout(v.width, v.height)
        for state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            for key, expected_name in (
                (ord('B'), 'AliceB'), (KeyEnum.BACKSPACE, 'Alic'),
            ):
                with self.subTest(state=state, key=key):
                    v.game.state = state
                    v.game.player_name = 'Alice'
                    v.game.needs_redraw = False
                    v.m.reset_mock()
                    self.draw_text.reset_mock()
                    v._on_key(key)
                    self.assertEqual(v.game.player_name, expected_name)
                    self.assertTrue(v.game.needs_redraw)
                    v._on_loop()
                    strings = [
                        call.args[3]
                        for call in self.draw_text.call_args_list
                    ]
                    self.assertTrue(any(expected_name in text for text in strings))
                    self.assertFalse(v.game.needs_redraw)
                    for _ in range(2):
                        v._on_loop()
                    v.m.mlx_put_image_to_window.assert_called_once()

    def test_power_bar_and_timer_only_appear_during_play_or_pause(self) -> None:
        v = self.viewer
        gui = GUI()
        gui.update_layout(800, 600)
        v.gui = Mock(wraps=gui, bar_width=gui.bar_width, bar_height=gui.bar_height,
                     hud_x=gui.hud_x, hud_y=gui.hud_y, bar_y=gui.bar_y)
        v.game.player.invincible_remain = 3.25
        for state in GUIStateEnum:
            for invincible in (False, True):
                with self.subTest(state=state, invincible=invincible):
                    v.game.state = state
                    v.game.player.is_invincible = invincible
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

"""Cheat commands require a complete ordered sequence and reset on mistakes."""

from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from visualize.cheating import CheatHandler
from visualize.gui import GUI, GUIStateEnum
from visualize.maze_visualizer import KeyEnum, MazeVisualizer


class CheatHandlerTests(unittest.TestCase):
    def test_only_the_last_key_completes_a_command(self) -> None:
        keys = [1, 1, 2, 2, 3, 4, 3, 4, 98, 97]
        command = CheatHandler(keys)
        self.assertEqual([command.consume(key) for key in keys],
                         [False] * (len(keys)-1) + [True])

    def test_mistake_requires_a_fresh_complete_sequence(self) -> None:
        command = CheatHandler([1, 2, 3])
        self.assertEqual([command.consume(key) for key in [1, 9, 2, 3]],
                         [False] * 4)
        self.assertEqual([command.consume(key) for key in [1, 2, 3]],
                         [False, False, True])

    def test_success_can_be_followed_by_another_command(self) -> None:
        command = CheatHandler([1, 2])
        self.assertEqual([command.consume(key) for key in [1, 2, 9, 1, 2]],
                         [False, True, False, False, True])

    def test_single_key_command_completes_and_resets(self) -> None:
        command = CheatHandler([7])
        self.assertEqual([command.consume(key) for key in [9, 7, 7]],
                         [False, True, True])


class CheatInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.viewer = MazeVisualizer.__new__(MazeVisualizer)
        v = self.viewer
        v.closed = False
        v.shift_keys = set()
        v.state = GUIStateEnum.Playing
        v.cheat_enabled = False
        v.ghost_frozen = False
        v.cheathandler = CheatHandler(list(map(ord, 'harnakam')))
        v.player, v.maze, v.canvas = Mock(), Mock(), Mock()
        v.next_level = Mock()

    def enter_command(self) -> None:
        for key in map(ord, 'harnakam'):
            self.viewer._on_key(key)

    def test_enable_and_disable_do_not_move_or_skip_during_command(self) -> None:
        v = self.viewer
        self.enter_command()
        self.assertTrue(v.cheat_enabled)
        self.enter_command()
        self.assertFalse(v.cheat_enabled)
        v.player.request_move.assert_not_called()
        v.next_level.assert_not_called()

    def test_level_skip_is_available_only_when_enabled(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.N)
        v.next_level.assert_not_called()
        self.enter_command()
        v._on_key(KeyEnum.N)
        v.next_level.assert_called_once()
        self.enter_command()
        v._on_key(KeyEnum.N)
        v.next_level.assert_called_once()

    def test_life_and_time_keys_require_cheats_and_stop_after_disabling(self) -> None:
        v = self.viewer
        v.player.lives, v.remaining_time = 3, 12.5
        v._on_key(KeyEnum.L)
        v._on_key(KeyEnum.T)
        self.assertEqual((v.player.lives, v.remaining_time), (3, 12.5))
        self.enter_command()
        for expected in ((4, 22.5), (5, 32.5)):
            v._on_key(KeyEnum.L)
            v._on_key(KeyEnum.T)
            self.assertEqual((v.player.lives, v.remaining_time), expected)
        self.enter_command()
        v._on_key(KeyEnum.L)
        v._on_key(KeyEnum.T)
        self.assertEqual((v.player.lives, v.remaining_time), (5, 32.5))
        v.player.request_move.assert_not_called()

    def test_life_and_time_cheats_do_not_apply_outside_playing(self) -> None:
        v = self.viewer
        v.cheat_enabled = True
        v.player.lives, v.remaining_time = 3, 12.5
        for state in (GUIStateEnum.Home, GUIStateEnum.Instruction,
                      GUIStateEnum.Ranking, GUIStateEnum.Pause,
                      GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            with self.subTest(state=state):
                v.state = state
                v.player_name = ''
                v._on_key(KeyEnum.L)
                v._on_key(KeyEnum.T)
                self.assertEqual((v.player.lives, v.remaining_time), (3, 12.5))
                if state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
                    self.assertEqual(v.player_name, 'lt')

    def test_wrong_key_resets_command_and_keeps_normal_controls(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.H)
        v._on_key(KeyEnum.UP)
        self.assertFalse(v.cheat_enabled)
        self.assertEqual(v.cheathandler.index, 0)
        v.player.request_move.assert_called_once_with('N', v.maze, v.canvas)

    def test_freeze_key_only_toggles_when_cheats_are_enabled(self) -> None:
        v = self.viewer
        v._on_key(KeyEnum.F)
        self.assertFalse(v.ghost_frozen)
        self.enter_command()
        v._on_key(KeyEnum.F)
        self.assertTrue(v.ghost_frozen)
        v._on_key(KeyEnum.F)
        self.assertFalse(v.ghost_frozen)

    def test_disabling_cheats_clears_freeze(self) -> None:
        v = self.viewer
        self.enter_command()
        v.ghost_frozen = True
        self.enter_command()
        self.assertFalse(v.cheat_enabled)
        self.assertFalse(v.ghost_frozen)

    def test_regular_movement_still_works_with_cheats_enabled(self) -> None:
        v = self.viewer
        self.enter_command()
        v._on_key(KeyEnum.RIGHT)
        v.player.request_move.assert_called_once_with('E', v.maze, v.canvas)

    def test_freeze_stops_ghost_update_but_preserves_player_and_collision(self) -> None:
        v = self.viewer
        v.cheat_enabled, v.ghost_frozen = True, True
        v.last_time, v.remaining_time = 10.0, 20.0
        v.pacgums = MagicMock()
        v.pacgums.__len__.return_value = 1
        v.player = SimpleNamespace(
            update=Mock(), update_mouth=Mock(), movement=SimpleNamespace(cell=(1, 0)),
            is_alive=True, is_invincible=False, lives=1,
        )
        ghost = Mock(respawn_remaining=0.0)
        v.ghosts = [ghost]
        v.judge = Mock()
        v.judge.is_collision.return_value = True
        v._draw = Mock()
        with redirect_stdout(StringIO()), patch(
            'visualize.maze_visualizer.time.monotonic', return_value=10.05
        ):
            v._on_loop()
        ghost.update.assert_not_called()
        v.player.update.assert_called_once()
        v.judge.is_collision.assert_called_once_with(v.player, ghost)
        self.assertEqual(v.state, GUIStateEnum.GameOver)
        self.assertEqual(v.player.lives, 0)
        v._draw.assert_called_once()


class CheatHudTests(unittest.TestCase):
    def test_cheat_label_is_only_shown_when_enabled(self) -> None:
        for enabled in (False, True):
            with self.subTest(enabled=enabled), patch('visualize.image_renderer.ImageRenderer.draw_text') as draw:
                gui = GUI()
                gui.update_layout(800, 600)
                gui.draw_stats(Mock(), 20, 15, 3, 120, 2, 42.5, enabled)
                text = draw.call_args.args[3]
                self.assertEqual('CHEAT ON' in text, enabled)
                for value in ('Lv:3', 'Score:120', 'Life:2', 'Time:42.5'):
                    self.assertIn(value, text)

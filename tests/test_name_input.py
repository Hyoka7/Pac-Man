"""Name entry preserves uppercase while tracking both Shift keys."""

from typing import Any, cast

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from visualize.gui import GUIStateEnum
from visualize.highscore import HighscoreManager
from visualize.maze_visualizer import KeyEnum, MazeVisualizer


def viewer(state: GUIStateEnum = GUIStateEnum.GameOver) -> Any:
    v = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
    v.closed = False
    v.state = state
    v.player_name = ''
    v.shift_keys = set()
    v.needs_redraw = False
    return v


class NameInputTests(unittest.TestCase):
    def test_either_shift_uppercases_only_while_held_on_both_end_screens(self) -> None:
        for state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            for shift in (KeyEnum.SHIFT_L, KeyEnum.SHIFT_R):
                with self.subTest(state=state, shift=shift):
                    v = viewer(state)
                    v._on_key(ord('a'))
                    v._on_key(shift)
                    v._on_key(ord('b'))
                    v._on_key_release(shift)
                    v._on_key(ord('c'))
                    self.assertEqual(v.player_name, 'aBc')
                    self.assertTrue(v.needs_redraw)

    def test_releasing_one_shift_keeps_the_other_active(self) -> None:
        v = viewer()
        v._on_key(KeyEnum.SHIFT_L)
        v._on_key(KeyEnum.SHIFT_R)
        v._on_key_release(KeyEnum.SHIFT_L)
        v._on_key(ord('a'))
        v._on_key_release(ord('a'))
        v._on_key(ord('b'))
        v._on_key_release(KeyEnum.SHIFT_R)
        v._on_key(ord('c'))
        self.assertEqual(v.player_name, 'ABc')

    def test_uppercase_keeps_name_limit_backspace_and_digits(self) -> None:
        v = viewer()
        v._on_key(KeyEnum.SHIFT_L)
        for key in 'abcdefghijklm':
            v._on_key(ord(key))
        self.assertEqual(v.player_name, 'ABCDEFGHIJ')
        v._on_key(KeyEnum.BACKSPACE)
        v._on_key(ord('7'))
        self.assertEqual(v.player_name, 'ABCDEFGHI7')
        v._on_key_release(KeyEnum.SHIFT_L)
        v._on_key_release(KeyEnum.SHIFT_L)
        self.assertFalse(v.shift_keys)

    def test_spaces_are_kept_and_eleventh_character_is_ignored(self) -> None:
        for state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            with self.subTest(state=state):
                v = viewer(state)
                for char in 'ab cd ef gh':
                    v._on_key(ord(char))
                self.assertEqual(v.player_name, 'ab cd ef g')
                v._on_key(KeyEnum.BACKSPACE)
                v._on_key(ord(' '))
                self.assertEqual(v.player_name, 'ab cd ef  ')

    def test_non_text_key_symbols_do_not_become_name_characters(self) -> None:
        for key in (KeyEnum.LEFT, KeyEnum.RIGHT, KeyEnum.UP, KeyEnum.DOWN, 0x1008FF12):
            with self.subTest(key=key):
                v = viewer()
                v.player_name = 'Alice'
                v._on_key(key)
                self.assertEqual(v.player_name, 'Alice')

    def test_saved_name_keeps_uppercase_after_reload(self) -> None:
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / 'scores.json')
            v = viewer()
            v.player = SimpleNamespace(score=123)
            v.score_manager = HighscoreManager(path)
            v._on_key(KeyEnum.SHIFT_L)
            for char in 'moae':
                v._on_key(ord(char))
            v._on_key_release(KeyEnum.SHIFT_L)
            v._on_key(KeyEnum.ENTER)
            saved = HighscoreManager(path).scores.scores[0]
            self.assertEqual((saved.name, saved.score), ('MOAE', 123))
            self.assertEqual(v.state, GUIStateEnum.Home)

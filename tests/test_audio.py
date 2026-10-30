"""Menu music survives screen changes without requiring a real audio device."""

from types import SimpleNamespace
from typing import Any, cast
import unittest
from unittest.mock import Mock, call, patch

from visualize.audio import AudioManager, AudioState
from visualize.game_state import GUIStateEnum
from visualize.maze_visualizer import MazeVisualizer
from visualize.pacgums import PacgumEatenEnum


class AudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mixer = self.enterContext(patch('visualize.audio.pygame.mixer'))
        self.sounds = {f'assets/audio/{name}.mp3': Mock()
                       for name in ('pacgum', 'eat', 'powerup')}
        self.mixer.Sound.side_effect = self.sounds.__getitem__
        self.audio = AudioManager()

    def viewer(self) -> Any:
        viewer = cast(Any, MazeVisualizer.__new__(MazeVisualizer))
        viewer.audio = self.audio
        viewer.closed = False
        viewer.last_time = 0.0
        viewer.canvas = Mock()
        viewer.game = SimpleNamespace(
            state=GUIStateEnum.Home, level_needs_placement=False,
            needs_redraw=False, update=Mock(return_value=(PacgumEatenEnum.Neither, 0)),
        )
        viewer._draw = Mock()
        return viewer

    def test_load_once_and_repeated_play_keeps_the_existing_track(self) -> None:
        self.audio.play_menu_bgm()
        self.audio.play_menu_bgm()
        self.mixer.init.assert_called_once_with()
        self.mixer.music.load.assert_called_once_with('assets/audio/menu_bgm.mp3')
        self.mixer.music.play.assert_called_once_with(-1)

    def test_stop_once_and_play_again_without_shutting_down_mixer(self) -> None:
        self.audio.play_menu_bgm()
        self.audio.stop_bgm()
        self.audio.stop_bgm()
        self.assertIsNone(self.audio.current_state)
        self.mixer.music.stop.assert_called_once_with()
        self.mixer.quit.assert_not_called()
        self.audio.play_menu_bgm()
        self.assertEqual(self.audio.current_state, AudioState.MENU)
        self.assertEqual(self.mixer.music.play.call_count, 2)

    def test_menu_screens_share_music_and_gameplay_switches_track_once(self) -> None:
        viewer = self.viewer()
        states = (GUIStateEnum.Home, GUIStateEnum.Ranking, GUIStateEnum.Instruction,
                  GUIStateEnum.Home, GUIStateEnum.Playing, GUIStateEnum.Pause)
        with patch('visualize.maze_visualizer.time.monotonic', return_value=1.0):
            for state in states:
                viewer.game.state = state
                viewer._on_loop()
        self.assertEqual(self.mixer.music.play.call_args_list, [call(-1), call(-1)])
        self.assertEqual(self.mixer.music.load.call_args_list,
                         [call('assets/audio/menu_bgm.mp3'), call('assets/audio/playing.ogg')])
        self.assertEqual(self.audio.current_state, AudioState.PLAYING)
        viewer.game.state = GUIStateEnum.Home
        viewer._on_loop()
        self.assertEqual(self.mixer.music.play.call_count, 3)
        self.assertEqual(self.audio.current_state, AudioState.MENU)

    def test_gum_sound_plays_only_for_normal_or_super_gum(self) -> None:
        viewer = self.viewer()
        sound = self.sounds['assets/audio/pacgum.mp3']
        powerup = self.sounds['assets/audio/powerup.mp3']
        self.mixer.Sound.assert_has_calls([call(path) for path in
            ('assets/audio/pacgum.mp3', 'assets/audio/eat.mp3', 'assets/audio/powerup.mp3')])
        for eaten in (PacgumEatenEnum.Neither, PacgumEatenEnum.Normal,
                      PacgumEatenEnum.Super, PacgumEatenEnum.Neither):
            viewer.game.update.return_value = eaten, 0
            viewer._on_loop()
        sound.play.assert_called_once_with()
        powerup.play.assert_called_once_with()
        self.sounds['assets/audio/eat.mp3'].play.assert_not_called()

    def test_gum_and_ghost_events_both_play_in_the_same_frame(self) -> None:
        viewer = self.viewer()
        for gum in (PacgumEatenEnum.Normal, PacgumEatenEnum.Super):
            with self.subTest(gum=gum):
                for sound in self.sounds.values():
                    sound.reset_mock()
                viewer.game.update.return_value = gum, 1
                viewer._on_loop()
                path = 'assets/audio/pacgum.mp3' if gum == PacgumEatenEnum.Normal else 'assets/audio/powerup.mp3'
                self.sounds[path].play.assert_called_once_with()
                self.sounds['assets/audio/eat.mp3'].play.assert_called_once_with()

    def test_ghost_event_plays_without_gum_and_does_not_repeat_next_frame(self) -> None:
        viewer = self.viewer()
        viewer.game.update.side_effect = [(PacgumEatenEnum.Neither, 2),
                                           (PacgumEatenEnum.Neither, 0)]
        viewer._on_loop()
        viewer._on_loop()
        self.sounds['assets/audio/eat.mp3'].play.assert_called_once_with()
        self.sounds['assets/audio/pacgum.mp3'].play.assert_not_called()

    def test_final_gum_still_plays_when_update_changes_screen_to_clear(self) -> None:
        viewer = self.viewer()
        viewer.game.state = GUIStateEnum.Playing
        def finish_level(*args: object) -> tuple[PacgumEatenEnum, int]:
            viewer.game.state = GUIStateEnum.All_Clear
            return PacgumEatenEnum.Normal, 0
        viewer.game.update.side_effect = finish_level
        viewer._on_loop()
        self.sounds['assets/audio/pacgum.mp3'].play.assert_called_once_with()

    def test_close_shuts_down_audio_once_and_closed_loops_do_not_restart_it(self) -> None:
        viewer = self.viewer()
        viewer.m = Mock()
        viewer.p = viewer.win = viewer.img = 1
        viewer._close()
        viewer._close()
        viewer._on_loop()
        self.mixer.quit.assert_called_once_with()
        self.mixer.music.play.assert_not_called()

    def test_gameover_screen_does_not_reload_or_restart_music_each_frame(self) -> None:
        viewer = self.viewer()
        viewer.game.state = GUIStateEnum.GameOver
        viewer._on_loop()
        viewer._on_loop()
        self.mixer.music.load.assert_called_once_with('assets/audio/gameover.mp3')
        self.assertEqual(self.mixer.music.play.call_count, 1)
        self.assertEqual(self.audio.current_state, AudioState.GAMEOVER)

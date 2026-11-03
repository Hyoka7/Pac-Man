"""Exercise window startup and cleanup without a display or audio device."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from pacman.models import Config
from pacman.models.models import LevelConfig
from pacman.visualize.maze_visualizer import MazeVisualizer


class WindowLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = self.enterContext(TemporaryDirectory())
        self.enterContext(patch('pacman.visualize.maze_visualizer.AudioManager'))
        config = Config(
            highscore_filename=str(Path(directory) / 'scores.json'),
            levels=[LevelConfig.model_construct(width=5, height=1)],
        )
        self.viewer = MazeVisualizer([[13, 5, 5, 5, 7]], Mock(), config)
        self.mlx = Mock()
        self.mlx.mlx_init.return_value = 1
        self.mlx.mlx_get_screen_size.return_value = (0, 320, 240)
        self.mlx.mlx_new_window.return_value = 2
        self.mlx.mlx_new_image.return_value = 3
        self.buffer = memoryview(bytearray(304 * 224 * 4))
        self.mlx.mlx_get_data_addr.return_value = (self.buffer, 32, 1216, 0)
        self.enterContext(patch.dict('sys.modules', {
            'mlx': SimpleNamespace(Mlx=Mock(return_value=self.mlx)),
        }))

    def test_startup_places_characters_registers_input_and_closes_once(self) -> None:
        self.viewer.run()
        self.assertEqual((self.viewer.canvas.width, self.viewer.canvas.height), (304, 224))
        player = self.viewer.game.player
        self.assertEqual(player.movement.center, self.viewer.canvas.cell_center(*player.movement.cell))
        self.assertEqual(self.mlx.mlx_hook.call_args_list, [
            call(2, 2, 1, self.viewer._on_key, None),
            call(2, 3, 2, self.viewer._on_key_release, None),
            call(2, 33, 0, self.viewer._close, None),
        ])
        self.mlx.mlx_loop.assert_called_once_with(1)
        self.mlx.mlx_destroy_image.assert_called_once_with(1, 3)
        self.mlx.mlx_destroy_window.assert_called_once_with(1, 2)
        self.viewer.audio.close.assert_called_once_with()
        self.assertTrue(self.viewer.closed)

    def test_failed_image_allocation_releases_the_window(self) -> None:
        self.mlx.mlx_new_image.return_value = None
        with self.assertRaisesRegex(RuntimeError, 'image creation failed'):
            self.viewer.run()
        self.mlx.mlx_destroy_window.assert_called_once_with(1, 2)
        self.mlx.mlx_destroy_image.assert_not_called()
        self.mlx.mlx_loop.assert_not_called()
        self.viewer.audio.close.assert_called_once_with()
        self.viewer._close()
        self.mlx.mlx_destroy_window.assert_called_once_with(1, 2)

    def test_failed_mlx_initialization_closes_audio_without_destroying_handles(self) -> None:
        self.mlx.mlx_init.return_value = None
        with self.assertRaisesRegex(RuntimeError, 'MLX initialization failed'):
            self.viewer.run()
        self.viewer.audio.close.assert_called_once_with()
        self.mlx.mlx_destroy_image.assert_not_called()
        self.mlx.mlx_destroy_window.assert_not_called()
        self.mlx.mlx_loop_exit.assert_not_called()

    def test_failed_window_allocation_closes_audio_without_destroying_missing_window(self) -> None:
        self.mlx.mlx_new_window.return_value = None
        with self.assertRaisesRegex(RuntimeError, 'window creation failed'):
            self.viewer.run()
        self.viewer.audio.close.assert_called_once_with()
        self.mlx.mlx_destroy_image.assert_not_called()
        self.mlx.mlx_destroy_window.assert_not_called()
        self.mlx.mlx_loop.assert_not_called()

    def test_layout_failure_before_window_allocation_still_closes_audio(self) -> None:
        self.mlx.mlx_get_screen_size.return_value = (0, 1, 1)
        with self.assertRaisesRegex(ValueError, 'maze is too large'):
            self.viewer.run()
        self.viewer.audio.close.assert_called_once_with()
        self.mlx.mlx_new_window.assert_not_called()
        self.mlx.mlx_destroy_image.assert_not_called()
        self.mlx.mlx_destroy_window.assert_not_called()

    def test_invalid_image_format_releases_allocated_resources(self) -> None:
        self.mlx.mlx_get_data_addr.return_value = (self.buffer, 24, 1216, 0)
        with self.assertRaisesRegex(RuntimeError, 'Unsupported MLX image format'):
            self.viewer.run()
        self.mlx.mlx_destroy_image.assert_called_once_with(1, 3)
        self.mlx.mlx_destroy_window.assert_called_once_with(1, 2)
        self.viewer.audio.close.assert_called_once_with()
        self.mlx.mlx_loop.assert_not_called()

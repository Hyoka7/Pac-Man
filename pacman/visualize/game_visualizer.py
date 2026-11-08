"""Adapt game state to the MLX window, events and rendering."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from mazegenerator import MazeGenerator

from pacman.audio.manager import AudioManager
from pacman.controls.keys import WindowAction
from pacman.game.game import Game
from pacman.game.pacgums import PacgumEatenEnum
from pacman.game.player import Player
from pacman.models import Config
from pacman.visualize.canvas import Canvas
from pacman.game.state import GameState
from pacman.visualize.gui import GUI
from pacman.visualize.layout import centered_start
from pacman.visualize.mlx_events import MlxEvent, MlxEventMask
from pacman.visualize.world_renderer import WorldRenderer

if TYPE_CHECKING:
    from mlx import Mlx


class GameVisualizer:
    """Own MLX resources, screen layout and presentation of the game."""

    mlx: Mlx
    mlx_pointer: int | None
    window_pointer: int | None
    image_pointer: int | None
    width: int
    height: int
    image_data: memoryview
    bytes_per_row: int
    pixel_format: int

    def __init__(
        self,
        generator: MazeGenerator,
        config: Config,
    ) -> None:
        """Connect game state to the GUI before opening a graphics window."""
        self.game = Game(generator, config)
        self.gui = GUI()
        self.world_renderer = WorldRenderer()
        self.audio = AudioManager()
        self.color_modes = [
            ((126, 249, 255), (255, 92, 138), (145, 255, 174)),
            ((89, 196, 255), (255, 204, 92), (77, 255, 218)),
            ((255, 167, 92), (255, 80, 120), (255, 231, 128)),
            ((255, 183, 213), (255, 92, 147), (204, 178, 255)),
            ((112, 224, 151), (255, 194, 92), (173, 255, 108)),
            ((0, 240, 255), (255, 45, 190), (247, 255, 0)),
            ((190, 168, 255), (255, 145, 200), (132, 224, 255)),
            ((255, 112, 67), (255, 213, 79), (255, 171, 145)),
            ((185, 230, 255), (110, 168, 255), (225, 255, 255)),
            ((128, 255, 214), (255, 148, 180), (211, 255, 140)),
            ((165, 148, 255), (255, 196, 82), (104, 214, 255)),
            ((224, 230, 238), (255, 105, 105), (112, 224, 178)),
        ]
        self.color_mode_index = 0
        self.mlx_pointer = None
        self.window_pointer = None
        self.image_pointer = None
        self.window_closed = True
        self.previous_frame_time = time.monotonic()

    def _draw(self, _param: object = None) -> None:
        """Compose the current game view into the image buffer."""
        del _param
        if self.window_closed:
            return
        self.canvas.clear_image()
        self.gui.draw_backdrop(self.canvas, self.game.state)
        if self.game.state in (
            GameState.Playing,
            GameState.Pause,
            GameState.Ready,
        ):
            self._draw_world()
            self._draw_hud()

        self._draw_screen()

        self.mlx.mlx_put_image_to_window(
            self.mlx_pointer, self.window_pointer, self.image_pointer, 0, 0
        )
        self.game.needs_redraw = False

    def _draw_screen(self) -> None:
        """Choose the UI renderer for the active screen."""
        renderers = {
            GameState.Home: self._draw_home,
            GameState.Instruction: self._draw_instruction,
            GameState.Ready: self._draw_ready,
            GameState.Ranking: self._draw_ranking,
            GameState.Confirm_Clear: self._draw_confirm_clear,
            GameState.GameOver: self._draw_gameover,
            GameState.Pause: self._draw_pause,
            GameState.Stage_Clear: self._draw_stage_clear,
            GameState.All_Clear: self._draw_all_clear,
        }
        renderer = renderers.get(self.game.state)
        if renderer is not None:
            renderer()

    def _draw_home(self) -> None:
        self.gui.home(
            self.canvas,
            self.width,
            self.height,
            self.game.score_manager.scores.scores,
            self.game.home_focusing,
        )

    def _draw_gameover(self) -> None:
        self.gui.gameover(
            self.canvas,
            self.width,
            self.height,
            self.game.player.score,
            self.game.player_name,
        )

    def _draw_instruction(self) -> None:
        self.gui.instruction(
            self.canvas,
            self.width,
            self.height,
        )

    def _draw_pause(self) -> None:
        self.gui.pause(
            self.canvas,
            self.width,
            self.height,
        )

    def _draw_ready(self) -> None:
        self.gui.ready(
            self.canvas,
            self.width,
            self.height,
        )

    def _draw_stage_clear(self) -> None:
        self.gui.stage_clear(
            self.canvas,
            self.width,
            self.height,
        )

    def _draw_ranking(self) -> None:
        self.gui.ranking(
            self.canvas,
            self.width,
            self.height,
            self.game.score_manager.scores.scores,
        )

    def _draw_all_clear(self) -> None:
        self.gui.all_clear(
            self.canvas,
            self.width,
            self.height,
            self.game.player.score,
            self.game.player_name,
        )

    def _draw_confirm_clear(self) -> None:
        self.gui.confirm_clear(self.canvas, self.width, self.height)

    def _draw_world(self) -> None:
        """Draw the maze, pacgums and characters into the current canvas."""
        wall_color, landmark_color, _ = self.color_modes[self.color_mode_index]
        self.world_renderer.draw_maze(
            self.game.maze, self.canvas, wall_color, landmark_color
        )
        self.world_renderer.draw_pacgums(self.game.pacgums, self.canvas)
        for ghost in self.game.ghosts:
            self.world_renderer.draw_ghost(
                ghost,
                self.canvas,
                self.game.player.is_invincible,
                self.game.player.invincible_remain,
            )
        self.world_renderer.draw_player(self.game.player, self.canvas)

    def _draw_hud(self) -> None:
        """Draw invincibility status and the gameplay score, lives and timer."""
        if self.game.player.is_invincible:
            bar_y = self.gui.bar_y
            self.gui.draw_invincible_bar(
                self.canvas,
                centered_start(self.width, self.gui.bar_width),
                bar_y,
                self.gui.bar_width,
                self.gui.bar_height,
                self.game.player.invincible_remain,
                Player.INVINCIBLE_DURATION,
            )
            self.gui.invincible_time(
                self.canvas,
                self.width,
                bar_y,
                self.game.player.invincible_remain,
            )
        if self.game.state in (GameState.Playing, GameState.Pause):
            self.gui.draw_stats(
                self.canvas,
                self.gui.hud_x,
                self.gui.hud_y,
                self.game.level,
                self.game.player.score,
                self.game.player.lives,
                self.game.remaining_time,
                self.game.cheat_enabled,
                score_multiplier=self.game.score_multiplier,
            )
        if self.game.cheat_enabled:
            self.gui.cheat_info(
                self.canvas,
                self.width,
                self.height,
            )

    def _close(self, _param: object = None) -> None:
        del _param
        if self.window_closed:
            return
        self.window_closed = True
        try:
            if self.mlx_pointer is not None:
                if self.image_pointer is not None:
                    self.mlx.mlx_destroy_image(self.mlx_pointer, self.image_pointer)
                if self.window_pointer is not None:
                    self.mlx.mlx_destroy_window(self.mlx_pointer, self.window_pointer)
                self.mlx.mlx_loop_exit(self.mlx_pointer)
        finally:
            self.audio.close()

    def _on_loop(self, _param: object = None) -> None:
        """Supply elapsed time to the game, then present its current state."""
        if self.window_closed:
            return
        current_time = time.monotonic()
        elapsed_seconds = current_time - self.previous_frame_time
        self.previous_frame_time = current_time
        self._place_pending_level()
        gum, eaten = self.game.update_game(elapsed_seconds, self.canvas)
        self._play_sound_effects(gum, eaten)
        self._update_bgm()
        if self.game.state == GameState.Playing or self.game.needs_redraw:
            self._draw()

    def _play_sound_effects(self, gum: PacgumEatenEnum, eaten: int) -> None:
        """Play independent pacgum and ghost events from the current update."""
        if gum == PacgumEatenEnum.Normal:
            self.audio.pacgum_sound()
        elif gum == PacgumEatenEnum.Super:
            self.audio.super_pacgum_sound()
        if eaten > 0:
            self.audio.eating_sound()

    def _update_bgm(self) -> None:
        """Select screen music while preserving the current track on overlays."""
        if self.game.state in (
            GameState.Home,
            GameState.Ranking,
            GameState.Instruction,
        ):
            self.audio.play_menu_bgm()
        elif self.game.state == GameState.Playing:
            self.audio.play_playing_bgm()
        elif self.game.state == GameState.GameOver:
            self.audio.play_gameover_bgm()

    def _on_key(self, key: int, _param: object = None) -> None:
        """Pass controls to the game and apply requested window actions."""
        if self.window_closed:
            return
        action = self.game.handle_key(key, self.canvas)
        if action == WindowAction.Close:
            self._close()
            return
        self._place_pending_level()
        if action == WindowAction.CycleColors:
            self.color_mode_index = (self.color_mode_index + 1) % len(self.color_modes)
            self._draw()

    def _on_key_release(self, key: int, _param: object = None) -> None:
        self.game.release_key(key)

    def _place_pending_level(self) -> None:
        """Apply screen geometry before the game places entities and pickups."""
        if not self.game.new_level_needs_placement:
            return
        self._update_layout()
        self.canvas.margin = self.margin
        self.canvas.cell_size = self.cell_size
        self.canvas.offset_x = self.offset_x
        self.canvas.offset_y = self.offset_y
        self.game.place_level(self.canvas)

    def display_next_level(self) -> None:
        self.game.next_level()
        self._place_pending_level()

    def restart_game_view(self) -> None:
        self.game.restart_game()
        self._place_pending_level()

    def _calc_cell_size(self) -> int:
        fit_x = (self.width - 2 * self.margin - 1) // self.game.maze.cols
        fit_y = (self.height - 2 * self.margin - 1) // self.game.maze.rows
        return min(fit_x, fit_y)

    def _update_layout(self) -> None:
        """Calculate cell size and center the maze in the fixed window."""
        self.gui.update_layout(self.width, self.height)
        self.margin = self.gui.maze_margin
        self.cell_size = self._calc_cell_size()
        if self.cell_size < 1:
            raise ValueError("maze is too large for the screen")
        self.offset_x = centered_start(
            self.width, self.cell_size * self.game.maze.cols + 1
        )
        self.offset_y = centered_start(
            self.height, self.cell_size * self.game.maze.rows + 1
        )

    def _open_window(self) -> None:
        """Initialize MLX and allocate the window and backing image."""
        from mlx import Mlx

        self.mlx = Mlx()
        self.mlx_pointer = self.mlx.mlx_init()
        if self.mlx_pointer is None:
            raise RuntimeError("MLX initialization failed")
        _, screen_width, screen_height = self.mlx.mlx_get_screen_size(self.mlx_pointer)
        window_margin = max(1, round(min(screen_width, screen_height) / 15))
        self.width = screen_width - window_margin
        self.height = screen_height - window_margin
        self._update_layout()
        self.window_pointer = self.mlx.mlx_new_window(
            self.mlx_pointer, self.width, self.height, "Pac-Man"
        )
        if self.window_pointer is None:
            raise RuntimeError("MLX window creation failed")
        self.image_pointer = self.mlx.mlx_new_image(
            self.mlx_pointer, self.width, self.height
        )
        if self.image_pointer is None:
            raise RuntimeError("MLX image creation failed")

    def _create_canvas(self) -> None:
        """Validate the backing image and expose it to drawing helpers."""
        (
            self.image_data,
            bits_per_pixel,
            self.bytes_per_row,
            self.pixel_format,
        ) = self.mlx.mlx_get_data_addr(self.image_pointer)
        if bits_per_pixel != 32 or self.pixel_format not in (0, 1):
            raise RuntimeError("Unsupported MLX image format")
        self.canvas = Canvas(
            self.width,
            self.height,
            self.cell_size,
            self.margin,
            self.image_data,
            self.bytes_per_row,
            self.pixel_format,
            self.offset_x,
            self.offset_y,
        )

    def _register_hooks(self) -> None:
        """Connect window events to this visualizer's callbacks."""
        self.mlx.mlx_loop_hook(self.mlx_pointer, self._on_loop, None)
        self.mlx.mlx_hook(
            self.window_pointer,
            MlxEvent.KEY_PRESS,
            MlxEventMask.KEY_PRESS,
            self._on_key,
            None,
        )
        self.mlx.mlx_hook(
            self.window_pointer,
            MlxEvent.KEY_RELEASE,
            MlxEventMask.KEY_RELEASE,
            self._on_key_release,
            None,
        )
        self.mlx.mlx_expose_hook(self.window_pointer, self._draw, None)
        self.mlx.mlx_hook(
            self.window_pointer,
            MlxEvent.WINDOW_CLOSE,
            MlxEventMask.NONE,
            self._close,
            None,
        )

    def start_visualization(self) -> None:
        """Open the window, place the game and release resources on exit."""
        self.mlx_pointer = self.window_pointer = self.image_pointer = None
        self.window_closed = False
        try:
            self._open_window()
            self._create_canvas()
            self.game.place_level(self.canvas)
            self._register_hooks()
            self._draw()
            self.previous_frame_time = time.monotonic()
            self.mlx.mlx_loop(self.mlx_pointer)
        finally:
            self._close()

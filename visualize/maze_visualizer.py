"""Adapt game state to the MLX window, events and rendering."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from mazegenerator import MazeGenerator

from models import Config

from .audio import AudioManager
from .controls import WindowAction
from .game import Game
from .gui import GUI, GUIStateEnum
from .pacgums import PacgumEatenEnum
from .visualizerutils import VisualizerUtils

if TYPE_CHECKING:
    from mlx import Mlx


class MazeVisualizer:
    """Own MLX resources, screen layout and presentation of the game."""

    m: Mlx
    p: int
    win: int
    img: int
    width: int
    height: int
    img_data: memoryview
    line_size: int
    img_format: int
    bytes_per_pixel: int

    def __init__(
        self,
        maze: list[list[int]],
        generator: MazeGenerator,
        config: Config,
    ) -> None:
        """Connect game state to the GUI before opening a graphics window."""
        self.game = Game(maze, generator, config)
        self.gui = GUI()
        self.audio = AudioManager()
        self.cmodes = [
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
        self.cm = 0
        self.closed = True
        self.last_time = time.monotonic()

    def _draw(self, _param: object = None) -> None:
        """Compose the current game view into the image buffer."""
        del _param
        if self.closed:
            return
        show_invincible_status = (
            self.game.state in (GUIStateEnum.Playing, GUIStateEnum.Pause)
            and self.game.player.is_invincible
        )
        self.canvas.clear_image()
        self.gui.draw_backdrop(self.canvas, self.game.state)
        if self.game.state == GUIStateEnum.Playing or self.game.state == GUIStateEnum.Pause:
            wall_color, landmark_color, _ = self.cmodes[self.cm]
            self.game.maze.draw(self.canvas, wall_color, landmark_color)
            self.game.pacgums.draw(self.canvas)
            for ghost in self.game.ghosts:
                ghost.draw(
                    self.canvas,
                    self.game.player.is_invincible,
                    self.game.player.invincible_remain,
                )
            self.game.player.draw(self.canvas)
        if self.game.state == GUIStateEnum.Pause:
            self.gui.draw_pause_background(self.canvas)
        bar_y = self.gui.bar_y
        if show_invincible_status:
            self.gui.draw_invincible_bar(
                self.canvas,
                (self.width - self.gui.bar_width) // 2,
                bar_y,
                self.gui.bar_width,
                self.gui.bar_height,
                self.game.player.invincible_remain,
                5.0,
            )

        if show_invincible_status:
            self.gui.invinsible_time(
                self.canvas,
                self.width,
                bar_y,
                self.game.player.invincible_remain,
            )

        if self.game.state == GUIStateEnum.Home:
            self.gui.home(
                self.canvas,
                self.width,
                self.height,
                self.game.score_manager.scores.scores,
                self.game.home_focusing,
            )
        elif self.game.state == GUIStateEnum.Instruction:
            self.gui.instruction(
                self.canvas,
                self.width,
                self.height,
            )
        elif self.game.state == GUIStateEnum.Playing or self.game.state == GUIStateEnum.Pause:
            self.gui.draw_stats(
                self.canvas,
                self.gui.hud_x,
                self.gui.hud_y,
                self.game.level,
                self.game.player.score,
                self.game.player.lives,
                self.game.remaining_time,
                self.game.cheat_enabled,
                auto_enabled=self.game.auto_enabled,
                score_multiplier=self.game.score_multiplier,
            )
        elif self.game.state == GUIStateEnum.Ranking:
            self.gui.ranking(
                self.canvas,
                self.width,
                self.height,
                self.game.score_manager.scores.scores,
            )
        elif self.game.state == GUIStateEnum.Confirm_Clear:
            self.gui.confirm_clear(self.canvas, self.width, self.height)
        if self.game.state == GUIStateEnum.GameOver:
            self.gui.gameover(
                self.canvas,
                self.width,
                self.height,
                self.game.player.score,
                self.game.player_name,
            )
        elif self.game.state == GUIStateEnum.Pause:
            self.gui.pause(
                self.canvas,
                self.width,
                self.height,
            )
        elif self.game.state == GUIStateEnum.Stage_Clear:
            self.gui.stage_clear(
                self.canvas,
                self.width,
                self.height,
            )
        elif self.game.state == GUIStateEnum.All_Clear:
            self.gui.all_clear(
                self.canvas,
                self.width,
                self.height,
                self.game.player.score,
                self.game.player_name,
            )

        self.m.mlx_put_image_to_window(self.p, self.win, self.img, 0, 0)
        self.game.needs_redraw = False

    def _close(self, _param: object = None) -> None:
        del _param
        if self.closed:
            return
        self.closed = True
        self.audio.close()
        self.m.mlx_destroy_image(self.p, self.img)
        self.m.mlx_destroy_window(self.p, self.win)
        self.m.mlx_loop_exit(self.p)

    def _on_loop(self, _param: object = None) -> None:
        """Supply elapsed time to the game, then present its current state."""
        now = time.monotonic()
        elapsed = now - self.last_time
        self.last_time = now
        if self.closed:
            return
        self._place_pending_level()
        gum, eaten = self.game.update(elapsed, self.canvas)
        if gum == PacgumEatenEnum.Normal:
            self.audio.pacgum_sound()
        elif gum == PacgumEatenEnum.Super:
            self.audio.super_pacgum_sound()
        if eaten > 0:
            self.audio.eating_sound()
        if self.game.state in (
            GUIStateEnum.Home,
            GUIStateEnum.Ranking,
            GUIStateEnum.Instruction,
        ):
            self.audio.play_menu_bgm()
        elif self.game.state == GUIStateEnum.Playing:
            self.audio.play_playing_bgm()
        elif self.game.state == GUIStateEnum.GameOver:
            self.audio.play_gameover_bgm()
        if self.game.state == GUIStateEnum.Playing or self.game.needs_redraw:
            self._draw()

    def _on_key(self, key: int, _param: object = None) -> None:
        """Pass controls to the game and apply requested window actions."""
        if self.closed:
            return
        action = self.game.handle_key(key, self.canvas)
        if action == WindowAction.Close:
            self._close()
            return
        self._place_pending_level()
        if action == WindowAction.CycleColors:
            self.cm = (self.cm + 1) % len(self.cmodes)
            self._draw()

    def _on_key_release(self, key: int, _param: object = None) -> None:
        self.game.release_key(key)

    def _place_pending_level(self) -> None:
        """Apply screen geometry before the game places entities and pickups."""
        if not self.game.level_needs_placement:
            return
        self._update_layout()
        self.canvas.margin = self.margin
        self.canvas.cell_size = self.cell_size
        self.canvas.offset_x = self.offset_x
        self.canvas.offset_y = self.offset_y
        self.game.place(self.canvas)

    def next_level(self) -> None:
        self.game.next_level()
        self._place_pending_level()

    def restart_game(self) -> None:
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
        self.offset_x = (self.width - (self.cell_size * self.game.maze.cols + 1)) // 2
        self.offset_y = (self.height - (self.cell_size * self.game.maze.rows + 1)) // 2

    def run(self) -> None:
        """Open the window and display the maze until it is closed."""
        from mlx import Mlx

        self.m = Mlx()
        self.p = self.m.mlx_init()
        if self.p is None:
            raise RuntimeError("MLX initialization failed")

        _, screen_width, screen_height = self.m.mlx_get_screen_size(self.p)
        window_gap = max(1, round(min(screen_width, screen_height) / 15))
        self.width = screen_width - window_gap
        self.height = screen_height - window_gap
        self._update_layout()
        self.win = self.m.mlx_new_window(self.p, self.width, self.height, "Maze Viewer")
        if self.win is None:
            raise RuntimeError("MLX window creation failed")
        self.img = self.m.mlx_new_image(self.p, self.width, self.height)
        if self.img is None:
            self.m.mlx_destroy_window(self.p, self.win)
            raise RuntimeError("MLX image creation failed")
        self.closed = False
        try:
            self.img_data, bpp, self.line_size, self.img_format = (
                self.m.mlx_get_data_addr(self.img)
            )
            self.bytes_per_pixel = bpp // 8
            if bpp != 32 or self.img_format not in (0, 1):
                raise RuntimeError("Unsupported MLX image format")
            self.canvas = VisualizerUtils(
                self.width,
                self.height,
                self.cell_size,
                self.margin,
                self.img_data,
                self.line_size,
                self.img_format,
                self.offset_x,
                self.offset_y,
            )
            self.game.place(self.canvas)
            self.m.mlx_loop_hook(self.p, self._on_loop, None)
            self.m.mlx_hook(self.win, 2, 1, self._on_key, None)
            self.m.mlx_hook(self.win, 3, 2, self._on_key_release, None)
            self.m.mlx_expose_hook(self.win, self._draw, None)
            self.m.mlx_hook(self.win, 33, 0, self._close, None)
            self._draw()
            self.last_time = time.monotonic()
            self.m.mlx_loop(self.p)
        finally:
            self._close()

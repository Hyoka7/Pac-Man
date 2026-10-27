"""Connect MLX lifecycle and events to the game components."""

from __future__ import annotations

import time
from enum import IntEnum
from typing import TYPE_CHECKING

from mazegenerator import MazeGenerator

from models import Config

from .cheating import CheatHandler
from .collision import Collision
from .ghost import Ghost
from .gui import GUI, GUIStateEnum
from .highscore import HighscoreManager, ScoreEntry
from .maze import Maze
from .pacgums import Pacgums
from .player import Player
from .strategy import BFSStrategy, RandomStrategy
from .visualizerutils import VisualizerUtils

if TYPE_CHECKING:
    from mlx import Mlx


class KeyEnum(IntEnum):
    A = 97
    C = 99
    D = 100
    F = 102
    H = 104
    I = 105
    K = 107
    L = 108
    M = 109
    N = 110
    P = 112
    R = 114
    S = 115
    T = 116
    W = 119
    Y = 121
    BACKSPACE = 65288
    ENTER = 65293
    ESC = 65307
    LEFT = 65361
    UP = 65362
    RIGHT = 65363
    DOWN = 65364
    SHIFT_L = 65505
    SHIFT_R = 65506



class MazeVisualizer:
    """Coordinate the window, input, updates and rendering."""

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
        """Create game components before opening a graphics window."""
        self.config = config
        self.maze = Maze(maze)
        self.player = Player(
            self.maze.central_cell(),
            self.config.lives,
            self.config.points_per_pacgum,
            self.config.points_per_super_pacgum,
        )
        self.pacgums = Pacgums(self.maze.rows, self.maze.cols)
        self.judge = Collision()
        self.score_manager = HighscoreManager(self.config.highscore_filename)
        self.gui = GUI()
        self.cheathandler = CheatHandler([ord(char) for char in "harnakam"])
        self.generator = generator
        self.ghosts: list[Ghost] = []
        self.ghosts.append(Ghost((0, 0), RandomStrategy(), (128, 128, 128)))
        self.ghosts.append(Ghost((0, self.maze.rows - 1), BFSStrategy()))
        self.ghosts.append(
            Ghost((self.maze.cols - 1, 0), BFSStrategy(), color=(0, 255, 0)),
        )
        self.ghosts.append(
            Ghost(
                (self.maze.cols - 1, self.maze.rows - 1),
                BFSStrategy(),
                color=(0, 0, 255),
            )
        )
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
        self.level = 1
        self.home_focusing = 0
        self.max_level = len(self.config.levels)
        self.remaining_time = self.config.levels[0].max_time
        self.closed = True
        self.needs_redraw = True
        self.cheat_enabled = False
        self.ghost_frozen = False
        self.state: GUIStateEnum = GUIStateEnum.Home
        self.last_time = time.monotonic()
        self.player_name = ""
        self.shift_keys: set[int] = set()

    def _draw(self, _param: object = None) -> None:
        """Compose the current game view into the image buffer."""
        del _param
        if self.closed:
            return
        show_invincible_status = (
            self.state in (GUIStateEnum.Playing, GUIStateEnum.Pause)
            and self.player.is_invincible
        )
        self.canvas.clear_image()
        self.gui.draw_backdrop(self.canvas, self.state)
        if self.state == GUIStateEnum.Playing or self.state == GUIStateEnum.Pause:
            wall_color, landmark_color, _ = self.cmodes[self.cm]
            self.maze.draw(self.canvas, wall_color, landmark_color)
            self.pacgums.draw(self.canvas)
            for ghost in self.ghosts:
                ghost.draw(
                    self.canvas,
                    self.player.is_invincible,
                    self.player.invincible_remain,
                )
            self.player.draw(self.canvas)
        if self.state == GUIStateEnum.Pause:
            self.gui.draw_pause_background(self.canvas)
        bar_y = self.gui.bar_y
        if show_invincible_status:
            self.gui.draw_invincible_bar(
                self.canvas,
                (self.width - self.gui.bar_width) // 2,
                bar_y,
                self.gui.bar_width,
                self.gui.bar_height,
                self.player.invincible_remain,
                5.0,
            )

        if show_invincible_status:
            self.gui.invinsible_time(
                self.canvas,
                self.width,
                bar_y,
                self.player.invincible_remain,
            )

        if self.state == GUIStateEnum.Home:
            self.gui.home(
                self.canvas,
                self.width,
                self.height,
                self.score_manager.scores.scores,
                self.home_focusing,
            )
        elif self.state == GUIStateEnum.Instruction:
            self.gui.instruction(
                self.canvas,
                self.width,
                self.height,
            )
        elif self.state == GUIStateEnum.Playing or self.state == GUIStateEnum.Pause:
            self.gui.draw_stats(
                self.canvas,
                self.gui.hud_x,
                self.gui.hud_y,
                self.level,
                self.player.score,
                self.player.lives,
                self.remaining_time,
                self.cheat_enabled,
            )
        elif self.state == GUIStateEnum.Ranking:
            self.gui.ranking(
                self.canvas,
                self.width,
                self.height,
                self.score_manager.scores.scores,
            )
        elif self.state == GUIStateEnum.Confirm_Clear:
            self.gui.confirm_clear(self.canvas, self.width, self.height)
        if self.state == GUIStateEnum.GameOver:
            self.gui.gameover(
                self.canvas,
                self.width,
                self.height,
                self.player.score,
                self.player_name,
            )
        elif self.state == GUIStateEnum.Pause:
            self.gui.pause(
                self.canvas,
                self.width,
                self.height,
            )
        elif self.state == GUIStateEnum.Stage_Clear:
            self.gui.stage_clear(
                self.canvas,
                self.width,
                self.height,
            )
        elif self.state == GUIStateEnum.All_Clear:
            self.gui.all_clear(
                self.canvas,
                self.width,
                self.height,
                self.player.score,
                self.player_name,
            )

        self.m.mlx_put_image_to_window(self.p, self.win, self.img, 0, 0)
        self.needs_redraw = False

    def _close(self, _param: object = None) -> None:
        del _param
        if self.closed:
            return
        self.closed = True
        self.m.mlx_destroy_image(self.p, self.img)
        self.m.mlx_destroy_window(self.p, self.win)
        self.m.mlx_loop_exit(self.p)

    def _respawn(self) -> None:
        self.player.reset(self.canvas)
        for ghost in self.ghosts:
            ghost.reset(self.canvas)

    def _on_loop(self, _param: object = None) -> None:
        """Update movement and mouth animation, then redraw the frame."""
        now = time.monotonic()
        elapsed = now - self.last_time
        self.last_time = now
        if self.closed:
            return
        if self.state == GUIStateEnum.Playing:
            self.remaining_time = max(self.remaining_time - elapsed, 0.0)
            self.player.update(elapsed, self.maze, self.canvas, self.pacgums)
            if len(self.pacgums) == 0:
                if self.level < self.max_level:
                    self.state = GUIStateEnum.Stage_Clear
                    self.needs_redraw = True
                else:
                    self.state = GUIStateEnum.All_Clear
                    self.needs_redraw = True
            elif self.remaining_time == 0.0:
                self.player.is_alive = False
                self.player.lives = 0
                self.state = GUIStateEnum.GameOver
                self.needs_redraw = True
            else:
                for ghost in self.ghosts:
                    if not self.ghost_frozen:
                        ghost.update(
                            elapsed,
                            self.maze,
                            self.canvas,
                            self.player.movement.cell,
                            self.player.is_invincible,
                        )
                    if ghost.respawn_remaining > 0.0:
                        continue
                    if self.player.is_alive and self.judge.is_collision(
                        self.player, ghost
                    ):
                        if not self.player.is_invincible:
                            print(f"YOU DIED BY {ghost.color}")
                            self.player.lives -= 1
                            if self.player.lives == 0:
                                self.player.is_alive = False
                                self.state = GUIStateEnum.GameOver
                                self.needs_redraw = True
                            else:
                                self._respawn()
                            break
                        else:
                            print(f"YOU EATEN {ghost.color}")
                            self.player.score += self.config.points_per_ghost
                            ghost.reset(self.canvas)
                            ghost.respawn_remaining = 5.0
                self.player.update_mouth(elapsed)
        if self.state == GUIStateEnum.Playing or self.needs_redraw:
            self._draw()

    def _on_key(self, key: int, _param: object = None) -> None:
        """Dispatch controls to the owning component."""
        if self.closed:
            return
        if key == KeyEnum.SHIFT_L or key == KeyEnum.SHIFT_R:
            self.shift_keys.add(key)
            return
        if key == KeyEnum.ESC:
            self._close()
            return
        if self.state == GUIStateEnum.Home:
            if key == KeyEnum.ENTER:
                if self.home_focusing == 0:
                    self.restart_game()
                elif self.home_focusing == 1:
                    self.state = GUIStateEnum.Instruction
                    self.needs_redraw = True
                elif self.home_focusing == 2:
                    self.state = GUIStateEnum.Ranking
                    self.needs_redraw = True
                elif self.home_focusing == 3:
                    self._close()
            elif key == KeyEnum.I:
                self.state = GUIStateEnum.Instruction
                self.needs_redraw = True
            elif key == KeyEnum.H:
                self.state = GUIStateEnum.Ranking
                self.needs_redraw = True
            elif key == KeyEnum.UP:
                self.home_focusing = (self.home_focusing - 1) % 4
                self.needs_redraw = True
            elif key == KeyEnum.DOWN:
                self.home_focusing = (self.home_focusing + 1) % 4
                self.needs_redraw = True
        elif self.state == GUIStateEnum.Ranking:
            if key == KeyEnum.ENTER:
                self.state = GUIStateEnum.Home
                self.needs_redraw = True
            elif key == KeyEnum.C:
                self.state = GUIStateEnum.Confirm_Clear
                self.needs_redraw = True
        elif self.state == GUIStateEnum.Instruction:
            if key == KeyEnum.ENTER:
                self.state = GUIStateEnum.Home
                self.needs_redraw = True
        elif self.state == GUIStateEnum.Confirm_Clear:
            if key == KeyEnum.Y:
                self.score_manager.clear()
                self.state = GUIStateEnum.Ranking
                self.needs_redraw = True
            elif key == KeyEnum.N:
                self.state = GUIStateEnum.Ranking
                self.needs_redraw = True
        elif self.state == GUIStateEnum.Playing:
            if self.cheathandler.consume(key):
                self.cheat_enabled = not self.cheat_enabled
                if not self.cheat_enabled:
                    self.ghost_frozen = False
                return
            if self.cheathandler.index > 0:
                return
            if key == KeyEnum.P:
                self.state = GUIStateEnum.Pause
                self.needs_redraw = True
            elif key in (99, 67):
                self.cm = (self.cm + 1) % len(self.cmodes)
                self._draw()
            elif key == KeyEnum.N and self.cheat_enabled:
                self.next_level()
            elif key == KeyEnum.F and self.cheat_enabled:
                self.ghost_frozen = not self.ghost_frozen
            elif key == KeyEnum.L and self.cheat_enabled:
                self.player.lives += 1
            elif key == KeyEnum.T and self.cheat_enabled:
                self.remaining_time += 10.0
            else:
                directions: dict[int, str] = {
                    KeyEnum.LEFT: "W",
                    KeyEnum.A: "W",
                    KeyEnum.UP: "N",
                    KeyEnum.W: "N",
                    KeyEnum.RIGHT: "E",
                    KeyEnum.D: "E",
                    KeyEnum.DOWN: "S",
                    KeyEnum.S: "S",
                }
                if key in directions:
                    self.player.request_move(directions[key], self.maze, self.canvas)

        elif self.state == GUIStateEnum.Pause:
            if key == KeyEnum.P:
                self.state = GUIStateEnum.Playing
                self.needs_redraw = True
            elif key == KeyEnum.H:
                self.state = GUIStateEnum.Home
                self.needs_redraw = True
        elif self.state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            if key == KeyEnum.ENTER:
                self.score_manager += ScoreEntry(
                    name=self.player_name if len(self.player_name) else "kyonaha",
                    score=self.player.score,
                )
                self.player_name = ""
                self.state = GUIStateEnum.Home
                self.needs_redraw = True
            elif key == KeyEnum.BACKSPACE:
                self.player_name = self.player_name[:-1]
                self.needs_redraw = True
            elif (
                0 <= key <= 128
                and (chr(key).isalnum() or chr(key) == " ")
                and len(self.player_name) < 10
            ):
                char = chr(key)
                if len(self.shift_keys):
                    self.player_name += char.upper()
                else:
                    self.player_name += char
                self.needs_redraw = True
        elif self.state == GUIStateEnum.Stage_Clear:
            self.next_level()

    def _on_key_release(self, key: int, _param: object = None) -> None:
        if key == KeyEnum.SHIFT_L or key == KeyEnum.SHIFT_R:
            self.shift_keys.discard(key)

    def regenerate_maze(self) -> None:
        new_conf = self.config.levels[self.level - 1]
        new_generator = MazeGenerator((new_conf.width, new_conf.height))
        self.generator = new_generator
        self.maze = Maze(self.generator.maze)
        self._update_layout()
        self.canvas.margin = self.margin
        self.canvas.cell_size = self.cell_size
        self.canvas.offset_x = self.offset_x
        self.canvas.offset_y = self.offset_y
        self.player.movement.initial_cell = self.maze.central_cell()
        corners = []
        corners.append((0, 0))
        corners.append((0, self.maze.rows - 1))
        corners.append((self.maze.cols - 1, 0))
        corners.append((self.maze.cols - 1, self.maze.rows - 1))
        for ghost, corner in zip(self.ghosts, corners):
            ghost.movement.initial_cell = corner

    def next_level(self) -> None:
        if self.level >= self.max_level:
            self.state = GUIStateEnum.All_Clear
            self.needs_redraw = True
            return
        self.level += 1
        self.regenerate_maze()
        self._respawn()
        self.pacgums.reset(
            self.maze,
            self.canvas,
            self.player.movement.cell,
        )
        self.remaining_time = self.config.levels[self.level - 1].max_time
        self.state = GUIStateEnum.Playing

    def restart_game(self) -> None:
        self.level = 1
        self.player.score = 0
        self.player.lives = self.player.initial_lives
        self.regenerate_maze()
        self._respawn()
        self.pacgums.reset(
            self.maze,
            self.canvas,
            self.player.movement.cell,
        )
        self.remaining_time = self.config.levels[0].max_time
        self.state = GUIStateEnum.Playing

    def _calc_cell_size(self) -> int:
        fit_x = (self.width - 2 * self.margin - 1) // self.maze.cols
        fit_y = (self.height - 2 * self.margin - 1) // self.maze.rows
        return min(fit_x, fit_y)

    def _update_layout(self) -> None:
        """Calculate cell size and center the maze in the fixed window."""
        self.gui.update_layout(self.width, self.height)
        self.margin = self.gui.maze_margin
        self.cell_size = self._calc_cell_size()
        if self.cell_size < 1:
            raise ValueError("maze is too large for the screen")
        self.offset_x = (self.width - (self.cell_size * self.maze.cols + 1)) // 2
        self.offset_y = (self.height - (self.cell_size * self.maze.rows + 1)) // 2

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
            self.player.place(self.canvas)
            for ghost in self.ghosts:
                ghost.place(self.canvas)
            self.pacgums.reset(self.maze, self.canvas, self.player.movement.cell)
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

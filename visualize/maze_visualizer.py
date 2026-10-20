"""Connect MLX lifecycle and events to the game components."""

from __future__ import annotations

import time
from enum import IntEnum

from mazegenerator import MazeGenerator

from .collision import Collision
from .ghost import Ghost
from .gui import GUI, GUIStateEnum
from .highscore import HighscoreManager, ScoreEntry
from .maze import Maze
from .pacgums import Pacgums
from .player import Player
from .strategy import BFSStrategy, RandomStrategy
from .visualizerutils import VisualizerUtils


class KeyEnum(IntEnum):
    A = 97
    D = 100
    N = 110
    P = 112
    R = 114
    S = 115
    W = 119
    BACKSPACE = 65288
    ENTER = 65293
    ESC = 65307
    LEFT = 65361
    UP = 65362
    RIGHT = 65363
    DOWN = 65364


class MazeVisualizer:
    """Coordinate the window, input, updates and rendering."""

    def __init__(self, maze: list[list[int]], generator: MazeGenerator) -> None:
        """Create game components before opening a graphics window."""
        self.maze = Maze(maze)
        self.player = Player(self.maze.central_cell())
        self.pacgums = Pacgums(self.maze.rows, self.maze.cols)
        self.judge = Collision()
        self.score_manager = HighscoreManager()
        self.gui = GUI()
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
        self.max_level = 10
        self.remaining_time = 90.0
        self.closed = True
        self.state: GUIStateEnum = GUIStateEnum.Home
        self.last_time = time.monotonic()
        self.player_name = ""

    def _draw(self, _param: object = None) -> None:
        """Compose the current game view into the image buffer."""
        del _param
        if self.closed:
            return
        self.canvas.clear_image()
        if self.state == GUIStateEnum.Playing or self.state == GUIStateEnum.Pause:
            wall_color, landmark_color, _ = self.cmodes[self.cm]
            self.maze.draw(self.canvas, wall_color, landmark_color)
            self.pacgums.draw(self.canvas)
            for ghost in self.ghosts:
                ghost.draw(self.canvas, self.player.is_invincible)
            self.player.draw(self.canvas)
        if self.state == GUIStateEnum.Pause:
            self.gui.background(
                self.canvas,
                self.width // 2 - 90,
                self.height // 2 - 30,
                180,
                60,
            )
        if self.player.is_invincible:
            self.gui.draw_invincible_bar(
                self.canvas,
                self.width // 2 - 100,
                self.height - 40,
                200,
                10,
                self.player.invincible_remain,
                5.0,
            )
        self.m.mlx_put_image_to_window(self.p, self.win, self.img, 0, 0)

        if self.player.is_invincible:
            self.gui.invinsible_time(
                self.m,
                self.p,
                self.win,
                self.width,
                self.height,
                self.player.invincible_remain,
            )

        if self.state == GUIStateEnum.Home:
            self.gui.home(
                self.m,
                self.p,
                self.win,
                self.width,
                self.height,
                self.score_manager.scores.scores,
            )
        elif self.state == GUIStateEnum.Playing or self.state == GUIStateEnum.Pause:
            self.gui.draw_stats(
                self.m,
                self.p,
                self.win,
                20,
                15,
                self.level,
                self.player.score,
                self.player.lives,
                self.remaining_time,
            )
        if self.state == GUIStateEnum.GameOver:
            self.gui.gameover(
                self.m,
                self.p,
                self.win,
                self.width,
                self.height,
                self.player.score,
                self.player_name,
            )
        elif self.state == GUIStateEnum.Pause:
            self.gui.pause(
                self.m,
                self.p,
                self.win,
                self.width,
                self.height,
            )
        elif self.state == GUIStateEnum.Stage_Clear:
            self.gui.stage_clear(
                self.m,
                self.p,
                self.win,
                self.width,
                self.height,
            )
        elif self.state == GUIStateEnum.All_Clear:
            self.gui.all_clear(
                self.m,
                self.p,
                self.win,
                self.width,
                self.height,
                self.player.score,
                self.player_name,
            )

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
                else:
                    self.state = GUIStateEnum.All_Clear
            elif self.remaining_time == 0.0:
                self.player.is_alive = False
                self.player.lives = 0
                self.state = GUIStateEnum.GameOver
            else:
                for ghost in self.ghosts:
                    ghost.update(
                        elapsed,
                        self.maze,
                        self.canvas,
                        self.player.movement.cell,
                        self.player.is_invincible,
                    )
                    if self.player.is_alive and self.judge.is_collision(
                        self.player, ghost
                    ):
                        if not self.player.is_invincible:
                            print(f"YOU DIED BY {ghost.color}")
                            self.player.lives -= 1
                            if self.player.lives == 0:
                                self.player.is_alive = False
                                self.state = GUIStateEnum.GameOver
                            else:
                                self._respawn()
                            break
                        else:
                            print(f"YOU EATEN {ghost.color}")
                            self.player.score += 200
                            ghost.reset(self.canvas)
                self.player.update_mouth(elapsed)
        self._draw()

    def _on_key(self, key: int, _param: object = None) -> None:
        """Dispatch controls to the owning component."""
        if self.closed:
            return
        if key == KeyEnum.ESC:
            self._close()
            return
        if self.state == GUIStateEnum.Home:
            if key == KeyEnum.ENTER:
                self.restart_game()
        elif self.state == GUIStateEnum.Playing:
            if key == KeyEnum.P:
                self.state = GUIStateEnum.Pause
            elif key in (99, 67):
                self.cm = (self.cm + 1) % len(self.cmodes)
                self._draw()
            elif key == KeyEnum.N:
                self.next_level()
            else:
                directions = {
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
        elif self.state in (GUIStateEnum.GameOver, GUIStateEnum.All_Clear):
            if key == KeyEnum.ENTER:
                self.score_manager += ScoreEntry(
                    name=self.player_name, score=self.player.score
                )
                self.player_name = ""
                self.state = GUIStateEnum.Home
            elif key == KeyEnum.BACKSPACE:
                self.player_name = self.player_name[:-1]
            elif 0 <= key < 128 and chr(key).isalnum():
                self.player_name += chr(key)
        elif self.state == GUIStateEnum.Stage_Clear:
            self.next_level()

    def regenerate_maze(self) -> None:
        self.generator.generate()
        self.maze = Maze(self.generator.maze)
        self.player.movement.initial_cell = self.maze.central_cell()

    def next_level(self) -> None:
        self.level += 1
        self.regenerate_maze()
        self._respawn()
        self.pacgums.reset(
            self.maze,
            self.canvas,
            self.player.movement.cell,
        )
        self.remaining_time = 90.0
        self.state = GUIStateEnum.Playing

    def restart_game(self) -> None:
        self.level = 1
        self.player.score = 0
        self.player.lives = 3
        self.regenerate_maze()
        self._respawn()
        self.pacgums.reset(
            self.maze,
            self.canvas,
            self.player.movement.cell,
        )
        self.remaining_time = 90.0
        self.state = GUIStateEnum.Playing

    def run(self) -> None:
        """Open the window and display the maze until it is closed."""
        from mlx import Mlx

        self.m = Mlx()
        self.p = self.m.mlx_init()
        if self.p is None:
            raise RuntimeError("MLX initialization failed")

        _, screen_width, screen_height = self.m.mlx_get_screen_size(self.p)
        self.margin = 100
        self.cell_size = min(
            32,
            (screen_width - 100 - 2 * self.margin - 1) // self.maze.cols,
            (screen_height - 100 - 2 * self.margin - 1) // self.maze.rows,
        )

        if self.cell_size < 1:
            raise ValueError("maze is too large for the screen")
        self.width = self.maze.cols * self.cell_size + 2 * self.margin + 1
        self.height = self.maze.rows * self.cell_size + 2 * self.margin + 1
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
            )
            self.player.place(self.canvas)
            for ghost in self.ghosts:
                ghost.place(self.canvas)
            self.pacgums.reset(self.maze, self.canvas, self.player.movement.cell)
            self.m.mlx_loop_hook(self.p, self._on_loop, None)
            self.m.mlx_hook(self.win, 2, 1, self._on_key, None)
            self.m.mlx_expose_hook(self.win, self._draw, None)
            self.m.mlx_hook(self.win, 33, 0, self._close, None)
            self._draw()
            self.last_time = time.monotonic()
            self.m.mlx_loop(self.p)
        finally:
            self._close()

"""Game progression, input decisions and rules, independent of MLX lifecycle."""

from mazegenerator import MazeGenerator

from models import Config

from .auto_player import AutoPlayer
from .cheating import CheatHandler
from .collision import Collision
from .controls import KeyEnum, WindowAction
from .game_state import GUIStateEnum
from .ghost import Ghost
from .highscore import HighscoreManager, ScoreEntry
from .maze import Maze
from .pacgums import PacgumEatenEnum, Pacgums
from .player import Player
from .strategy import BFSStrategy, RandomStrategy
from .visualizerutils import VisualizerUtils


class Game:
    """Own one game's state, rules and level lifecycle."""

    def __init__(
        self,
        maze: list[list[int]],
        generator: MazeGenerator,
        config: Config,
    ) -> None:
        """Own game rules and state without opening a graphics window."""
        self.config = config
        self.pacgum_points = {
            PacgumEatenEnum.Normal: config.points_per_pacgum,
            PacgumEatenEnum.Super: config.points_per_super_pacgum,
        }
        self.ghost_points = config.points_per_ghost
        self.score_multiplier = 1
        self.maze = Maze(maze)
        self.player = Player(
            self.maze.central_cell(),
            self.config.lives,
        )
        self.pacgums = Pacgums(self.maze.rows, self.maze.cols)
        self.judge = Collision()
        self.score_manager = HighscoreManager(self.config.highscore_filename)
        self.cheathandler = CheatHandler([ord(char) for char in "3111696"])
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
        self.level = 1
        self.home_focusing = 0
        self.max_level = len(self.config.levels)
        self.remaining_time = self.config.levels[0].max_time
        self.needs_redraw = True
        self.cheat_enabled = False
        self.auto_enabled = False
        self.auto_player = AutoPlayer()
        self.ghost_frozen = False
        self.state: GUIStateEnum = GUIStateEnum.Home
        self.player_name = ""
        self.shift_keys: set[int] = set()
        self.level_needs_placement = False
        self.no_collision = False

    def place(self, canvas: VisualizerUtils) -> None:
        """Place a new level after the renderer has updated the canvas layout."""
        self.respawn(canvas)
        self.pacgums.reset(self.maze, canvas, self.player.movement.cell)
        self.level_needs_placement = False

    def respawn(self, canvas: VisualizerUtils) -> None:
        self.player.reset(canvas)
        for ghost in self.ghosts:
            ghost.reset(canvas)

    def update(
        self, elapsed: float, canvas: VisualizerUtils
    ) -> tuple[PacgumEatenEnum, int]:
        """Advance gameplay by the supplied elapsed seconds; paused states stay still."""
        eaten = PacgumEatenEnum.Neither
        ghost_eaten = 0
        if self.state == GUIStateEnum.Playing:
            self.remaining_time = max(self.remaining_time - elapsed, 0.0)
            if self.auto_enabled:
                eaten = self.player.update(
                    elapsed,
                    self.maze,
                    canvas,
                    self.pacgums,
                    choose_auto_direction=lambda: self._choose_auto_direction(canvas),
                )
            else:
                eaten = self.player.update(elapsed, self.maze, canvas, self.pacgums)
            points = self.pacgum_points.get(eaten, 0)
            if points:
                self.player.score += points * self.score_multiplier
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
                            canvas,
                            self.player.movement.cell,
                            self.player.is_invincible,
                        )
                    if ghost.respawn_remaining > 0.0:
                        continue
                    if self.player.is_alive and self.judge.is_collision(
                        self.player, ghost
                    ):
                        if not self.player.is_invincible:
                            if self.no_collision:
                                continue
                            self.player.lives -= 1

                            if self.player.lives == 0:
                                self.player.is_alive = False
                                self.state = GUIStateEnum.GameOver
                                self.needs_redraw = True
                            else:
                                self.respawn(canvas)
                            break
                        else:
                            self.player.score += (
                                self.ghost_points * self.score_multiplier
                            )
                            ghost_eaten += 1
                            ghost.reset(canvas)
                            ghost.respawn_remaining = 5.0
                self.player.update_mouth(elapsed)
        return eaten, ghost_eaten

    def _choose_auto_direction(self, canvas: VisualizerUtils) -> str | None:
        return self.auto_player.choose_direction(
            self.maze,
            self.player,
            self.pacgums,
            self.ghosts,
            canvas,
            ghosts_frozen=self.ghost_frozen,
        )

    def handle_key(self, key: int, canvas: VisualizerUtils) -> WindowAction | None:
        """Dispatch controls to the owning component."""
        if key == KeyEnum.SHIFT_L or key == KeyEnum.SHIFT_R:
            self.shift_keys.add(key)
            return
        if key == KeyEnum.ESC:
            return WindowAction.Close
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
                    return WindowAction.Close
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
                    self.no_collision = False
                    self.auto_enabled = False
                    self.score_multiplier = 1
                    self.player.movement.wallhack = False
                return
            if self.cheathandler.index > 0:
                return
            if key == KeyEnum.P:
                self.state = GUIStateEnum.Pause
                self.needs_redraw = True
            elif key in (99, 67):
                return WindowAction.CycleColors
            elif key == KeyEnum.N and self.cheat_enabled:
                self.next_level()
            elif key == KeyEnum.F and self.cheat_enabled:
                self.ghost_frozen = not self.ghost_frozen
            elif key == KeyEnum.L and self.cheat_enabled:
                self.player.lives += 1
            elif key == KeyEnum.T and self.cheat_enabled:
                self.remaining_time += 10.0
            elif key == KeyEnum.O and self.cheat_enabled:
                self.auto_enabled = not self.auto_enabled
                self.player.reserved_move = None
            elif key == KeyEnum.X and self.cheat_enabled:
                self.score_multiplier = 10 if self.score_multiplier == 1 else 1
            elif key == KeyEnum.H and self.cheat_enabled:
                self.player.movement.wallhack = not self.player.movement.wallhack
            elif key == KeyEnum.V and self.cheat_enabled:
                self.player.movement.speed = (
                    8 if self.player.movement.speed == 16 else 16
                )
            elif key == KeyEnum.K and self.cheat_enabled:
                self.no_collision = not self.no_collision
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
                    self.auto_enabled = False
                    self.player.request_move(directions[key], self.maze, canvas)

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

    def release_key(self, key: int) -> None:
        if key == KeyEnum.SHIFT_L or key == KeyEnum.SHIFT_R:
            self.shift_keys.discard(key)

    def regenerate_maze(self) -> None:
        """Prepare the maze and spawn cells; place it after screen layout updates."""
        new_conf = self.config.levels[self.level - 1]
        new_generator = MazeGenerator((new_conf.width, new_conf.height))
        self.generator = new_generator
        self.maze = Maze(self.generator.maze)
        self.level_needs_placement = True
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
        self.remaining_time = self.config.levels[self.level - 1].max_time
        self.state = GUIStateEnum.Playing
        self.needs_redraw = True

    def restart_game(self) -> None:
        self.auto_enabled = False
        self.no_collision = False
        self.score_multiplier = 1
        self.player.movement.wallhack = False
        self.level = 1
        self.player.score = 0
        self.player.lives = self.player.initial_lives
        self.regenerate_maze()
        self.remaining_time = self.config.levels[0].max_time
        self.state = GUIStateEnum.Playing
        self.needs_redraw = True

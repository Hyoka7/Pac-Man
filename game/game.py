"""Game progression, input decisions and rules, independent of MLX lifecycle."""

from mazegenerator import MazeGenerator

from models import Config

from game.auto_player import AutoPlayer
from controls.cheating import CheatHandler
from game.collision import Collision
from controls.keys import WindowAction
from controls.game_input import handle_key as handle_game_key
from controls.game_input import release_key as release_game_key
from game.state import GUIStateEnum
from game.ghost import Ghost
from storage.highscore import HighscoreManager, ScoreEntry
from game.maze import Maze
from game.pacgums import PacgumEatenEnum, Pacgums
from game.player import Player
from game.strategy import AmbushStrategy, BFSStrategy, InkyStrategy, ReverseAmbushStrategy
from visualize.visualizerutils import VisualizerUtils


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
        self.ghosts = self._create_ghosts()
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
        self,
        elapsed: float,
        canvas: VisualizerUtils,
    ) -> tuple[PacgumEatenEnum, int]:
        """Advance gameplay and return pacgum and ghost-eating events."""
        if self.state != GUIStateEnum.Playing:
            return PacgumEatenEnum.Neither, 0
        self.remaining_time = max(self.remaining_time - elapsed, 0.0)
        eaten = self._update_player(elapsed, canvas)
        if self._check_level_end():
            return eaten, 0
        ghost_eaten = self._update_ghosts(elapsed, canvas)
        self.player.update_mouth(elapsed)
        return eaten, ghost_eaten

    def _update_player(
        self,
        elapsed: float,
        canvas: VisualizerUtils,
    ) -> PacgumEatenEnum:
        """Move the player and award points for consumed pacgums."""
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
        return eaten

    def _check_level_end(self) -> bool:
        """Resolve clear before timeout; return whether gameplay has ended."""
        if len(self.pacgums) == 0:
            self.state = (
                GUIStateEnum.Stage_Clear
                if self.level < self.max_level
                else GUIStateEnum.All_Clear
            )
        elif self.remaining_time == 0.0:
            self.player.is_alive = False
            self.player.lives = 0
            self.state = GUIStateEnum.GameOver
        else:
            return False
        self.needs_redraw = True
        return True

    def _update_ghosts(self, elapsed: float, canvas: VisualizerUtils) -> int:
        """Move ghosts, resolve contacts and return the number eaten."""
        ghost_eaten = 0
        red_pos = next(
            (
                ghost.cell
                for ghost in self.ghosts
                if type(ghost.strategy) is BFSStrategy
            ),
            None,
        )
        for ghost in self.ghosts:
            if not self.ghost_frozen:
                ghost.update(
                    elapsed,
                    self.maze,
                    canvas,
                    self.player.movement.cell,
                    self.player.movement.direction,
                    self.player.is_invincible,
                    red_pos=red_pos,
                )
            if ghost.respawn_remaining > 0.0:
                continue
            if not self.player.is_alive or not self.judge.is_collision(
                self.player, ghost
            ):
                continue
            if self.player.is_invincible:
                self._eat_ghost(ghost, canvas)
                ghost_eaten += 1
            elif not self.no_collision:
                self._handle_player_hit(canvas)
                break
        return ghost_eaten

    def _eat_ghost(self, ghost: Ghost, canvas: VisualizerUtils) -> None:
        """Award ghost points and begin its respawn wait."""
        self.player.score += self.ghost_points * self.score_multiplier
        ghost.reset(canvas)
        ghost.respawn_remaining = 5.0

    def _handle_player_hit(self, canvas: VisualizerUtils) -> None:
        """Lose one life, then enter GameOver or wait at the spawn positions."""
        self.player.lives -= 1
        if self.player.lives == 0:
            self.player.is_alive = False
            self.state = GUIStateEnum.GameOver
        else:
            self.respawn(canvas)
            self.state = GUIStateEnum.Ready
        self.needs_redraw = True

    def _choose_auto_direction(self, canvas: VisualizerUtils) -> str | None:
        return self.auto_player.choose_direction(
            self.maze,
            self.player,
            self.pacgums,
            self.ghosts,
            canvas,
            ghosts_frozen=self.ghost_frozen,
        )

    def set_state(self, state: GUIStateEnum) -> None:
        """Change the active screen and request its next redraw."""
        self.state = state
        self.needs_redraw = True

    def handle_key(self, key: int, canvas: VisualizerUtils) -> WindowAction | None:
        """Delegate keyboard interpretation to the input module."""
        return handle_game_key(self, key, canvas)

    def submit_score(self) -> None:
        """Save the result, clear the entered name and return to Home."""
        self.score_manager += ScoreEntry(
            name=self.player_name if len(self.player_name) else "kyonaha",
            score=self.player.score,
        )
        self.player_name = ""
        self.set_state(GUIStateEnum.Home)

    def release_key(self, key: int) -> None:
        release_game_key(self, key)

    def regenerate_maze(self) -> None:
        """Prepare the maze and spawn cells; place it after screen layout updates."""
        new_conf = self.config.levels[self.level - 1]
        new_generator = MazeGenerator((new_conf.width, new_conf.height))
        self.generator = new_generator
        self.maze = Maze(self.generator.maze)
        self.level_needs_placement = True
        self.player.movement.initial_cell = self.maze.central_cell()
        for ghost, corner in zip(self.ghosts, self._ghost_spawn_cells()):
            ghost.movement.initial_cell = corner

    def _create_ghosts(self) -> list[Ghost]:
        """Create the team with its existing strategies, colors and spawn order."""
        corners = self._ghost_spawn_cells()
        return [
            Ghost(corners[0], InkyStrategy(), color=(0, 255, 255)),
            Ghost(corners[1], BFSStrategy()),
            Ghost(corners[2], AmbushStrategy(), color=(0, 255, 0)),
            Ghost(corners[3], ReverseAmbushStrategy(), color=(0, 0, 255)),
        ]

    def _ghost_spawn_cells(self) -> tuple[tuple[int, int], ...]:
        """Return spawn corners in the same order as the ghost team."""
        return (
            (0, 0),
            (0, self.maze.rows - 1),
            (self.maze.cols - 1, 0),
            (self.maze.cols - 1, self.maze.rows - 1),
        )

    def _prepare_level(self, state: GUIStateEnum) -> None:
        """Generate the selected level and initialize its timer and screen state."""
        self.regenerate_maze()
        self.remaining_time = self.config.levels[self.level - 1].max_time
        self.set_state(state)

    def next_level(self) -> None:
        if self.level >= self.max_level:
            self.set_state(GUIStateEnum.All_Clear)
            return
        self.level += 1
        self._prepare_level(GUIStateEnum.Playing)

    def restart_game(self) -> None:
        self.auto_enabled = False
        self.no_collision = False
        self.score_multiplier = 1
        self.player.movement.wallhack = False
        self.level = 1
        self.player.score = 0
        self.player.lives = self.player.initial_lives
        self._prepare_level(GUIStateEnum.Ready)

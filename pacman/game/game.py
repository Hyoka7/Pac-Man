"""Game progression, input decisions and rules, independent of MLX lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mazegenerator import MazeGenerator

from pacman.types import CellPosition
from pacman.controls.cheating import CheatHandler
from pacman.controls.game_input import dispatch_key
from pacman.controls.game_input import release_key as release_game_key
from pacman.controls.keys import WindowAction
from pacman.game.collision import Collision
from pacman.game.ghost import Ghost, GhostRole
from pacman.game.maze import Maze
from pacman.game.pacgums import PacgumEatenEnum, Pacgums
from pacman.game.player import Player
from pacman.game.state import GameState
from pacman.game.strategy import (
    AmbushStrategy,
    BFSStrategy,
    InkyStrategy,
    ReverseAmbushStrategy,
)
from pacman.models import Config
from pacman.storage.highscore import HighscoreManager, ScoreEntry

if TYPE_CHECKING:
    from pacman.visualize.canvas import Canvas


class Game:
    """Own one game's state, rules and level lifecycle."""

    def __init__(
        self,
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
        self.maze = Maze(generator.maze)
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
        self.ghost_frozen = False
        self.state: GameState = GameState.Home
        self.player_name = ""
        self.shift_keys: set[int] = set()
        self.new_level_needs_placement = False
        self.no_collision = False

    def place_level(self, canvas: Canvas) -> None:
        """Place a new level after the renderer has updated the canvas layout."""
        self.respawn(canvas)
        self.pacgums.reset_pacgums(self.maze, self.player.movement.cell)
        self.new_level_needs_placement = False

    def respawn(self, canvas: Canvas) -> None:
        self.player.reset_player(canvas)
        for ghost in self.ghosts:
            ghost.reset_ghost(canvas)

    def update_game(
        self,
        elapsed: float,
        canvas: Canvas,
    ) -> tuple[PacgumEatenEnum, int]:
        """Advance gameplay and return pacgum and ghost-eating events."""
        if self.state != GameState.Playing:
            return PacgumEatenEnum.Neither, 0
        self.remaining_time = max(self.remaining_time - elapsed, 0.0)
        gum_eaten = self._update_player(elapsed, canvas)
        if self._check_level_end():
            return gum_eaten, 0
        ghost_eaten = self._update_ghosts(elapsed, canvas)
        self.player.update_mouth(elapsed)
        return gum_eaten, ghost_eaten

    def _update_player(
        self,
        elapsed: float,
        canvas: Canvas,
    ) -> PacgumEatenEnum:
        """Move the player and award points for consumed pacgums."""
        eaten = self.player.update_player(elapsed, self.maze, canvas, self.pacgums)
        points = self.pacgum_points.get(eaten, 0)
        if points:
            self.player.score += points * self.score_multiplier
        return eaten

    def _check_level_end(self) -> bool:
        """Resolve clear before timeout; return whether gameplay has ended."""
        if len(self.pacgums) == 0:
            state = (
                GameState.Stage_Clear
                if self.level < self.max_level
                else GameState.All_Clear
            )
        elif self.remaining_time == 0.0:
            self.player.is_alive = False
            self.player.lives = 0
            state = GameState.GameOver
        else:
            return False
        self.set_state(state)
        return True

    def _update_ghosts(self, elapsed: float, canvas: Canvas) -> int:
        """Move ghosts, resolve contacts and return the number eaten."""
        ghost_eaten = 0
        red_pos = next(
            (ghost.cell for ghost in self.ghosts if ghost.role == GhostRole.RED),
            None,
        )
        for ghost in self.ghosts:
            if not self.ghost_frozen:
                ghost.update_ghost(
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
            if not self.judge.is_collision(self.player, ghost):
                continue
            if self.player.is_invincible:
                self._eat_ghost(ghost, canvas)
                ghost_eaten += 1
            elif not self.no_collision:
                self._handle_player_hit(canvas)
                break
        return ghost_eaten

    def _eat_ghost(self, ghost: Ghost, canvas: Canvas) -> None:
        """Award ghost points and begin its respawn wait."""
        self.player.score += self.ghost_points * self.score_multiplier
        ghost.reset_ghost(canvas)
        ghost.respawn_remaining = Ghost.RESPAWN_DELAY

    def _handle_player_hit(self, canvas: Canvas) -> None:
        """Lose one life, then enter GameOver or wait at the spawn positions."""
        self.player.lives -= 1
        if self.player.lives == 0:
            self.player.is_alive = False
            self.set_state(GameState.GameOver)
        else:
            self.respawn(canvas)
            self.set_state(GameState.Ready)

    def set_state(self, state: GameState) -> None:
        """Change the active screen and request its next redraw."""
        self.state = state
        self.needs_redraw = True

    def handle_key(self, key: int, canvas: Canvas) -> WindowAction | None:
        """Delegate keyboard interpretation to the input module."""
        return dispatch_key(self, key, canvas)

    def submit_score(self) -> None:
        """Save the result, clear the entered name and return to Home."""
        self.score_manager += ScoreEntry(
            name=self.player_name if len(self.player_name) else "kyonaha",
            score=self.player.score,
        )
        self.player_name = ""
        self.set_state(GameState.Home)

    def release_key(self, key: int) -> None:
        release_game_key(self, key)

    def regenerate_maze(self) -> None:
        """Prepare the maze and spawn cells; place it after screen layout updates."""
        new_conf = self.config.levels[self.level - 1]
        maze_seed = self.config.seed if self.level == 1 else 0
        new_generator = MazeGenerator((new_conf.width, new_conf.height), seed=maze_seed)
        self.generator = new_generator
        self.maze = Maze(self.generator.maze)
        self.new_level_needs_placement = True
        self.player.movement.initial_cell = self.maze.central_cell()
        for ghost, corner in zip(self.ghosts, self._ghost_spawn_cells()):
            ghost.movement.initial_cell = corner

    def _create_ghosts(self) -> list[Ghost]:
        """Create the team with its existing strategies, colors and spawn order."""
        corners = self._ghost_spawn_cells()
        return [
            Ghost(corners[0], InkyStrategy(), color=(0, 255, 255), role=GhostRole.CYAN),
            Ghost(corners[1], BFSStrategy(), role=GhostRole.RED),
            Ghost(
                corners[2], AmbushStrategy(), color=(0, 255, 0), role=GhostRole.GREEN
            ),
            Ghost(
                corners[3],
                ReverseAmbushStrategy(),
                color=(0, 0, 255),
                role=GhostRole.BLUE,
            ),
        ]

    def _ghost_spawn_cells(self) -> tuple[CellPosition, ...]:
        """Return spawn corners in the same order as the ghost team."""
        return (
            (0, 0),
            (0, self.maze.rows - 1),
            (self.maze.cols - 1, 0),
            (self.maze.cols - 1, self.maze.rows - 1),
        )

    def _prepare_level(self, state: GameState) -> None:
        """Generate the selected level and initialize its timer and screen state."""
        self.regenerate_maze()
        self.remaining_time = self.config.levels[self.level - 1].max_time
        self.set_state(state)

    def next_level(self) -> None:
        if self.level >= self.max_level:
            self.set_state(GameState.All_Clear)
            return
        self.level += 1
        self._prepare_level(GameState.Playing)

    def restart_game(self) -> None:
        self.ghost_frozen = False
        self.no_collision = False
        self.score_multiplier = 1
        self.player.movement.wallhack = False
        self.player.movement.speed = Player.DEFAULT_SPEED
        self.level = 1
        self.player.score = 0
        self.player.lives = self.player.initial_lives
        self._prepare_level(GameState.Ready)

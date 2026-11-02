"""Translate keyboard input into game actions for each screen state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controls.keys import KeyEnum, MOVEMENT_DIRECTIONS, WindowAction
from game.state import GUIStateEnum
from visualize.visualizerutils import VisualizerUtils

if TYPE_CHECKING:
    from game.game import Game


def handle_key(game: Game, key: int, canvas: VisualizerUtils) -> WindowAction | None:
    """Handle common controls, then dispatch to the current state's handler."""
    if key in (KeyEnum.SHIFT_L, KeyEnum.SHIFT_R):
        game.shift_keys.add(key)
        return
    if key == KeyEnum.ESC:
        return WindowAction.Close
    handlers = {
        GUIStateEnum.Home: _handle_home_key,
        GUIStateEnum.Ranking: _handle_ranking_key,
        GUIStateEnum.Instruction: _handle_instruction_key,
        GUIStateEnum.Confirm_Clear: _handle_confirm_clear_key,
        GUIStateEnum.Playing: _handle_playing_key,
        GUIStateEnum.Ready: _handle_ready_key,
        GUIStateEnum.Pause: _handle_pause_key,
        GUIStateEnum.GameOver: _handle_result_key,
        GUIStateEnum.All_Clear: _handle_result_key,
        GUIStateEnum.Stage_Clear: _handle_stage_clear_key,
    }
    handler = handlers.get(game.state)
    if handler is not None:
        return handler(game, key, canvas)


def _handle_home_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    if key == KeyEnum.ENTER:
        if game.home_focusing == 0:
            game.restart_game()
        elif game.home_focusing == 1:
            game.set_state(GUIStateEnum.Instruction)
        elif game.home_focusing == 2:
            game.set_state(GUIStateEnum.Ranking)
        elif game.home_focusing == 3:
            return WindowAction.Close
    elif key == KeyEnum.I:
        game.set_state(GUIStateEnum.Instruction)
    elif key == KeyEnum.H:
        game.set_state(GUIStateEnum.Ranking)
    elif key == KeyEnum.UP:
        game.home_focusing = (game.home_focusing - 1) % 4
        game.needs_redraw = True
    elif key == KeyEnum.DOWN:
        game.home_focusing = (game.home_focusing + 1) % 4
        game.needs_redraw = True


def _handle_ranking_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    if key == KeyEnum.ENTER:
        game.set_state(GUIStateEnum.Home)
    elif key == KeyEnum.C:
        game.set_state(GUIStateEnum.Confirm_Clear)


def _handle_instruction_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    if key == KeyEnum.ENTER:
        game.set_state(GUIStateEnum.Home)


def _handle_confirm_clear_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    if key == KeyEnum.Y:
        game.score_manager.clear()
        game.set_state(GUIStateEnum.Ranking)
    elif key == KeyEnum.N:
        game.set_state(GUIStateEnum.Ranking)


def _handle_playing_key(
    game: Game,
    key: int,
    canvas: VisualizerUtils,
) -> WindowAction | None:
    if _handle_cheat_sequence(game, key):
        return
    if key == KeyEnum.P:
        game.set_state(GUIStateEnum.Pause)
        return
    if key in (99, 67):
        return WindowAction.CycleColors
    if _handle_cheat_key(game, key):
        return
    _handle_movement_key(game, key, canvas)


def _handle_cheat_sequence(game: Game, key: int) -> bool:
    """Consume activation keys before ordinary gameplay controls."""
    if game.cheathandler.consume(key):
        game.cheat_enabled = not game.cheat_enabled
        if not game.cheat_enabled:
            game.ghost_frozen = False
            game.no_collision = False
            game.auto_enabled = False
            game.score_multiplier = 1
            game.player.movement.wallhack = False
        return True
    return game.cheathandler.index > 0


def _handle_cheat_key(game: Game, key: int) -> bool:
    """Apply an enabled cheat and report whether the key was handled."""
    if not game.cheat_enabled:
        return False
    if key == KeyEnum.N:
        game.next_level()
    elif key == KeyEnum.F:
        game.ghost_frozen = not game.ghost_frozen
    elif key == KeyEnum.L:
        game.player.lives += 1
    elif key == KeyEnum.T:
        game.remaining_time += 10.0
    elif key == KeyEnum.O:
        game.auto_enabled = not game.auto_enabled
        game.player.reserved_move = None
    elif key == KeyEnum.X:
        game.score_multiplier = 10 if game.score_multiplier == 1 else 1
    elif key == KeyEnum.H:
        game.player.movement.wallhack = not game.player.movement.wallhack
    elif key == KeyEnum.V:
        game.player.movement.speed = 8 if game.player.movement.speed == 16 else 16
    elif key == KeyEnum.K:
        game.no_collision = not game.no_collision
    else:
        return False
    return True


def _handle_movement_key(game: Game, key: int, canvas: VisualizerUtils) -> None:
    """Translate movement keys and hand the requested direction to Player."""
    direction = MOVEMENT_DIRECTIONS.get(key)
    if direction is not None:
        game.auto_enabled = False
        game.player.request_move(direction, game.maze, canvas)


def _handle_ready_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    game.set_state(GUIStateEnum.Playing)


def _handle_pause_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    if key == KeyEnum.P:
        game.set_state(GUIStateEnum.Playing)
    elif key == KeyEnum.H:
        game.set_state(GUIStateEnum.Home)


def _handle_result_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    if key == KeyEnum.ENTER:
        game.submit_score()
    else:
        _handle_name_key(game, key)


def _handle_name_key(game: Game, key: int) -> None:
    """Edit the result name with the existing length and character limits."""
    if key == KeyEnum.BACKSPACE:
        game.player_name = game.player_name[:-1]
        game.needs_redraw = True
    elif (
        0 <= key <= 128
        and (chr(key).isalnum() or chr(key) == " ")
        and len(game.player_name) < 10
    ):
        char = chr(key)
        if len(game.shift_keys):
            game.player_name += char.upper()
        else:
            game.player_name += char
        game.needs_redraw = True


def _handle_stage_clear_key(
    game: Game,
    key: int,
    _canvas: VisualizerUtils,
) -> WindowAction | None:
    game.next_level()


def release_key(game: Game, key: int) -> None:
    if key == KeyEnum.SHIFT_L or key == KeyEnum.SHIFT_R:
        game.shift_keys.discard(key)

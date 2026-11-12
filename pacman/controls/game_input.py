"""Translate keyboard input into game actions for each screen state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pacman.controls.keys import MOVEMENT_DIRECTIONS, KeyEnum, WindowAction
from pacman.game.player import Player
from pacman.game.state import GameState

if TYPE_CHECKING:
    from pacman.visualize.canvas import Canvas

if TYPE_CHECKING:
    from pacman.game.game import Game


def dispatch_key(game: Game, key: int, canvas: Canvas) -> WindowAction | None:
    """Handle common controls, then dispatch to the current state's handler.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        canvas: Canvas holding the current cell layout.

    Returns:
        The window action to perform, or None.
    """
    if key in (KeyEnum.SHIFT_L, KeyEnum.SHIFT_R):
        game.shift_keys.add(key)
        return
    if key == KeyEnum.ESC:
        return WindowAction.Close
    handlers = {
        GameState.Home: _handle_home_key,
        GameState.Ranking: _handle_ranking_key,
        GameState.Instruction: _handle_instruction_key,
        GameState.Confirm_Clear: _handle_confirm_clear_key,
        GameState.Playing: _handle_playing_key,
        GameState.Ready: _handle_ready_key,
        GameState.Pause: _handle_pause_key,
        GameState.GameOver: _handle_result_key,
        GameState.All_Clear: _handle_result_key,
        GameState.Stage_Clear: _handle_stage_clear_key,
    }
    handler = handlers.get(game.state)
    if handler is not None:
        return handler(game, key, canvas)


def _handle_home_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Move the menu cursor or open the selected Home entry.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        WindowAction.Close when Exit is chosen, otherwise None.
    """
    if key == KeyEnum.ENTER:
        if game.home_focusing == 0:
            game.restart_game()
        elif game.home_focusing == 1:
            game.set_state(GameState.Instruction)
        elif game.home_focusing == 2:
            game.set_state(GameState.Ranking)
        elif game.home_focusing == 3:
            return WindowAction.Close
    elif key == KeyEnum.I:
        game.set_state(GameState.Instruction)
    elif key == KeyEnum.H:
        game.set_state(GameState.Ranking)
    elif key == KeyEnum.UP:
        game.home_focusing = (game.home_focusing - 1) % 4
        game.needs_redraw = True
    elif key == KeyEnum.DOWN:
        game.home_focusing = (game.home_focusing + 1) % 4
        game.needs_redraw = True


def _handle_ranking_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Return Home with Enter or ask to clear rankings with C.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    if key == KeyEnum.ENTER:
        game.set_state(GameState.Home)
    elif key == KeyEnum.C:
        game.set_state(GameState.Confirm_Clear)


def _handle_instruction_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Return Home from the instructions with Enter.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    if key == KeyEnum.ENTER:
        game.set_state(GameState.Home)


def _handle_confirm_clear_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Clear the rankings with Y or cancel with N.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    if key == KeyEnum.Y:
        game.score_manager.clear()
        game.set_state(GameState.Ranking)
    elif key == KeyEnum.N:
        game.set_state(GameState.Ranking)


def _handle_playing_key(
    game: Game,
    key: int,
    canvas: Canvas,
) -> WindowAction | None:
    """Handle cheats, pause, color cycling and movement in play.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        canvas: Canvas holding the current cell layout.

    Returns:
        WindowAction.CycleColors for C, otherwise None.
    """
    if _handle_cheat_sequence(game, key):
        return
    if key == KeyEnum.P:
        game.set_state(GameState.Pause)
        return
    if key == KeyEnum.C:
        return WindowAction.CycleColors
    if _handle_cheat_key(game, key):
        return
    _handle_movement_key(game, key, canvas)


def _handle_cheat_sequence(game: Game, key: int) -> bool:
    """Consume activation keys before ordinary gameplay controls.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.

    Returns:
        True when the key belongs to the cheat command and is consumed.
    """
    if game.cheathandler.consume_key(key):
        game.cheat_enabled = not game.cheat_enabled
        if not game.cheat_enabled:
            game.ghost_frozen = False
            game.no_collision = False
            game.score_multiplier = 1
            game.player.movement.wallhack = False
            game.player.movement.speed = Player.DEFAULT_SPEED
        return True
    return game.cheathandler.index > 0


def _handle_cheat_key(game: Game, key: int) -> bool:
    """Apply an enabled cheat and report whether the key was handled.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.

    Returns:
        True when an enabled cheat handled the key.
    """
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


def _handle_movement_key(game: Game, key: int, canvas: Canvas) -> None:
    """Translate movement keys and hand the requested direction to Player.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        canvas: Canvas holding the current cell layout.
    """
    direction = MOVEMENT_DIRECTIONS.get(key)
    if direction is not None:
        game.player.request_move(direction, game.maze, canvas)


def _handle_ready_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Start playing on any key.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    game.set_state(GameState.Playing)


def _handle_pause_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Resume with P or return Home with H.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    if key == KeyEnum.P:
        game.set_state(GameState.Playing)
    elif key == KeyEnum.H:
        game.set_state(GameState.Home)


def _handle_result_key(
    game: Game,
    key: int,
    _canvas: Canvas,
) -> WindowAction | None:
    """Save the score with Enter, otherwise edit the name.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    if key == KeyEnum.ENTER:
        game.submit_score()
    else:
        _handle_name_key(game, key)


def _handle_name_key(game: Game, key: int) -> None:
    """Edit the result name with the existing length and character limits.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
    """
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
    _canvas: Canvas,
) -> WindowAction | None:
    """Continue to the next level on any key.

    Args:
        game: Game whose state the key changes.
        key: Key code reported by MLX.
        _canvas: Unused; keeps every handler's signature identical.

    Returns:
        Always None.
    """
    game.next_level()


def release_key(game: Game, key: int) -> None:
    """Forget a released Shift key used for uppercase names.

    Args:
        game: Game whose pressed Shift keys are tracked.
        key: Released key code.
    """
    if key == KeyEnum.SHIFT_L or key == KeyEnum.SHIFT_R:
        game.shift_keys.discard(key)

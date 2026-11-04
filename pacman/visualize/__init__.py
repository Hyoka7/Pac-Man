"""Window presentation and rendering, loaded without starting the application."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_visualizer import GameVisualizer

__all__ = ["GameVisualizer"]


def __getattr__(name: str) -> type[GameVisualizer]:
    if name == "GameVisualizer":
        from .game_visualizer import GameVisualizer

        return GameVisualizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

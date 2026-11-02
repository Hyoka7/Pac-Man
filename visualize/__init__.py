"""Window presentation and rendering, loaded without starting the application."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .maze_visualizer import MazeVisualizer

__all__ = ["MazeVisualizer"]


def __getattr__(name: str) -> type[MazeVisualizer]:
    if name == "MazeVisualizer":
        from .maze_visualizer import MazeVisualizer

        return MazeVisualizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

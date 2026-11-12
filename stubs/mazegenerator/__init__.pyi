"""Type stubs for the assigned A-Maze-ing package (mazegenerator 2.1.0).

The package has type hints but no ``py.typed`` marker, so mypy cannot
read them. These stubs restate its public API; the package is used as-is.
"""


class MazeGenerator:
    def __init__(
        self,
        size: tuple[int, int] = ...,
        perfect: bool = ...,
        entry_cell: tuple[int, int] = ...,
        exit_cell: tuple[int, int] = ...,
        seed: int = ...,
    ) -> None: ...

    @property
    def maze(self) -> list[list[int]]: ...

    @property
    def shortest_path(self) -> str | bool: ...

    @property
    def maze_entry(self) -> tuple[int, int]: ...

    @property
    def maze_exit(self) -> tuple[int, int]: ...

    def generate(self, seed: int = ...) -> None: ...


__all__ = ["MazeGenerator"]

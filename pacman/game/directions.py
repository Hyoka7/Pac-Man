"""Shared grid directions; positive y points down the screen."""

from pacman.types import CellOffset

DIRECTIONS = ("N", "E", "S", "W")

DIRECTION_OFFSETS: dict[str, CellOffset] = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}

OPPOSITE_DIRECTIONS: dict[str, str] = {
    "N": "S",
    "E": "W",
    "S": "N",
    "W": "E",
}

WALL_BITS: dict[str, int] = {
    "N": 1,
    "E": 2,
    "S": 4,
    "W": 8,
}

ALL_WALLS = sum(WALL_BITS.values())
"""Wall mask of a closed cell (walls on every side)."""

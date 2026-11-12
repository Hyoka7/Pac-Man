"""Names for shared coordinates, image colors and maze data structures."""

type CellPosition = tuple[int, int]
"""Maze cell coordinates (column, row), counted from zero."""

type CellOffset = tuple[int, int]
"""Change in maze cell coordinates (dx, dy); positive y points down."""

type PixelPosition = tuple[float, float]
"""Screen coordinates (x, y) in pixels, including fractional positions."""

type RGBColor = tuple[int, int, int]
"""Red, green and blue channel values, each from 0 to 255."""

type RGBAColor = tuple[int, int, int, int]
"""Red, green, blue and alpha, each 0 to 255; alpha 255 is opaque."""

type MazeGrid = list[list[int]]
"""Rows of wall bitmasks, indexed as grid[y][x]."""

type CellDistances = dict[CellPosition, int]
"""Reachable cells mapped to shortest step counts from one origin."""

type MazeDistances = dict[CellPosition, CellDistances]
"""Origin cells mapped to their destination-distance dictionaries."""

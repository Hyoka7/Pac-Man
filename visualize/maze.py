"""Maze walls, navigation and rendering."""

from collections import deque

from .visualizerutils import VisualizerUtils


class Maze:
    """Own a rectangular grid of wall masks."""

    def __init__(self, maze: list[list[int]]) -> None:
        """Validate and copy the supplied maze."""
        if not maze or not maze[0]:
            raise ValueError("maze must not be empty")
        self.rows = len(maze)
        self.cols = len(maze[0])
        if any(len(row) != self.cols for row in maze):
            raise ValueError("maze must be rectangular")
        if any(
            type(cell) is not int or not 0 <= cell <= 15 for row in maze for cell in row
        ):
            raise ValueError("each cell must be an integer wall mask (0..15)")
        self.maze = [row[:] for row in maze]
        self.distances = {
            (x, y): self._build_distances((x, y))
            for y, row in enumerate(self.maze)
            for x, cell in enumerate(row)
            if cell != 15
        }

    def central_cell(self) -> tuple[int, int]:
        """Return a passage nearest the center, breaking ties in row order."""
        center_x, center_y = self.cols // 2, self.rows // 2
        passages = [
            (x, y)
            for y, row in enumerate(self.maze)
            for x, cell in enumerate(row)
            if cell != 15
        ]
        if not passages:
            raise ValueError("maze has no passage for the player")
        return min(
            passages,
            key=lambda cell: abs(cell[0] - center_x) + abs(cell[1] - center_y),
        )

    def _build_distances(
        self, start: tuple[int, int]
    ) -> dict[tuple[int, int], int]:
        """Run BFS from one cell while preparing the level's distance table."""
        distances = {start: 0}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for direction in ("N", "E", "S", "W"):
                if not self.can_move(*cell, direction):
                    continue
                neighbor = self.next_cell(*cell, direction)
                x, y = neighbor
                if neighbor in distances or self.maze[y][x] == 15:
                    continue
                distances[neighbor] = distances[cell] + 1
                queue.append(neighbor)
        return distances

    def next_cell(self, x: int, y: int, direction: str) -> tuple[int, int]:
        """Return the adjacent cell; walls and bounds are checked separately."""
        offsets = {
            "N": (0, -1),
            "E": (1, 0),
            "S": (0, 1),
            "W": (-1, 0),
        }
        if direction not in offsets:
            raise ValueError("direction must be N, E, S or W")
        dx, dy = offsets[direction]
        return x + dx, y + dy

    def can_move(self, x: int, y: int, direction: str) -> bool:
        """Return whether a cell has an in-bounds passage in a direction."""
        directions = {
            "N": 1,
            "E": 2,
            "S": 4,
            "W": 8,
        }
        if direction not in directions:
            return False
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return False
        next_x, next_y = self.next_cell(x, y, direction)
        wall = directions[direction]
        return (
            0 <= next_x < self.cols
            and 0 <= next_y < self.rows
            and self.maze[y][x] & wall == 0
        )

    def draw(
        self,
        canvas: VisualizerUtils,
        wall_color: tuple[int, int, int],
        landmark_color: tuple[int, int, int],
    ) -> None:
        """Draw the maze and enclosed 42 cells."""

        def line(x0: int, y0: int, x1: int, y1: int) -> None:
            canvas._fill_cell(x0, y0, x1 + 1, y1 + 1, wall_color)

        for y, row in enumerate(self.maze):
            for x, cell in enumerate(row):
                x0 = canvas.offset_x + x * canvas.cell_size
                y0 = canvas.offset_y + y * canvas.cell_size
                x1 = x0 + canvas.cell_size
                y1 = y0 + canvas.cell_size
                if cell == 15:
                    canvas._fill_cell(x0, y0, x1, y1, landmark_color)
                if cell & 1:
                    line(x0, y0, x1, y0)
                if cell & 2:
                    line(x1, y0, x1, y1)
                if cell & 4:
                    line(x0, y1, x1, y1)
                if cell & 8:
                    line(x0, y0, x0, y1)

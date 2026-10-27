"""Pixel-coordinate movement shared by players and ghosts."""

from .maze import Maze
from .visualizerutils import VisualizerUtils


class Movement:
    """Own a character's cell, pixel position and active cell-to-cell motion."""

    def __init__(
        self,
        cell: tuple[int, int],
        speed: float = 5.0,
        direction: str = "E",
    ) -> None:
        """Set the initial cell and speed in cells per second."""
        self.cell = cell
        self.previous_cell: tuple[int, int] | None = None
        self.initial_cell = cell
        # place() sets the actual pixel coordinates before drawing or movement.
        self.center: tuple[float, float] = (0.0, 0.0)
        self.target_cell = cell
        self.target: tuple[float, float] = self.center
        self.direction = direction
        self.speed = speed
        self.moving = False

    @staticmethod
    def move_towards(
        center: tuple[float, float],
        target: tuple[float, float],
        distance: float,
    ) -> tuple[float, float]:
        """Advance along one axis, stopping exactly at the target.

        Coordinates and distance are measured in pixels. The caller chooses a
        reachable neighboring cell and handles what happens on arrival.
        """
        if distance < 0:
            raise ValueError("movement distance must be non-negative")
        x, y = center
        target_x, target_y = target
        if x != target_x and y != target_y:
            raise ValueError("movement target must be horizontal or vertical")
        if x < target_x:
            x = min(x + distance, target_x)
        elif x > target_x:
            x = max(x - distance, target_x)
        if y < target_y:
            y = min(y + distance, target_y)
        elif y > target_y:
            y = max(y - distance, target_y)
        return x, y

    def place(self, canvas: VisualizerUtils) -> None:
        """Place the character at its cell center once layout is available."""
        self.previous_cell = None
        self.center = canvas.cell_center(*self.cell)
        self.target = self.center
        self.target_cell = self.cell
        self.moving = False

    def start(self, direction: str, maze: Maze, canvas: VisualizerUtils) -> bool:
        """Begin an allowed neighboring-cell animation when stopped."""
        if self.moving or not maze.can_move(*self.cell, direction):
            return False
        self.center = canvas.cell_center(*self.cell)
        self.target_cell = maze.next_cell(*self.cell, direction)
        self.target = canvas.cell_center(*self.target_cell)
        self.direction = direction
        self.moving = True
        return True

    def update(self, elapsed: float, canvas: VisualizerUtils) -> bool:
        """Advance one frame; return True only on arrival at the target cell."""
        if not self.moving:
            return False
        distance = canvas.cell_size * self.speed * elapsed
        self.center = self.move_towards(self.center, self.target, distance)
        if self.center != self.target:
            return False
        if self.cell != self.target_cell:
            self.previous_cell = self.cell
        self.cell = self.target_cell
        self.moving = False
        return True

    def reset(self, canvas: VisualizerUtils) -> None:
        self.cell = self.initial_cell
        self.place(canvas)

    def _cell_distance(self, p1: float, p2: float) -> float:
        return abs(p1 - p2)

    def redirect(self, req_dir: str, maze: Maze, canvas: VisualizerUtils) -> bool:
        if not self.moving:
            return self.start(req_dir, maze, canvas)
        if req_dir == self.direction:
            return False
        else:
            against_dict = {
                "N": "S",
                "S": "N",
                "E": "W",
                "W": "E",
            }
            if req_dir == against_dict[self.direction]:
                new_target = maze.next_cell(
                    *self.target_cell,
                    req_dir,
                )
                self.target_cell = new_target
                self.target = canvas.cell_center(*new_target)
                self.direction = req_dir
                return True
            diff_x = self._cell_distance(
                self.center[0], canvas.cell_center(*self.cell)[0]
            )
            diff_y = self._cell_distance(
                self.center[1], canvas.cell_center(*self.cell)[1]
            )
            # 交差点曲がり判定幅：小さいほど厳密
            allowed_distance = canvas.cell_size / 4
            if (
                diff_x <= allowed_distance
                and diff_y <= allowed_distance
                and maze.can_move(*self.cell, req_dir)
            ):
                self.moving = False
                return self.start(req_dir, maze, canvas)
            return False

"""Choose player directions using gum routes and predicted ghost arrivals."""

from collections import deque
from math import hypot, inf

from .ghost import Ghost
from .maze import Maze
from .pacgums import Pacgums
from .player import Player
from .visualizerutils import VisualizerUtils

Cell = tuple[int, int]


class AutoPlayer:
    """Search a few cells ahead; prefer survival before collecting gum."""

    LOOKAHEAD = 8
    SAFETY_SECONDS = 0.10

    def choose_direction(
        self,
        maze: Maze,
        player: Player,
        pacgums: Pacgums,
        ghosts: list[Ghost],
        canvas: VisualizerUtils,
        *,
        ghosts_frozen: bool = False,
    ) -> str | None:
        """Return a safe step toward gum, or the least dangerous escape step."""
        source = player.movement.cell
        targets = {
            (round((x - canvas.offset_x) / canvas.cell_size - 0.5),
             round((y - canvas.offset_y) / canvas.cell_size - 0.5))
            for x, y in pacgums.remain_gums | pacgums.super_gums
        }
        neighbors = self._neighbors(maze, source)
        if not targets or not neighbors or player.movement.speed <= 0:
            return None

        arrivals = self._ghost_arrivals(maze, player, ghosts, canvas, ghosts_frozen)
        protection = player.invincible_remain if player.is_invincible else 0.0
        super_cells = {
            (round((x - canvas.offset_x) / canvas.cell_size - 0.5),
             round((y - canvas.offset_y) / canvas.cell_size - 0.5))
            for x, y in pacgums.super_gums
        }
        blocked: set[str] = set()
        for direction, neighbor in neighbors:
            corridor = self._dead_end(maze, source, neighbor)
            escape_time = 2 * len(corridor) / player.movement.speed
            if (corridor and not super_cells.intersection(corridor)
                    and protection <= escape_time + self.SAFETY_SECONDS
                    and arrivals.get(source, inf) <= escape_time + self.SAFETY_SECONDS):
                blocked.add(direction)

        # BFS supplies shortest safe routes without rebuilding the distance table.
        queue: deque[tuple[Cell, int, str | None]] = deque([(source, 0, None)])
        visited = {source}
        best: tuple[float, float, float] | None = None
        chosen: str | None = None
        while queue:
            cell, steps, first_direction = queue.popleft()
            if first_direction is not None:
                if cell in targets:
                    return first_direction
                remaining = self._gum_distance(maze, cell, targets)
                rank = (remaining + steps, remaining, -arrivals.get(cell, inf))
                if best is None or rank < best:
                    best, chosen = rank, first_direction
            if steps >= self.LOOKAHEAD:
                continue
            exits = self._neighbors(maze, cell)
            exits.sort(key=lambda item: item[0] != player.movement.direction)
            for direction, neighbor in exits:
                if neighbor in visited or (steps == 0 and direction in blocked):
                    continue
                travel_time = (steps + 1) / player.movement.speed
                if (protection <= travel_time + self.SAFETY_SECONDS
                        and arrivals.get(neighbor, inf) <= travel_time + self.SAFETY_SECONDS):
                    continue
                visited.add(neighbor)
                queue.append((neighbor, steps + 1, first_direction or direction))
        if chosen is not None:
            return chosen

        # No safe route was found: keep the greatest margin from an approaching enemy.
        return max(neighbors, key=lambda item: (
            arrivals.get(item[1], inf),
            item[0] not in blocked,
            -self._gum_distance(maze, item[1], targets),
            item[1] != player.movement.previous_cell,
        ))[0]

    def _neighbors(self, maze: Maze, cell: Cell) -> list[tuple[str, Cell]]:
        return [(direction, maze.next_cell(*cell, direction))
                for direction in ("N", "E", "S", "W")
                if maze.can_move(*cell, direction)]

    def _gum_distance(self, maze: Maze, cell: Cell, targets: set[Cell]) -> float:
        distances = maze.distances.get(cell, {})
        return min((distances.get(target, inf) for target in targets), default=inf)

    def _dead_end(self, maze: Maze, previous: Cell, cell: Cell) -> list[Cell]:
        """Return corridor cells if this exit leads to a dead end."""
        corridor: list[Cell] = []
        seen = {previous}
        while cell not in seen:
            seen.add(cell)
            corridor.append(cell)
            exits = [neighbor for _, neighbor in self._neighbors(maze, cell)
                     if neighbor != previous]
            if len(exits) != 1:
                return corridor if not exits else []
            previous, cell = cell, exits[0]
        return []

    def _ghost_arrivals(
        self, maze: Maze, player: Player, ghosts: list[Ghost],
        canvas: VisualizerUtils, frozen: bool,
    ) -> dict[Cell, float]:
        """Estimate the earliest dangerous arrival, including collision radii."""
        arrivals: dict[Cell, float] = {}
        for ghost in ghosts:
            distances = maze.distances.get(ghost.cell, {})
            center = canvas.cell_center(*ghost.cell)
            progress = (hypot(ghost.movement.center[0] - center[0],
                              ghost.movement.center[1] - center[1]) / canvas.cell_size
                        if ghost.movement.moving else 0.0)
            collision_distance = (player.radius + ghost.radius) / canvas.cell_size
            for cell, distance in distances.items():
                clearance = max(0.0, distance - progress) - collision_distance
                if frozen or ghost.movement.speed <= 0:
                    arrival = 0.0 if clearance <= 0 else inf
                else:
                    arrival = max(0.0, clearance / ghost.movement.speed)
                arrival += ghost.respawn_remaining
                arrivals[cell] = min(arrivals.get(cell, inf), arrival)
        return arrivals

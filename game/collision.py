import math

from game.ghost import Ghost
from game.player import Player


class Collision:
    def is_collision(
        self,
        player: Player,
        ghost: Ghost,
    ) -> bool:
        x = player.movement.center[0] - ghost.movement.center[0]
        y = player.movement.center[1] - ghost.movement.center[1]
        return math.hypot(x, y) <= ghost.radius + player.radius

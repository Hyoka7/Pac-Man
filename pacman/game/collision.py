import math

from pacman.game.ghost import Ghost
from pacman.game.player import Player


class Collision:
    """Circle-based contact test between the player and a ghost."""

    def is_collision(
        self,
        player: Player,
        ghost: Ghost,
    ) -> bool:
        """Return whether the two characters' circles touch.

        Args:
            player: Player with a pixel center and radius.
            ghost: Ghost with a pixel center and radius.

        Returns:
            True when the center distance is at most the sum of the radii.
        """
        x = player.movement.center[0] - ghost.movement.center[0]
        y = player.movement.center[1] - ghost.movement.center[1]
        return math.hypot(x, y) <= ghost.radius + player.radius

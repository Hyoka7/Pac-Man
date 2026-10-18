"""Checks for movement shared by the player and ghosts."""

import unittest

from visualize.movement import Movement


class MovementTests(unittest.TestCase):
    """Check movement in pixel coordinates without an MLX window."""

    def test_moves_one_step_in_each_direction(self) -> None:
        """Move eight pixels toward each of four neighboring centers."""
        for target, expected in (
            ((36.0, 4.0), (36.0, 28.0)),
            ((68.0, 36.0), (44.0, 36.0)),
            ((36.0, 68.0), (36.0, 44.0)),
            ((4.0, 36.0), (28.0, 36.0)),
        ):
            with self.subTest(target=target):
                self.assertEqual(
                    Movement.move_towards((36.0, 36.0), target, 8.0), expected
                )

    def test_large_step_stops_at_target(self) -> None:
        """A long frame must never move past the selected cell center."""
        for target in ((36.0, 4.0), (68.0, 36.0),
                       (36.0, 68.0), (4.0, 36.0)):
            with self.subTest(target=target):
                self.assertEqual(
                    Movement.move_towards((36.0, 36.0), target, 100.0), target
                )

    def test_keeps_fractional_positions(self) -> None:
        """Subpixel movement must not be rounded to whole pixels."""
        self.assertEqual(
            Movement.move_towards((36.25, 36.0), (68.0, 36.0), 0.5), (36.75, 36.0)
        )

    def test_zero_step_and_arrived_position_stay_still(self) -> None:
        """No movement is needed with zero distance or at the goal."""
        self.assertEqual(
            Movement.move_towards((36.0, 36.0), (68.0, 36.0), 0.0), (36.0, 36.0)
        )
        self.assertEqual(
            Movement.move_towards((36.0, 36.0), (36.0, 36.0), 8.0), (36.0, 36.0)
        )

    def test_rejects_negative_steps(self) -> None:
        """A negative travel distance is not a valid movement step."""
        with self.assertRaises(ValueError):
            Movement.move_towards((36.0, 36.0), (68.0, 36.0), -1.0)

    def test_rejects_diagonal_targets(self) -> None:
        """Only horizontal and vertical passages are supported."""
        with self.assertRaises(ValueError):
            Movement.move_towards((36.0, 36.0), (68.0, 68.0), 8.0)


if __name__ == '__main__':
    unittest.main()

"""Cached player sprites keep direction, mouth animation and placement."""

import unittest

from visualize.player import Player
from visualize.visualizerutils import VisualizerUtils


def make_canvas() -> VisualizerUtils:
    target = VisualizerUtils(160, 120, 32, 0,
        memoryview(bytearray(160 * 120 * 4)), 160 * 4, 0, 0, 0)
    target.clear_image()
    return target


def rgb(target, x, y):
    start = y * target.line_size + x * 4
    b, g, r, _ = target.img_data[start:start+4]
    return r, g, b


class PlayerRenderingTests(unittest.TestCase):
    def test_open_mouth_faces_each_direction(self):
        cardinal = {'E': (6, 0), 'W': (-6, 0), 'N': (0, -6), 'S': (0, 6)}
        for direction in cardinal:
            with self.subTest(direction=direction):
                target = make_canvas()
                player = Player((1, 1))
                player.place(target)
                player.movement.direction = direction
                player.mouth_half_angle = 45
                player.draw(target)
                for point_direction, (dx, dy) in cardinal.items():
                    self.assertEqual(rgb(target, 48+dx, 48+dy),
                        (0, 0, 0) if point_direction == direction else (255, 255, 0))

    def test_closed_sprite_keeps_round_antialiased_edges_and_transparent_corners(self):
        target = make_canvas()
        target.fill_rect(0, 0, 160, 120, (0, 0, 80))
        player = Player((1, 1))
        player.place(target)
        player.mouth_half_angle = 0
        player.draw(target)
        for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)):
            self.assertEqual(rgb(target, 48+dx, 48+dy), (255, 255, 0))
        self.assertEqual(rgb(target, 36, 36), (0, 0, 80))
        self.assertTrue(any(0 < rgb(target, x, y)[0] < 255
                            for y in range(35, 62) for x in range(35, 62)))

    def test_stopped_player_still_animates_mouth(self):
        target = make_canvas()
        player = Player((1, 1))
        player.place(target)
        for expected in ((255, 255, 0), (0, 0, 0)):
            player.update_mouth(player.mouth_period / 2)
            target.clear_image()
            player.draw(target)
            self.assertFalse(player.movement.moving)
            self.assertEqual(rgb(target, 54, 48), expected)

    def test_sprite_follows_interpolated_center_and_new_cell_size(self):
        target = make_canvas()
        player = Player((1, 1))
        player.place(target)
        player.mouth_half_angle = 0
        player.movement.center = (96.0, 48.0)
        player.draw(target)
        self.assertEqual(rgb(target, 96, 48), (255, 255, 0))
        self.assertEqual(rgb(target, 48, 48), (0, 0, 0))
        target.cell_size = 48
        player.place(target)
        target.clear_image()
        player.draw(target)
        self.assertEqual(rgb(target, 87, 72), (255, 255, 0))
        self.assertEqual(rgb(target, 92, 72), (0, 0, 0))

import unittest

import pygame

from game.config import ZOMBIE_TYPES
from game.entities import Zombie


class ZombieBehaviorTests(unittest.TestCase):
    def test_confirmed_base_stats(self) -> None:
        self.assertEqual(ZOMBIE_TYPES["normal"]["hp"], 5)
        self.assertEqual(ZOMBIE_TYPES["fast"]["hp"], 3)
        self.assertEqual(ZOMBIE_TYPES["heavy"]["hp"], 8)
        self.assertEqual(ZOMBIE_TYPES["normal"]["speed"], 1.2)
        self.assertEqual(ZOMBIE_TYPES["fast"]["speed"], 2.0)
        self.assertEqual(ZOMBIE_TYPES["heavy"]["speed"], 0.9)
        self.assertEqual(ZOMBIE_TYPES["normal"]["separation_radius"], 12)
        self.assertEqual(ZOMBIE_TYPES["fast"]["separation_radius"], 9)
        self.assertEqual(ZOMBIE_TYPES["heavy"]["separation_radius"], 17)

    def test_confirmed_charge_parameters(self) -> None:
        expected = {
            "normal": (0.35, 3.0, 400, 0.6),
            "fast": (0.20, 3.0, 192, 0.45),
            "heavy": (0.65, 5.0, 320, 0.9),
        }
        for kind, values in expected.items():
            data = ZOMBIE_TYPES[kind]
            self.assertEqual(
                (
                    data["warning"],
                    data["charge_mult"],
                    data["max_charge_dist"],
                    data["stun"],
                ),
                values,
            )

    def test_zombie_warns_before_charging(self) -> None:
        class OpenRoom:
            @staticmethod
            def clamp_rect(rect: pygame.Rect) -> pygame.Rect:
                return rect

        zombie = Zombie("normal", pygame.Vector2(100, 100))
        player = pygame.Vector2(150, 100)
        zombie.update(0.01, player, OpenRoom(), [])
        self.assertEqual(zombie.state, "warning")
        zombie.update(0.36, player, OpenRoom(), [])
        self.assertEqual(zombie.state, "charge")
        self.assertEqual(zombie.speed, zombie.base_speed * 3)


if __name__ == "__main__":
    unittest.main()

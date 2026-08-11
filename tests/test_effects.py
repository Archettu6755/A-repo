import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game.effects import VisualEffect, numbered_paths
from game.entities import Bullet
from game.game import Game


class VisualEffectTests(unittest.TestCase):
    def test_numbered_paths_and_duration(self) -> None:
        effect = VisualEffect(
            numbered_paths("effects/fx", 3),
            pygame.Vector2(10, 20),
            (16, 16),
            0.3,
            0,
        )
        self.assertEqual(
            effect.paths,
            ("effects/fx_0.png", "effects/fx_1.png", "effects/fx_2.png"),
        )
        self.assertTrue(effect.update(0.29))
        self.assertFalse(effect.update(0.01))


class GameEffectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.start_level(1, fresh=True)

    def tearDown(self) -> None:
        pygame.quit()

    def test_firing_spawns_muzzle_effect(self) -> None:
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        self.game._try_fire()
        self.assertEqual(len(self.game.bullets), 1)
        self.assertTrue(
            any("fx_muzzle" in effect.paths[0] for effect in self.game.effects)
        )

    def test_new_effect_keeps_first_frame_until_first_draw(self) -> None:
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        self.game.update(1 / 30)
        muzzle = next(
            effect for effect in self.game.effects if "fx_muzzle" in effect.paths[0]
        )
        self.assertEqual(muzzle.elapsed, 0.0)
        self.game.update(1 / 30)
        self.assertAlmostEqual(muzzle.elapsed, 1 / 30)

    def test_lethal_hit_keeps_death_and_blood_visuals(self) -> None:
        zombie = self.game.room.zombies[0]
        zombie.hp = self.game.player.attack
        bullet = Bullet(pygame.Vector2(zombie.rect.topleft), pygame.Vector2(1, 0))
        with patch("game.game.drop_coin", return_value=None):
            self.assertTrue(self.game._bullet_hit_zombie(bullet))
        self.assertNotIn(zombie, self.game.room.zombies)
        paths = [effect.paths[0] for effect in self.game.effects]
        self.assertTrue(any("_death_" in path for path in paths))
        self.assertTrue(any("effects/blood_" in path for path in paths))

    def test_effect_pool_never_exceeds_confirmed_limit(self) -> None:
        for index in range(100):
            self.game._add_effect(
                VisualEffect(
                    ("effects/fx_bullet_impact_0.png",),
                    pygame.Vector2(index, index),
                    (16, 16),
                    1.0,
                    0,
                )
            )
        self.assertEqual(len(self.game.effects), 80)

    def test_foreground_effect_draws_after_boss(self) -> None:
        self.game.start_boss_room()
        effect = VisualEffect(
            ("effects/fx_bullet_impact_0.png",),
            pygame.Vector2(self.game.boss.rect.center),
            (16, 16),
            1.0,
            0,
            layer="foreground",
        )
        self.game.effects = [effect]
        order = []
        with (
            patch.object(
                self.game.boss, "draw", side_effect=lambda *_: order.append("boss")
            ),
            patch.object(effect, "draw", side_effect=lambda *_: order.append("effect")),
        ):
            self.game._draw_level()
        self.assertEqual(order, ["boss", "effect"])


if __name__ == "__main__":
    unittest.main()

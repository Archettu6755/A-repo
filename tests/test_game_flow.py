import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game.entities import Bullet
from game.game import Game
from game.shop import ShopScreen


class GameFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()

    def tearDown(self) -> None:
        pygame.quit()

    def test_game_starts_at_title(self) -> None:
        self.assertEqual(self.game.state, "title")

    def test_third_shop_exits_to_empty_boss_room(self) -> None:
        self.game.start_level(3, fresh=True)
        self.game.shop = ShopScreen(
            3,
            self.game.coins,
            self.game.player,
            self.game.purchase_counts,
        )
        self.game.shop.selected = len(self.game.shop.items)
        self.game.state = "shop"
        self.game._handle_shop_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
        self.assertEqual(self.game.state, "boss_room")
        self.assertTrue(self.game.room.lit)
        self.assertFalse(self.game.room.zombies)
        self.assertFalse(self.game.room.boxes)

    def test_boss_pause_menu_can_return_to_title(self) -> None:
        self.game.start_boss_room()
        self.game._pause()
        self.game.paused_selection = 1
        self.game._handle_pause_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        self.assertEqual(self.game.state, "title")

    def test_bullet_can_damage_box(self) -> None:
        self.game.start_level(1, fresh=True)
        box = self.game.room.boxes[0]
        box.hp = self.game.player.attack
        bullet = Bullet(pygame.Vector2(box.rect.center), pygame.Vector2(1, 0))
        bullet.speed = 0
        self.game.bullets.append(bullet)
        self.game._update_projectiles(0, can_hit_enemies=True)
        self.assertNotIn(box, self.game.room.boxes)

    def test_short_fire_tap_creates_bullet(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYUP, key=pygame.K_f)
        )
        self.game._try_fire()
        self.assertEqual(len(self.game.bullets), 1)

    def test_fire_tap_waits_for_nearly_ready_cooldown(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game.player.fire_timer = 0.05
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
        )
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYUP, key=pygame.K_f)
        )
        self.game._try_fire()
        self.assertFalse(self.game.bullets)
        self.game.player.update(0.06)
        self.game.controls.update(0.06)
        self.game._try_fire()
        self.assertEqual(len(self.game.bullets), 1)


if __name__ == "__main__":
    unittest.main()

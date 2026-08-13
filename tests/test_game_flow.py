import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game.config import (
    HEART_ORIGIN,
    LEVEL_CLEAR_DELAY,
    ROOM_SCREEN_LEFT,
    ROOM_SCREEN_TOP,
)
from game.entities import Bullet
from game.game import Game
from game.resources import SPRITES
from game.shop import ShopScreen


class GameFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()

    def tearDown(self) -> None:
        pygame.quit()

    def test_game_starts_at_title(self) -> None:
        self.assertEqual(self.game.state, "title")

    def test_game_disables_ime_text_input(self) -> None:
        with patch("pygame.key.stop_text_input") as stop_text_input:
            Game()
        stop_text_input.assert_called_once_with()

    def test_third_shop_exits_to_boss_room_with_boss(self) -> None:
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
        self.assertIsNone(self.game.room.switch)
        self.assertIsNotNone(self.game.boss)

    def test_three_level_flow_reaches_boss_after_third_shop(self) -> None:
        self.game.start_level(1, fresh=True)
        for expected_level in (1, 2, 3):
            with self.subTest(level=expected_level):
                self.assertEqual(self.game.level, expected_level)
                for room in self.game.level_map.rooms:
                    room.zombies.clear()
                self.game.update(1 / 60)
                self.assertEqual(self.game.state, "level_clear")
                self.game.player.hp = 1
                self.game.update(LEVEL_CLEAR_DELAY)
                self.assertEqual(self.game.state, "shop")
                self.assertEqual(self.game.player.hp, self.game.player.max_hp)
                self.game.shop.selected = len(self.game.shop.items)
                self.game._handle_shop_event(
                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
                )
        self.assertEqual(self.game.state, "boss_room")
        self.assertIsNotNone(self.game.boss)

    def test_room_screen_starts_below_heart_hud(self) -> None:
        self.game.start_level(1, fresh=True)
        self.assertEqual(ROOM_SCREEN_LEFT, 128)
        self.assertEqual(HEART_ORIGIN, (8, 6))
        room_left, room_top = self.game._to_screen(self.game.room.rect.topleft)
        self.assertEqual(room_left, ROOM_SCREEN_LEFT)
        self.assertEqual(room_top, ROOM_SCREEN_TOP)

        heart_rects = [self.game._heart_rect(index) for index in range(10)]
        self.assertEqual(max(rect.bottom for rect in heart_rects), 114)
        self.assertLessEqual(max(rect.bottom for rect in heart_rects), ROOM_SCREEN_TOP)
        rows = {}
        for rect in heart_rects:
            rows[rect.y] = rows.get(rect.y, 0) + 1
        self.assertEqual(list(rows.values()), [3, 3, 3, 1])
        for shake_timer in (0.0, 0.1, 11 / 120):
            with self.subTest(shake_timer=shake_timer):
                self.game.screen_shake_timer = shake_timer
                cam_x, cam_y = self.game.camera
                screen_walls = [
                    wall.move(-cam_x, -cam_y) for wall in self.game.room.walls
                ]
                self.assertTrue(
                    all(heart.collidelist(screen_walls) == -1 for heart in heart_rects)
                )
                visual_wall_bounds = [
                    pygame.Rect(
                        wall.left,
                        wall.top - 16,
                        wall.width,
                        wall.height + 16,
                    )
                    for wall in screen_walls
                ]
                self.assertTrue(
                    all(
                        heart.collidelist(visual_wall_bounds) == -1
                        for heart in heart_rects
                    )
                )

    def test_level_two_block_cluster_uses_fissure_art(self) -> None:
        self.game.start_level(2, fresh=True)
        with patch.object(SPRITES, "load", wraps=SPRITES.load) as load:
            self.game._draw_block_cluster(pygame.Rect(0, 0, 64, 96))
        self.assertIn(
            "environment/shared/pit_vertical.png",
            [call.args[0] for call in load.call_args_list],
        )

    def test_hud_draws_full_and_empty_hearts_without_coin(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game.player.max_hp = 5
        self.game.player.hp = 3
        with patch.object(SPRITES, "load", wraps=SPRITES.load) as load:
            self.game._draw_hud()
        paths = [call.args[0] for call in load.call_args_list]
        self.assertEqual(paths.count("ui/heart_full.png"), 3)
        self.assertEqual(paths.count("ui/heart_empty.png"), 2)
        self.assertNotIn("ui/icon_coin.png", paths)

    def test_boss_death_finishes_before_development_notice(self) -> None:
        self.game.start_boss_room()
        self.assertIsNone(self.game.shop)
        self.game.boss._load_phase(2)
        self.game.boss.hp = 1
        self.game.boss.take_damage(1)
        self.game._begin_boss_death()
        self.game.update(0.99)
        self.assertEqual(self.game.state, "boss_death")
        self.game.update(0.01)
        self.assertEqual(self.game.state, "coming_soon")
        self.game.draw()

    def test_development_notice_returns_to_title_on_any_key(self) -> None:
        self.game.start_boss_room()
        self.game.state = "coming_soon"
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.game.handle_events()
        self.assertEqual(self.game.state, "title")
        self.assertIsNone(self.game.shop)

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

    def test_player_speed_is_consistent_at_30_and_60_fps(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game.controls.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        )
        dx_60, _ = self.game._player_input(1 / 60)
        dx_30, _ = self.game._player_input(1 / 30)
        self.assertAlmostEqual(dx_60 * 60, dx_30 * 30)

    def test_darkness_keeps_full_outer_wall_height_visible(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game.room.lit = False
        self.game.screen.fill("white")
        self.game._draw_vision()
        self.assertEqual(self.game.screen.get_at((200, 80)), pygame.Color("white"))
        self.assertEqual(self.game.screen.get_at((200, 140)), pygame.Color("black"))

    def test_event_queue_fire_tap_survives_full_frame(self) -> None:
        self.game.start_level(1, fresh=True)
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_f))
        self.game.handle_events()
        self.game.update(1 / 60)
        self.game.draw()
        self.assertEqual(len(self.game.bullets), 1)
        self.assertFalse(self.game.bullets[0].rect.colliderect(self.game.player.rect))

    def _assert_physical_f_keeps_game_running(self, raw_key: int) -> None:
        self.game.start_level(1, fresh=True)
        zombie = self.game.room.zombies[0]
        pygame.event.clear()
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=raw_key,
                scancode=pygame.KSCAN_F,
            )
        )
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYUP,
                key=raw_key,
                scancode=pygame.KSCAN_F,
            )
        )
        self.game.handle_events()
        self.game.update(1 / 60)
        self.game.draw()
        self.assertEqual(self.game.state, "playing")
        self.assertEqual(len(self.game.bullets), 1)
        self.assertFalse(self.game.controls.fire_held)
        self.assertGreater(self.game.player.animation_clock, 0)
        self.assertGreater(zombie.animation_clock, 0)

        player_x = self.game.player.pos.x
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_RIGHT,
                scancode=pygame.KSCAN_RIGHT,
            )
        )
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYUP,
                key=pygame.K_RIGHT,
                scancode=pygame.KSCAN_RIGHT,
            )
        )
        self.game.handle_events()
        self.game.update(1 / 60)
        self.game.draw()
        self.assertGreater(self.game.player.pos.x, player_x)

    def test_physical_f_cannot_be_misread_as_stats_key(self) -> None:
        self._assert_physical_f_keeps_game_running(pygame.K_e)

    def test_physical_f_cannot_be_misread_as_pause_key(self) -> None:
        self._assert_physical_f_keeps_game_running(pygame.K_ESCAPE)

    def test_physical_f_works_with_unknown_logical_key(self) -> None:
        self._assert_physical_f_keeps_game_running(pygame.K_UNKNOWN)

    def test_translated_f_cannot_poison_player_movement(self) -> None:
        self.game.start_level(1, fresh=True)
        pygame.event.clear()
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
                unicode="f",
            )
        )
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYUP,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
            )
        )
        self.game.handle_events()
        self.game.update(1 / 60)
        self.assertEqual(len(self.game.bullets), 1)

        player_x = self.game.player.pos.x
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_RIGHT,
                scancode=pygame.KSCAN_RIGHT,
            )
        )
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYUP,
                key=pygame.K_RIGHT,
                scancode=pygame.KSCAN_RIGHT,
            )
        )
        self.game.handle_events()
        self.game.update(1 / 60)
        self.assertGreater(self.game.player.pos.x, player_x)

    def test_repeated_fire_pause_resume_never_blocks_movement(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game.player.hp = 999
        fire_events = (
            (pygame.K_f, pygame.KSCAN_F, "f"),
            (pygame.K_e, pygame.KSCAN_F, ""),
            (pygame.K_ESCAPE, pygame.KSCAN_F, ""),
            (pygame.K_LEFT, pygame.KSCAN_LEFT, "f"),
        )
        for cycle, (raw_key, scancode, text) in enumerate(fire_events):
            with self.subTest(cycle=cycle):
                self.game.player.fire_timer = 0
                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYDOWN,
                        key=raw_key,
                        scancode=scancode,
                        unicode=text,
                    )
                )
                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYUP,
                        key=raw_key,
                        scancode=scancode,
                    )
                )
                self.game.handle_events()
                self.game.update(1 / 60)
                self.assertEqual(self.game.state, "playing")
                self.assertFalse(self.game.controls.fire_held)

                direction = pygame.K_RIGHT if cycle % 2 == 0 else pygame.K_LEFT
                scancode_direction = (
                    pygame.KSCAN_RIGHT if cycle % 2 == 0 else pygame.KSCAN_LEFT
                )
                player_x = self.game.player.pos.x
                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYDOWN,
                        key=direction,
                        scancode=scancode_direction,
                    )
                )
                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYUP,
                        key=direction,
                        scancode=scancode_direction,
                    )
                )
                self.game.handle_events()
                self.game.update(1 / 60)
                if direction == pygame.K_RIGHT:
                    self.assertGreater(self.game.player.pos.x, player_x)
                else:
                    self.assertLess(self.game.player.pos.x, player_x)

                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYDOWN,
                        key=pygame.K_ESCAPE,
                        scancode=pygame.KSCAN_ESCAPE,
                    )
                )
                self.game.handle_events()
                self.assertEqual(self.game.state, "paused")
                pygame.event.post(
                    pygame.event.Event(
                        pygame.KEYDOWN,
                        key=pygame.K_ESCAPE,
                        scancode=pygame.KSCAN_ESCAPE,
                    )
                )
                self.game.handle_events()
                self.assertEqual(self.game.state, "playing")

    def test_translated_f_can_resume_pause_menu(self) -> None:
        self.game.start_level(1, fresh=True)
        self.game._pause()
        pygame.event.clear()
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
                unicode="f",
            )
        )
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYUP,
                key=pygame.K_LEFT,
                scancode=pygame.KSCAN_LEFT,
            )
        )
        self.game.handle_events()
        self.assertEqual(self.game.state, "playing")
        self.assertFalse(self.game.controls.fire_held)

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

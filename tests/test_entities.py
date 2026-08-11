import random
import unittest
from unittest.mock import patch

import pygame

from game.config import (
    PLAYER_ATTACK,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_MAX_HP,
    PLAYER_SPEED,
    ZOMBIE_TYPES,
)
from game.entities import Player, Zombie
from game.resources import SPRITES


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
            "normal": (288, 0.35, 3.0, 384, 0.6),
            "fast": (256, 0.20, 3.0, 320, 0.45),
            "heavy": (320, 0.65, 5.0, 448, 0.9),
        }
        for kind, values in expected.items():
            data = ZOMBIE_TYPES[kind]
            self.assertEqual(
                (
                    data["sensing_distance"],
                    data["warning"],
                    data["charge_mult"],
                    data["max_charge_dist"],
                    data["stun"],
                ),
                values,
            )

    def test_level_scaling_changes_hp_but_only_third_level_damage(self) -> None:
        for kind, base_hp, base_damage in (
            ("normal", 5, 1),
            ("fast", 3, 1),
            ("heavy", 8, 2),
        ):
            first = Zombie(kind, pygame.Vector2(), level=1)
            second = Zombie(kind, pygame.Vector2(), level=2)
            third = Zombie(kind, pygame.Vector2(), level=3)
            self.assertEqual(
                (first.hp, second.hp, third.hp), (base_hp, base_hp + 1, base_hp + 2)
            )
            self.assertEqual(
                (first.damage, second.damage, third.damage),
                (base_damage, base_damage, base_damage + 1),
            )

    def test_zombie_warns_before_charging(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

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

    def test_blocker_prevents_charge_detection(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

            @staticmethod
            def clamp_rect(rect: pygame.Rect) -> pygame.Rect:
                return rect

        zombie = Zombie("normal", pygame.Vector2(100, 100))
        zombie.wander_target = pygame.Vector2(100, 200)
        blocker = pygame.Rect(130, 80, 32, 100)
        zombie.update(0.01, pygame.Vector2(200, 100), OpenRoom(), [blocker])
        self.assertEqual(zombie.state, "wander")

    def test_warning_locks_direction_when_charge_starts(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

            @staticmethod
            def clamp_rect(rect: pygame.Rect) -> pygame.Rect:
                return rect

        zombie = Zombie("normal", pygame.Vector2(100, 100))
        zombie.update(0.01, pygame.Vector2(200, 100), OpenRoom(), [])
        self.assertEqual(zombie.state, "warning")
        zombie.update(
            0.36,
            pygame.Vector2(zombie.rect.centerx, 220),
            OpenRoom(),
            [],
        )
        self.assertEqual(zombie.state, "charge")
        self.assertGreater(zombie.charge_dir.y, 0.9)
        self.assertLess(abs(zombie.charge_dir.x), 0.1)

    def test_stun_is_followed_by_recovery_before_new_warning(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

            @staticmethod
            def clamp_rect(rect: pygame.Rect) -> pygame.Rect:
                return rect

        zombie = Zombie("normal", pygame.Vector2(100, 100))
        zombie._stun()
        zombie.update(0.61, pygame.Vector2(120, 100), OpenRoom(), [])
        self.assertEqual(zombie.state, "recover")
        zombie.update(0.81, pygame.Vector2(120, 100), OpenRoom(), [])
        self.assertEqual(zombie.state, "wander")

    def test_seeded_wander_is_reproducible(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

        first = Zombie("normal", pygame.Vector2(100, 100), rng=random.Random(7))
        second = Zombie("normal", pygame.Vector2(100, 100), rng=random.Random(7))
        first.state_timer = 0
        second.state_timer = 0
        player = pygame.Vector2(700, 500)
        first.update(0.01, player, OpenRoom(), [])
        second.update(0.01, player, OpenRoom(), [])
        self.assertEqual(first.wander_target, second.wander_target)
        self.assertEqual(first.pos, second.pos)

    def test_large_charge_step_cannot_tunnel_through_obstacle(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

        zombie = Zombie("fast", pygame.Vector2(100, 100))
        zombie._set_state("charge")
        zombie.charge_dir = pygame.Vector2(1, 0)
        zombie.speed = zombie.base_speed * zombie.charge_mult
        zombie.charge_origin = zombie.pos.copy()
        blocker = pygame.Rect(150, 80, 32, 100)
        zombie.update(0.5, pygame.Vector2(700, 100), OpenRoom(), [blocker])
        self.assertEqual(zombie.state, "stun")
        self.assertLessEqual(zombie.rect.right, blocker.left)
        self.assertTrue(zombie.consume_wall_impact())

    def test_fractional_charge_speed_does_not_fake_a_wall_collision(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

        zombie = Zombie("heavy", pygame.Vector2(100, 100))
        zombie._set_state("charge")
        zombie.charge_dir = pygame.Vector2(1, 0)
        zombie.speed = zombie.base_speed * zombie.charge_mult
        zombie.charge_origin = zombie.pos.copy()
        zombie.update(1 / 60, pygame.Vector2(700, 100), OpenRoom(), [])
        self.assertEqual(zombie.state, "charge")
        self.assertAlmostEqual(zombie.pos.x, 104.5)
        self.assertFalse(zombie.consume_wall_impact())

    def test_fast_warning_uses_all_four_prepare_frames(self) -> None:
        zombie = Zombie("fast", pygame.Vector2(100, 100))
        zombie._set_state("warning", zombie.warning_time)
        zombie.state_clock = zombie.warning_time - 0.001
        with patch.object(
            SPRITES,
            "frame",
            return_value=pygame.Surface((32, 40), pygame.SRCALPHA),
        ) as frame:
            zombie.draw(pygame.Surface((320, 240), pygame.SRCALPHA))
        self.assertIn("zombie_fast_charge_right_sheet.png", frame.call_args.args[0])
        self.assertEqual(frame.call_args.args[2], 3)

    def test_charge_trace_detects_player_crossed_during_large_frame(self) -> None:
        class OpenRoom:
            rect = pygame.Rect(0, 0, 800, 600)

        zombie = Zombie("fast", pygame.Vector2(100, 100))
        zombie._set_state("charge")
        zombie.charge_dir = pygame.Vector2(1, 0)
        zombie.speed = zombie.base_speed * zombie.charge_mult
        zombie.charge_origin = zombie.pos.copy()
        player = Player(
            pygame.Vector2(150, 100),
            PLAYER_MAX_HP,
            PLAYER_ATTACK,
            PLAYER_FIRE_COOLDOWN,
            PLAYER_SPEED,
        )
        zombie.update(0.5, pygame.Vector2(700, 100), OpenRoom(), [])
        self.assertTrue(zombie.hits_player(player))


class PlayerAnimationTests(unittest.TestCase):
    def test_lethal_hit_uses_non_looping_death_sheet(self) -> None:
        player = Player(
            pygame.Vector2(100, 100),
            PLAYER_MAX_HP,
            PLAYER_ATTACK,
            PLAYER_FIRE_COOLDOWN,
            PLAYER_SPEED,
        )
        player.take_hit(PLAYER_MAX_HP)
        player.update(0.5)
        self.assertTrue(player.dead)
        self.assertEqual(player.death_clock, 0.5)
        with patch.object(
            SPRITES,
            "frame",
            return_value=pygame.Surface((32, 48), pygame.SRCALPHA),
        ) as frame:
            player.draw(pygame.Surface((320, 240), pygame.SRCALPHA))
        self.assertEqual(
            frame.call_args.args[0], "characters/player/player_death_sheet.png"
        )
        self.assertEqual(frame.call_args.args[2], 5)


if __name__ == "__main__":
    unittest.main()

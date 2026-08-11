import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game.config import (
    BOSS_CHARGE_SUBSTEP,
    BOSS_SEPARATION_RADIUS,
    BOSS_SIZE,
    PLAYER_ATTACK,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_MAX_HP,
    PLAYER_SPEED,
)
from game.entities import Boss, Bullet, Player
from game.game import Game
from game.level import Level
from game.resources import SPRITES

EXPECTED_PHASES = {
    1: {
        "hp": 100,
        "base_speed": 1.0,
        "warning": 0.80,
        "charge_speed": 6.0,
        "max_charge_dist": 640.0,
        "charges": 1,
        "stun": 1.10,
        "recovery": 1.00,
        "damage": 2,
    },
    2: {
        "hp": 50,
        "base_speed": 1.4,
        "warning": 0.40,
        "charge_speed": 7.5,
        "max_charge_dist": 480.0,
        "charges": 2,
        "stun": 0.60,
        "recovery": 0.50,
        "damage": 3,
    },
}


class BossBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.room = SimpleNamespace(rect=pygame.Rect(0, 0, 1000, 600))

    def tearDown(self) -> None:
        pygame.quit()

    @staticmethod
    def make_player(pos: tuple[float, float]) -> Player:
        return Player(
            pygame.Vector2(pos),
            PLAYER_MAX_HP,
            PLAYER_ATTACK,
            PLAYER_FIRE_COOLDOWN,
            PLAYER_SPEED,
        )

    def test_confirmed_phase_stats_and_collision_size(self) -> None:
        self.assertEqual(BOSS_SIZE, 56)
        self.assertEqual(BOSS_SEPARATION_RADIUS, 28)
        self.assertEqual(BOSS_CHARGE_SUBSTEP, 8.0)
        boss = Boss(pygame.Vector2(100, 100))
        self.assertEqual(boss.rect.size, (BOSS_SIZE, BOSS_SIZE))
        self.assertEqual(boss.separation_radius, BOSS_SEPARATION_RADIUS)
        for phase, expected in EXPECTED_PHASES.items():
            boss._load_phase(phase)
            self.assertEqual(boss.hp, expected["hp"])
            self.assertEqual(boss.base_speed, expected["base_speed"])
            self.assertEqual(boss.warning_time, expected["warning"])
            self.assertEqual(boss.charge_speed, expected["charge_speed"])
            self.assertEqual(boss.max_charge_dist, expected["max_charge_dist"])
            self.assertEqual(boss.charge_count, expected["charges"])
            self.assertEqual(boss.stun_time, expected["stun"])
            self.assertEqual(boss.recovery_time, expected["recovery"])
            self.assertEqual(boss.damage, expected["damage"])

    def test_phase_one_overflow_damage_does_not_reach_phase_two(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss.hp = 2
        self.assertEqual(boss.take_damage(5), "phase_changed")
        self.assertEqual(boss.phase, 2)
        self.assertEqual(boss.hp, 50)
        self.assertEqual(boss.state, "recover")
        boss.hp = 2
        self.assertEqual(boss.take_damage(5), "dead")
        self.assertTrue(boss.dead)
        self.assertEqual(boss.hp, 0)

    def test_charge_speed_is_frame_rate_independent(self) -> None:
        for phase, dt in ((1, 1 / 60), (1, 1 / 30), (2, 1 / 60), (2, 1 / 30)):
            with self.subTest(phase=phase, dt=dt):
                boss = Boss(pygame.Vector2(100, 100))
                boss._load_phase(phase)
                boss.charges_remaining = boss.charge_count
                boss._begin_charge(pygame.Vector2(900, boss.rect.centery))
                start_x = boss.pos.x
                boss.update(dt, pygame.Vector2(900, boss.rect.centery), self.room, [])
                expected = EXPECTED_PHASES[phase]["charge_speed"] * dt * 60
                self.assertAlmostEqual(boss.pos.x - start_x, expected)

    def test_large_recovery_step_cannot_tunnel_through_pillar(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss._set_state("recover", 2.0)
        blocker = pygame.Rect(200, 80, 32, 100)
        boss.update(2.0, pygame.Vector2(900, boss.rect.centery), self.room, [blocker])
        self.assertLessEqual(boss.rect.right, blocker.left)
        self.assertEqual(boss.state, "warning")

    def test_large_frame_cannot_exceed_recovery_movement_budget(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss._set_state("recover", boss.recovery_time)
        start_x = boss.pos.x
        boss.update(2.0, pygame.Vector2(900, boss.rect.centery), self.room, [])
        expected = boss.base_speed * boss.recovery_time * 60
        self.assertAlmostEqual(boss.pos.x - start_x, expected)
        self.assertEqual(boss.state, "warning")

    def test_large_step_cannot_tunnel_and_trace_is_segmented(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss.charges_remaining = boss.charge_count
        boss._begin_charge(pygame.Vector2(900, boss.rect.centery))
        blocker = pygame.Rect(220, 80, 32, 100)
        boss.update(0.5, pygame.Vector2(900, boss.rect.centery), self.room, [blocker])
        self.assertEqual(boss.state, "stun")
        self.assertLessEqual(boss.rect.right, blocker.left)
        self.assertTrue(boss.consume_wall_impact())
        steps = [
            first.distance_to(second)
            for first, second in zip(
                boss.movement_trace,
                boss.movement_trace[1:],
                strict=False,
            )
        ]
        self.assertTrue(steps)
        self.assertLessEqual(max(steps), BOSS_CHARGE_SUBSTEP)

    def test_diagonal_charge_trace_keeps_float_substep_limit(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss.charges_remaining = boss.charge_count
        target = pygame.Vector2(900, 500)
        boss._begin_charge(target)
        boss.update(1 / 30, target, self.room, [])
        steps = [
            first.distance_to(second)
            for first, second in zip(
                boss.movement_trace,
                boss.movement_trace[1:],
                strict=False,
            )
        ]
        self.assertTrue(steps)
        self.assertLessEqual(max(steps), BOSS_CHARGE_SUBSTEP + 1e-9)

    def test_contact_checks_full_trace_segments(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        player = self.make_player((26, 25))
        boss.charge_trace_active = True
        boss.contact_available = True
        boss.contact_damage = 2
        boss.movement_trace = [pygame.Vector2(0, 0), pygame.Vector2(80, 0)]
        minimum = boss.separation_radius + player.separation_radius
        self.assertGreater(
            boss.movement_trace[0].distance_to(player.rect.center), minimum
        )
        self.assertGreater(
            boss.movement_trace[1].distance_to(player.rect.center), minimum
        )
        self.assertEqual(boss.contact_with_player(player), 2)

    def test_phase_two_rewarns_and_relocks_before_second_charge(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss._start_attack()
        first_target = pygame.Vector2(900, boss.rect.centery)
        boss.update(boss.warning_time, first_target, self.room, [])
        self.assertEqual(boss.state, "charge")
        boss.update(
            boss.max_charge_dist / (boss.charge_speed * 60),
            first_target,
            self.room,
            [],
        )
        self.assertEqual(boss.state, "warning")
        self.assertEqual(boss.charges_remaining, 1)

        second_target = pygame.Vector2(boss.rect.centerx, 20)
        boss.update(boss.warning_time / 2, second_target, self.room, [])
        self.assertLess(boss.facing.y, -0.99)
        boss.update(boss.warning_time / 2, second_target, self.room, [])
        self.assertEqual(boss.state, "charge")
        self.assertLess(boss.charge_dir.y, -0.99)
        self.assertEqual(boss.charges_remaining, 0)

    def test_wall_hit_cancels_remaining_phase_two_charge(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss._start_attack()
        target = pygame.Vector2(900, boss.rect.centery)
        boss.update(boss.warning_time, target, self.room, [])
        blocker = pygame.Rect(220, 80, 32, 100)
        boss.update(0.5, target, self.room, [blocker])
        self.assertEqual(boss.state, "stun")
        self.assertEqual(boss.charges_remaining, 0)

    def test_fixed_arena_preserves_full_phase_one_charge_lane(self) -> None:
        level = Level(3, boss_only=True, seed=1)
        room = level.rooms[0]
        boss = Boss(room.boss_spawn)
        boss.charges_remaining = boss.charge_count
        target = pygame.Vector2(room.spawn) + pygame.Vector2(14)
        boss._begin_charge(target)
        boss.update(2.0, target, room, room.static_blockers())
        self.assertAlmostEqual(boss.pos.distance_to(boss.charge_origin), 640.0)
        self.assertEqual(boss.state, "stun")
        self.assertFalse(boss.consume_wall_impact())

    def test_swept_contact_hits_once_per_charge_even_before_wall_impact(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss.charges_remaining = boss.charge_count
        player = self.make_player((186, 114))
        boss._begin_charge(pygame.Vector2(900, boss.rect.centery))
        blocker = pygame.Rect(260, 80, 32, 100)
        boss.update(0.5, pygame.Vector2(900, boss.rect.centery), self.room, [blocker])
        self.assertEqual(boss.state, "stun")
        self.assertEqual(boss.contact_with_player(player), 3)
        self.assertEqual(boss.contact_with_player(player), 0)

        boss.pos.update(100, 100)
        boss.charges_remaining = 1
        boss._begin_charge(pygame.Vector2(900, boss.rect.centery))
        boss.update(0.3, pygame.Vector2(900, boss.rect.centery), self.room, [])
        self.assertEqual(boss.contact_with_player(player), 3)

    def test_draw_uses_confirmed_sheet_mapping(self) -> None:
        boss = Boss(pygame.Vector2(100, 100))
        boss._load_phase(2)
        boss.state = "warning"
        boss.facing.update(0, -1)
        target = pygame.Surface((300, 300), pygame.SRCALPHA)
        frame = pygame.Surface((80, 88), pygame.SRCALPHA)
        with patch.object(SPRITES, "frame", return_value=frame) as load_frame:
            boss.draw(target)
        load_frame.assert_called_once()
        self.assertEqual(
            load_frame.call_args.args[0],
            "characters/boss/boss_phase2_charge_up_sheet.png",
        )

        boss.state = "charge"
        with patch.object(SPRITES, "frame", return_value=frame) as load_frame:
            boss.draw(target)
        self.assertEqual(load_frame.call_args.args[2], 2)

        boss.dead = True
        boss.state = "dead"
        with patch.object(SPRITES, "frame", return_value=frame) as load_frame:
            boss.draw(target)
        self.assertEqual(
            load_frame.call_args.args[0],
            "characters/boss/boss_death_sheet.png",
        )


class BossGameFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.start_boss_room()

    def tearDown(self) -> None:
        pygame.quit()

    def add_bullet_on_boss(self) -> None:
        position = pygame.Vector2(self.game.boss.rect.center) - pygame.Vector2(4, 4)
        self.game.bullets.append(Bullet(position, pygame.Vector2(1, 0)))

    def test_phase_one_bullet_transition_keeps_combat_running(self) -> None:
        self.game.boss.hp = 1
        self.game.player.attack = 5
        self.add_bullet_on_boss()
        self.game._update_projectiles(0, can_hit_enemies=False, can_hit_boss=True)
        self.assertEqual(self.game.state, "boss_room")
        self.assertEqual(self.game.boss.phase, 2)
        self.assertEqual(self.game.boss.hp, 50)
        self.assertFalse(self.game.bullets)
        self.assertFalse(self.game.coin_items)

    def test_phase_two_death_clears_combat_and_locks_input(self) -> None:
        self.game.boss._load_phase(2)
        self.game.boss.hp = 1
        self.add_bullet_on_boss()
        self.game._update_projectiles(0, can_hit_enemies=False, can_hit_boss=True)
        self.assertEqual(self.game.state, "boss_death")
        self.assertFalse(self.game.bullets)
        self.assertFalse(self.game.coin_items)

        player_pos = self.game.player.pos.copy()
        pygame.event.clear()
        for key in (pygame.K_f, pygame.K_e, pygame.K_ESCAPE, pygame.K_RIGHT):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.game.handle_events()
        self.game.update(0.5)
        self.assertEqual(self.game.state, "boss_death")
        self.assertEqual(self.game.player.pos, player_pos)
        self.assertFalse(self.game.bullets)
        self.assertEqual(self.game.controls.movement_axis(), (0, 0))
        self.assertFalse(self.game.controls.wants_fire())

    def test_death_animation_precedes_notice_and_notice_returns_to_title(self) -> None:
        self.game.boss._load_phase(2)
        self.game.boss.hp = 1
        self.add_bullet_on_boss()
        self.game._update_projectiles(0, can_hit_enemies=False, can_hit_boss=True)
        self.game.update(0.99)
        self.assertEqual(self.game.state, "boss_death")
        self.game.update(0.01)
        self.assertEqual(self.game.state, "coming_soon")
        self.assertIsNone(self.game.shop)

        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.game.handle_events()
        self.assertEqual(self.game.state, "title")
        self.assertIsNone(self.game.shop)

    def test_boss_room_failure_restarts_third_level_with_upgrades(self) -> None:
        self.game.player.attack = 4
        self.game.player.speed = 5
        self.game.coins = 9
        self.game.purchase_counts = {"attack": 2, "move_speed": 1}
        self.game.state = "game_over"
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.game.handle_events()
        self.assertEqual(self.game.state, "playing")
        self.assertEqual(self.game.level, 3)
        self.assertIsNone(self.game.boss)
        self.assertEqual(self.game.coins, 0)
        self.assertEqual(self.game.player.attack, 4)
        self.assertEqual(self.game.player.speed, 5)
        self.assertEqual(
            self.game.purchase_counts,
            {"attack": 2, "move_speed": 1},
        )


if __name__ == "__main__":
    unittest.main()

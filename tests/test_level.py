import random
import unittest

import pygame

from game.config import PLAYER_SIZE, ZOMBIE_COUNT_PER_ROOM_RANGE
from game.entities import Zombie
from game.level import Level


class LevelGenerationTests(unittest.TestCase):
    def test_room_counts_and_topology(self) -> None:
        expected_ranges = {1: range(2, 4), 2: range(2, 5), 3: range(2, 5)}
        for level_number, expected in expected_ranges.items():
            for seed in range(20):
                level = Level(level_number, rng=random.Random(seed))
                self.assertIn(len(level.rooms), expected)
                self.assertEqual(len(level.doors), len(level.rooms) - 1)
                self.assertEqual(
                    len({room.coord for room in level.rooms}), len(level.rooms)
                )
                for room in level.rooms:
                    self.assertTrue(room.template_id)
                    self.assertIsNotNone(room.switch)

    def test_enemy_and_box_budgets(self) -> None:
        expected_extra_boxes = {1: (0, 1), 2: (1, 2), 3: (2, 3)}
        for level_number in (1, 2, 3):
            for seed in range(20):
                level = Level(level_number, rng=random.Random(seed))
                low, high = ZOMBIE_COUNT_PER_ROOM_RANGE[level_number]
                level.spawn_zombies((low, high), lambda pos: Zombie("normal", pos))
                enemy_count = sum(len(room.zombies) for room in level.rooms)
                self.assertGreaterEqual(enemy_count, low * len(level.rooms))
                self.assertLessEqual(enemy_count, high * len(level.rooms))
                self.assertTrue(
                    all(low <= len(room.zombies) <= high for room in level.rooms)
                )

                box_count = sum(len(room.boxes) for room in level.rooms)
                extra_low, extra_high = expected_extra_boxes[level_number]
                self.assertGreaterEqual(box_count, len(level.rooms) + extra_low)
                self.assertLessEqual(box_count, len(level.rooms) + extra_high)

    def test_enemy_spawns_do_not_overlap(self) -> None:
        for level_number, count_range in ZOMBIE_COUNT_PER_ROOM_RANGE.items():
            level = Level(level_number, rng=random.Random(7))
            maximum = count_range[1]
            level.spawn_zombies((maximum, maximum), lambda pos: Zombie("heavy", pos))
            for room in level.rooms:
                self.assertEqual(len(room.zombies), maximum)
                for index, first in enumerate(room.zombies):
                    for second in room.zombies[index + 1 :]:
                        distance = pygame.Vector2(first.rect.center).distance_to(
                            second.rect.center
                        )
                        minimum = first.separation_radius + second.separation_radius + 8
                        self.assertGreaterEqual(distance, minimum)

    def test_doors_lock_until_current_room_is_clear(self) -> None:
        level = Level(1, rng=random.Random(2))
        level.spawn_zombies((6, 6), lambda pos: Zombie("normal", pos))
        level.update_doors(0)
        self.assertTrue(level.doors_of(0))
        self.assertTrue(all(not door.open for door in level.doors_of(0)))
        level.rooms[0].zombies.clear()
        level.update_doors(0)
        self.assertTrue(all(door.open for door in level.doors_of(0)))

    def test_transition_places_player_inside_connected_room(self) -> None:
        level = Level(2, rng=random.Random(3))
        old_room = level.rooms[0]
        new_room = level.rooms[1]
        position = pygame.Vector2(new_room.rect.center)
        placed = level.place_inside_room(position, 24, 0, 1)
        self.assertTrue(new_room.rect.contains(pygame.Rect(placed.x, placed.y, 24, 24)))
        self.assertNotEqual(old_room.coord, new_room.coord)

    def test_boss_room_has_only_exit_switch_and_is_lit(self) -> None:
        level = Level(3, boss_only=True, rng=random.Random(1))
        self.assertEqual(len(level.rooms), 1)
        room = level.rooms[0]
        self.assertTrue(room.is_boss)
        self.assertTrue(room.lit)
        self.assertFalse(room.zombies)
        self.assertFalse(room.boxes)
        self.assertIsNotNone(room.switch)
        self.assertFalse(room.switch.active)
        player_rect = pygame.Rect(room.spawn.x, room.spawn.y, PLAYER_SIZE, PLAYER_SIZE)
        self.assertFalse(room.switch.rect.colliderect(player_rect))
        self.assertEqual(room.switch.rect.collidelist(room.static_blockers()), -1)
        self.assertIsNone(room.boss_spawn)


if __name__ == "__main__":
    unittest.main()

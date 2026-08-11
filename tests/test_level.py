import random
import unittest

import pygame

from game.config import (
    BOSS_SIZE,
    OBSTACLE_CELL_RANGE,
    PLAYER_SIZE,
    ROOM_HEIGHT,
    ROOM_WIDTH,
    SECONDARY_GROUP_COUNT_RANGE,
    TILE_SIZE,
    ZOMBIE_COUNT_PER_ROOM_RANGE,
)
from game.entities import Zombie
from game.level import Level
from game.room_templates import (
    PLAYER_SPAWN_CELL,
    ROOM_TEMPLATES,
    SECONDARY_PATTERNS,
)


class LevelGenerationTests(unittest.TestCase):
    def test_seed_reproduces_topology_templates_and_visuals(self) -> None:
        first = Level(3, seed=12345)
        second = Level(3, seed=12345)
        self.assertEqual(first.seed, second.seed)
        self.assertEqual(
            [room.coord for room in first.rooms],
            [room.coord for room in second.rooms],
        )
        self.assertEqual(
            [room.template_id for room in first.rooms],
            [room.template_id for room in second.rooms],
        )
        self.assertEqual(
            [room.visual_seed for room in first.rooms],
            [room.visual_seed for room in second.rooms],
        )
        self.assertEqual(
            [room.switch_cells for room in first.rooms],
            [room.switch_cells for room in second.rooms],
        )
        self.assertEqual(
            [
                [
                    (
                        obstacle.rect.left - room.rect.left,
                        obstacle.rect.top - room.rect.top,
                        obstacle.rect.width,
                        obstacle.rect.height,
                        obstacle.kind,
                    )
                    for obstacle in room.obstacles
                ]
                for room in first.rooms
            ],
            [
                [
                    (
                        obstacle.rect.left - room.rect.left,
                        obstacle.rect.top - room.rect.top,
                        obstacle.rect.width,
                        obstacle.rect.height,
                        obstacle.kind,
                    )
                    for obstacle in room.obstacles
                ]
                for room in second.rooms
            ],
        )

    def test_room_counts_and_topology(self) -> None:
        expected_ranges = {1: range(2, 3), 2: range(2, 4), 3: range(2, 4)}
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

    def test_template_metadata_and_level_selection_rules(self) -> None:
        for template in ROOM_TEMPLATES:
            self.assertTrue(template.allowed_door_masks)
            self.assertTrue(template.player_spawn_cells)
            self.assertGreaterEqual(len(template.enemy_spawn_cells), 13)
            self.assertTrue(template.switch_cells)
            self.assertTrue(template.crate_cells)
            self.assertTrue(template.decal_cells)

        allowed = {1: {1, 2}, 2: {1, 2, 3}, 3: {2, 3}}
        difficulty_counts = {1: {}, 2: {}, 3: {}}
        for level_number in (1, 2, 3):
            for seed in range(30):
                level = Level(level_number, seed=seed)
                for room in level.rooms:
                    self.assertIn(room.template_difficulty, allowed[level_number])
                    difficulty_counts[level_number][room.template_difficulty] = (
                        difficulty_counts[level_number].get(room.template_difficulty, 0)
                        + 1
                    )
                for door in level.doors:
                    first, second = door.rooms
                    self.assertNotEqual(
                        level.rooms[first].template_id,
                        level.rooms[second].template_id,
                    )
        self.assertGreater(
            difficulty_counts[1].get(1, 0), difficulty_counts[1].get(2, 0)
        )
        self.assertGreater(
            difficulty_counts[2].get(2, 0),
            max(
                difficulty_counts[2].get(1, 0),
                difficulty_counts[2].get(3, 0),
            ),
        )

    def test_obstacle_budgets_and_clearance_rules(self) -> None:
        spawn_x, spawn_y = PLAYER_SPAWN_CELL
        spawn_zone = {
            (x, y)
            for x in range(spawn_x - 1, spawn_x + 2)
            for y in range(spawn_y - 1, spawn_y + 2)
        }
        for level_number in (1, 2, 3):
            cell_low, cell_high = OBSTACLE_CELL_RANGE[level_number]
            group_low, group_high = SECONDARY_GROUP_COUNT_RANGE[level_number]
            for seed in range(20):
                level = Level(level_number, seed=seed)
                for room in level.rooms:
                    blocked = {
                        (cell_x, cell_y)
                        for obstacle in room.obstacles
                        for cell_x in range(
                            (obstacle.rect.left - room.rect.left) // TILE_SIZE,
                            (obstacle.rect.right - room.rect.left) // TILE_SIZE,
                        )
                        for cell_y in range(
                            (obstacle.rect.top - room.rect.top) // TILE_SIZE,
                            (obstacle.rect.bottom - room.rect.top) // TILE_SIZE,
                        )
                    }
                    self.assertGreaterEqual(len(blocked), cell_low)
                    self.assertLessEqual(len(blocked), cell_high)
                    self.assertIn(
                        room.secondary_group_count,
                        range(group_low, group_high + 1),
                    )
                    self.assertFalse(blocked & spawn_zone)
                    self.assertFalse(blocked & set(room.decal_cells))
                    self.assertTrue(level._has_charge_lane(blocked))
                    self.assertTrue(
                        level._switch_is_occluded_from_spawn(
                            [
                                (
                                    (obstacle.rect.left - room.rect.left) // TILE_SIZE,
                                    (obstacle.rect.top - room.rect.top) // TILE_SIZE,
                                    obstacle.rect.width // TILE_SIZE,
                                    obstacle.rect.height // TILE_SIZE,
                                    obstacle.kind,
                                )
                                for obstacle in room.obstacles
                            ],
                            room.switch_cells[0],
                        )
                    )
                    targets = [room.switch_cells[0]]
                    if room.door_mask & 1:
                        targets.append((16, 1))
                    if room.door_mask & 2:
                        targets.append((30, 9))
                    if room.door_mask & 4:
                        targets.append((16, 16))
                    if room.door_mask & 8:
                        targets.append((1, 9))
                    self.assertTrue(level._has_two_cell_routes(blocked, targets))
                    blocked_with_boxes = blocked | {
                        (
                            (box.rect.centerx - room.rect.left) // TILE_SIZE,
                            (box.rect.centery - room.rect.top) // TILE_SIZE,
                        )
                        for box in room.boxes
                    }
                    self.assertTrue(
                        level._has_two_cell_routes(blocked_with_boxes, targets)
                    )

    def test_pit_clusters_stay_within_confirmed_size(self) -> None:
        groups = [template.solids for template in ROOM_TEMPLATES] + list(
            SECONDARY_PATTERNS
        )
        for group in groups:
            for _, _, width, height, kind in group:
                if kind == "block":
                    self.assertIn(width * height, range(2, 7))

        p02 = next(
            template for template in ROOM_TEMPLATES if template.template_id == "P02"
        )
        self.assertEqual(p02.name, "双侧裂隙")
        self.assertEqual(len(p02.solids), 2)
        self.assertTrue(all(item[4] == "block" for item in p02.solids))

    def test_confirmed_secondary_tag_rules(self) -> None:
        open_patterns = Level._secondary_patterns_for_tags(("open",))
        self.assertEqual(len(open_patterns), 3)
        self.assertTrue(
            all(item[4] != "block" for pattern in open_patterns for item in pattern)
        )

        cover_patterns = Level._secondary_patterns_for_tags(("cover",))
        self.assertEqual(len(cover_patterns), 2)
        for pattern in cover_patterns:
            kinds = {item[4] for item in pattern}
            self.assertGreaterEqual(kinds, {"wall", "pillar"})

        split_patterns = Level._secondary_patterns_for_tags(("split",))
        heavy_patterns = Level._secondary_patterns_for_tags(("cover", "heavy"))
        self.assertEqual(len(split_patterns), 1)
        self.assertEqual(heavy_patterns, split_patterns)
        self.assertTrue(any(item[2] == 3 for item in split_patterns[0]))

        pit_patterns = Level._secondary_patterns_for_tags(("pit",))
        self.assertEqual(len(pit_patterns), 1)
        self.assertTrue(all(item[4] == "block" for item in pit_patterns[0]))
        self.assertEqual(
            Level._secondary_patterns_for_tags(("pit", "open")),
            open_patterns,
        )

    def test_switch_occlusion_ignores_corner_grazes(self) -> None:
        level = Level(1, seed=0)
        switch_cell = (2, 3)
        self.assertFalse(level._switch_is_occluded_from_spawn([], switch_cell))
        self.assertTrue(
            level._switch_is_occluded_from_spawn([(10, 6, 1, 1, "wall")], switch_cell)
        )
        self.assertFalse(
            level._switch_is_occluded_from_spawn([(11, 6, 1, 1, "wall")], switch_cell)
        )

    def test_switch_line_of_sight_regression_seed_is_blocked(self) -> None:
        level = Level(1, seed=0)
        for room in level.rooms:
            solids = [
                (
                    (obstacle.rect.left - room.rect.left) // TILE_SIZE,
                    (obstacle.rect.top - room.rect.top) // TILE_SIZE,
                    obstacle.rect.width // TILE_SIZE,
                    obstacle.rect.height // TILE_SIZE,
                    obstacle.kind,
                )
                for obstacle in room.obstacles
            ]
            self.assertTrue(
                level._switch_is_occluded_from_spawn(solids, room.switch_cells[0]),
                (room.template_id, room.switch_cells[0]),
            )

    def test_single_cell_route_regression_seed_is_rejected(self) -> None:
        level = Level(1, seed=20)
        for room in level.rooms:
            blocked = {
                (cell_x, cell_y)
                for obstacle in room.obstacles
                for cell_x in range(
                    (obstacle.rect.left - room.rect.left) // TILE_SIZE,
                    (obstacle.rect.right - room.rect.left) // TILE_SIZE,
                )
                for cell_y in range(
                    (obstacle.rect.top - room.rect.top) // TILE_SIZE,
                    (obstacle.rect.bottom - room.rect.top) // TILE_SIZE,
                )
            }
            targets = [room.switch_cells[0]]
            self.assertTrue(level._has_two_cell_routes(blocked, targets))

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
        self.assertTrue(all(door.opening_timer > 0 for door in level.doors_of(0)))
        level.update_animations(0.3)
        self.assertTrue(all(door.opening_timer == 0 for door in level.doors_of(0)))

    def test_transition_places_player_inside_connected_room(self) -> None:
        level = Level(2, rng=random.Random(3))
        old_room = level.rooms[0]
        new_room = level.rooms[1]
        position = pygame.Vector2(new_room.rect.center)
        placed = level.place_inside_room(position, 24, 0, 1)
        self.assertTrue(new_room.rect.contains(pygame.Rect(placed.x, placed.y, 24, 24)))
        self.assertNotEqual(old_room.coord, new_room.coord)

    def test_boss_room_has_fixed_arena_and_spawn(self) -> None:
        level = Level(3, boss_only=True, rng=random.Random(1))
        self.assertEqual(len(level.rooms), 1)
        self.assertFalse(level.doors)
        room = level.rooms[0]
        self.assertTrue(room.is_boss)
        self.assertTrue(room.lit)
        self.assertFalse(room.zombies)
        self.assertFalse(room.boxes)
        self.assertIsNone(room.switch)
        self.assertEqual(len(room.obstacles), 4)
        self.assertIsNotNone(room.boss_spawn)
        player_rect = pygame.Rect(room.spawn.x, room.spawn.y, PLAYER_SIZE, PLAYER_SIZE)
        boss_rect = pygame.Rect(
            room.boss_spawn.x, room.boss_spawn.y, BOSS_SIZE, BOSS_SIZE
        )
        self.assertEqual(player_rect.collidelist(room.static_blockers()), -1)
        self.assertEqual(boss_rect.collidelist(room.static_blockers()), -1)
        self.assertGreaterEqual(
            pygame.Vector2(player_rect.center).distance_to(boss_rect.center),
            6 * TILE_SIZE,
        )

    def test_outer_walls_sit_outside_full_playable_grid(self) -> None:
        room = Level(3, boss_only=True, seed=1).rooms[0]
        self.assertEqual(room.rect.size, (ROOM_WIDTH, ROOM_HEIGHT))
        self.assertEqual(room.rect.size, (32 * TILE_SIZE, 18 * TILE_SIZE))
        wall_envelope = room.walls[0].unionall(room.walls[1:])
        self.assertEqual(wall_envelope.size, (34 * TILE_SIZE, 20 * TILE_SIZE))
        self.assertEqual(wall_envelope.left, room.rect.left - TILE_SIZE)
        self.assertEqual(wall_envelope.top, room.rect.top - TILE_SIZE)


if __name__ == "__main__":
    unittest.main()

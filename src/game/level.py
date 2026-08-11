import random
from collections import deque
from collections.abc import Callable

import pygame

from .config import (
    BOSS_SIZE,
    BOX_EXTRA_RANGE,
    BOX_HP,
    BOX_SIZE,
    DOOR_WIDTH,
    OBSTACLE_CELL_RANGE,
    PLAYER_SIZE,
    ROOM_COUNT_RANGE,
    ROOM_GRID_HEIGHT,
    ROOM_GRID_WIDTH,
    ROOM_HEIGHT,
    ROOM_TOP_OFFSET,
    ROOM_WIDTH,
    SECONDARY_GROUP_COUNT_RANGE,
    SWITCH_COLOR,
    SWITCH_COLOR_ACTIVE,
    SWITCH_SIZE,
    TILE_SIZE,
    WALL_THICKNESS,
    WINDOW_HEIGHT,
    ZOMBIE_SPAWN_GAP,
)
from .room_templates import (
    BOSS_DECAL_CELLS,
    BOSS_OBSTACLES,
    BOSS_SPAWN_CELL,
    PLAYER_SPAWN_CELL,
    ROOM_TEMPLATES,
    SECONDARY_LIGHT_COVER_PATTERN,
    SECONDARY_LONG_COVER_PATTERN,
    SECONDARY_PATTERNS,
    SECONDARY_PIT_PATTERN,
    SECONDARY_SHORT_WALL_PATTERN,
    transform_cell,
    transform_rect,
)

NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8

DIRECTIONS = (
    ((0, -1), NORTH, SOUTH),
    ((1, 0), EAST, WEST),
    ((0, 1), SOUTH, NORTH),
    ((-1, 0), WEST, EAST),
)


class Door:
    def __init__(self, rect: pygame.Rect, rooms: tuple[int, int]) -> None:
        self.rect = rect
        self.rooms = rooms
        self.open = True
        self.opening_timer = 0.0

    def set_open(self, open_state: bool) -> None:
        if open_state and not self.open:
            self.opening_timer = 0.25
        self.open = open_state

    def update(self, dt: float) -> None:
        self.opening_timer = max(0.0, self.opening_timer - dt)

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        color = (60, 160, 80) if self.open else (110, 80, 60)
        pygame.draw.rect(surface, color, self.rect.move(-cam_x, -cam_y))


class Obstacle:
    def __init__(self, rect: pygame.Rect, kind: str) -> None:
        self.rect = rect
        self.kind = kind


class Box:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.hp = BOX_HP

    def hit(self, damage: int) -> bool:
        self.hp -= damage
        return self.hp <= 0


class Switch:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.active = False

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        color = SWITCH_COLOR_ACTIVE if self.active else SWITCH_COLOR
        center = (self.rect.centerx - cam_x, self.rect.centery - cam_y)
        pygame.draw.circle(surface, color, center, self.rect.width // 2)


class Room:
    def __init__(
        self,
        index: int,
        coord: tuple[int, int],
        rect: pygame.Rect,
        walls: list[pygame.Rect],
        spawn: pygame.Vector2,
        template_id: str,
        enemy_cells: list[tuple[int, int]],
        crate_cells: list[tuple[int, int]],
        switch_cells: list[tuple[int, int]],
        decal_cells: list[tuple[int, int]],
        *,
        is_boss: bool = False,
        visual_seed: int = 0,
        template_difficulty: int = 0,
        template_tags: tuple[str, ...] = (),
        secondary_group_count: int = 0,
        door_mask: int = 0,
    ) -> None:
        self.index = index
        self.coord = coord
        self.rect = rect
        self.walls = walls
        self.spawn = spawn
        self.template_id = template_id
        self.enemy_cells = enemy_cells
        self.crate_cells = crate_cells
        self.switch_cells = switch_cells
        self.decal_cells = decal_cells
        self.obstacles: list[Obstacle] = []
        self.boxes: list[Box] = []
        self.zombies = []
        self.switch: Switch | None = None
        self.lit = is_boss
        self.is_boss = is_boss
        self.visual_seed = visual_seed
        self.template_difficulty = template_difficulty
        self.template_tags = template_tags
        self.secondary_group_count = secondary_group_count
        self.door_mask = door_mask
        self.boss_spawn: pygame.Vector2 | None = None

    @property
    def cleared(self) -> bool:
        return len(self.zombies) == 0

    def terrain_blockers(self) -> list[pygame.Rect]:
        return self.walls + [obstacle.rect for obstacle in self.obstacles]

    def static_blockers(self) -> list[pygame.Rect]:
        return self.terrain_blockers() + [box.rect for box in self.boxes]

    def clamp_rect(self, rect: pygame.Rect) -> pygame.Rect:
        rect.left = max(rect.left, self.rect.left)
        rect.right = min(rect.right, self.rect.right)
        rect.top = max(rect.top, self.rect.top)
        rect.bottom = min(rect.bottom, self.rect.bottom)
        return rect


class Level:
    def __init__(
        self,
        level_number: int,
        *,
        boss_only: bool = False,
        rng: random.Random | None = None,
        seed: int | None = None,
    ) -> None:
        self.level_number = level_number
        if rng is None:
            self.seed = random.randrange(2**63) if seed is None else seed
            self.rng = random.Random(self.seed)
        else:
            self.seed = seed
            self.rng = rng
        self.rooms: list[Room] = []
        self.doors: list[Door] = []
        if boss_only:
            self._build_boss_room()
        else:
            self._build()

    def _build_boss_room(self) -> None:
        top = (WINDOW_HEIGHT - ROOM_HEIGHT) // 2 + ROOM_TOP_OFFSET
        rect = pygame.Rect(0, top, ROOM_WIDTH, ROOM_HEIGHT)
        walls = self._build_walls(rect, 0)
        spawn = self._spawn_position(rect)
        room = Room(
            0,
            (0, 0),
            rect,
            walls,
            spawn,
            "B01",
            [],
            [],
            [],
            list(BOSS_DECAL_CELLS),
            is_boss=True,
            visual_seed=self.rng.randrange(2**31),
            template_difficulty=3,
            template_tags=("boss", "cover"),
        )
        for cell_x, cell_y, width, height, kind in BOSS_OBSTACLES:
            room.obstacles.append(
                Obstacle(
                    pygame.Rect(
                        rect.left + cell_x * TILE_SIZE,
                        rect.top + cell_y * TILE_SIZE,
                        width * TILE_SIZE,
                        height * TILE_SIZE,
                    ),
                    kind,
                )
            )
        room.boss_spawn = self._position_at_cell(rect, BOSS_SPAWN_CELL, BOSS_SIZE)
        boss_rect = pygame.Rect(room.boss_spawn, (BOSS_SIZE, BOSS_SIZE))
        if boss_rect.collidelist(room.static_blockers()) != -1:
            raise RuntimeError("Boss 出生点与固定障碍重叠")
        self.rooms.append(room)

    def _build(self) -> None:
        low, high = ROOM_COUNT_RANGE[self.level_number]
        coords = self._generate_path(self.rng.randint(low, high))
        coord_to_index = {coord: index for index, coord in enumerate(coords)}
        masks = [0] * len(coords)

        for index, coord in enumerate(coords):
            x, y = coord
            for (dx, dy), own_bit, _ in DIRECTIONS:
                if (x + dx, y + dy) in coord_to_index:
                    masks[index] |= own_bit

        top = (WINDOW_HEIGHT - ROOM_HEIGHT) // 2 + ROOM_TOP_OFFSET
        for index, ((grid_x, grid_y), mask) in enumerate(
            zip(coords, masks, strict=True)
        ):
            rect = pygame.Rect(
                grid_x * ROOM_WIDTH,
                top + grid_y * ROOM_HEIGHT,
                ROOM_WIDTH,
                ROOM_HEIGHT,
            )
            adjacent_ids = {
                self.rooms[coord_to_index[neighbor]].template_id
                for (dx, dy), _, _ in DIRECTIONS
                if (neighbor := (grid_x + dx, grid_y + dy)) in coord_to_index
                and coord_to_index[neighbor] < index
            }
            template, transform, solids, switch_cell, group_count = self._choose_layout(
                mask, adjacent_ids
            )
            blocked_cells = self._blocked_cells(solids)
            decal_cells = [
                transform_cell(cell, transform)
                for cell in template.decal_cells
                if transform_cell(cell, transform) not in blocked_cells
            ]
            room = Room(
                index,
                (grid_x, grid_y),
                rect,
                self._build_walls(rect, mask),
                self._spawn_position(rect),
                template.template_id,
                [
                    transform_cell(cell, transform)
                    for cell in template.enemy_spawn_cells
                ],
                [transform_cell(cell, transform) for cell in template.crate_cells],
                [switch_cell],
                decal_cells,
                visual_seed=self.rng.randrange(2**31),
                template_difficulty=template.difficulty,
                template_tags=template.tags,
                secondary_group_count=group_count,
                door_mask=mask,
            )
            for cell_x, cell_y, width, height, kind in solids:
                obstacle_rect = pygame.Rect(
                    rect.left + cell_x * TILE_SIZE,
                    rect.top + cell_y * TILE_SIZE,
                    width * TILE_SIZE,
                    height * TILE_SIZE,
                )
                room.obstacles.append(Obstacle(obstacle_rect, kind))
            self.rooms.append(room)

        for index in range(len(coords) - 1):
            self.doors.append(self._make_door(index, index + 1))

        self._place_boxes()
        self._place_switches()

    def _generate_path(self, count: int) -> list[tuple[int, int]]:
        for _ in range(50):
            coords = [(0, 0)]
            while len(coords) < count:
                x, y = coords[-1]
                candidates: list[tuple[int, int]] = []
                for (dx, dy), _, _ in DIRECTIONS:
                    candidate = (x + dx, y + dy)
                    if candidate in coords:
                        continue
                    adjacent = sum(
                        (candidate[0] + nx, candidate[1] + ny) in coords
                        for (nx, ny), _, _ in DIRECTIONS
                    )
                    if adjacent == 1:
                        candidates.append(candidate)
                if not candidates:
                    break
                coords.append(self.rng.choice(candidates))
            if len(coords) == count:
                return coords
        raise RuntimeError("无法生成连通房间路径")

    def _choose_layout(self, door_mask: int, excluded_ids: set[str]):
        difficulty_weights = {
            1: {1: 4, 2: 1},
            2: {1: 1, 2: 3, 3: 1},
            3: {2: 1, 3: 1},
        }[self.level_number]
        templates = [
            template
            for template in ROOM_TEMPLATES
            if template.template_id not in excluded_ids
            and door_mask in template.allowed_door_masks
            and template.difficulty in difficulty_weights
        ]
        weighted = [
            template
            for template in templates
            for _ in range(difficulty_weights[template.difficulty])
        ]
        self.rng.shuffle(weighted)
        transforms = ("identity", "hflip", "vflip", "rot180")
        for template in weighted:
            shuffled_transforms = list(transforms)
            self.rng.shuffle(shuffled_transforms)
            for transform in shuffled_transforms:
                solids = [transform_rect(rect, transform) for rect in template.solids]
                switch_cells = [
                    transform_cell(cell, transform) for cell in template.switch_cells
                ]
                self.rng.shuffle(switch_cells)
                for switch_cell in switch_cells:
                    if not self._layout_is_valid(solids, door_mask, switch_cell):
                        continue
                    result = self._add_secondary_groups(
                        solids,
                        door_mask,
                        switch_cell,
                        template.tags,
                    )
                    if result is not None:
                        enhanced, group_count = result
                        return template, transform, enhanced, switch_cell, group_count
        raise RuntimeError("没有符合门掩码、难度和障碍预算的房间模板")

    def _add_secondary_groups(
        self,
        base_solids: list[tuple[int, int, int, int, str]],
        door_mask: int,
        switch_cell: tuple[int, int],
        tags: tuple[str, ...],
    ) -> tuple[list[tuple[int, int, int, int, str]], int] | None:
        group_low, group_high = SECONDARY_GROUP_COUNT_RANGE[self.level_number]
        preferred = self.rng.randint(group_low, group_high)
        group_counts = [preferred] + [
            count for count in range(group_low, group_high + 1) if count != preferred
        ]
        cell_low, cell_high = OBSTACLE_CELL_RANGE[self.level_number]

        for group_count in group_counts:
            for _ in range(160):
                solids = list(base_solids)
                placed = 0
                while placed < group_count:
                    candidate = self._place_secondary_group(
                        solids,
                        door_mask,
                        switch_cell,
                        tags,
                        cell_high,
                    )
                    if candidate is None:
                        break
                    solids = candidate
                    placed += 1
                occupied = len(self._blocked_cells(solids))
                if (
                    placed == group_count
                    and cell_low <= occupied <= cell_high
                    and self._layout_is_valid(solids, door_mask, switch_cell)
                    and self._switch_is_occluded_from_spawn(solids, switch_cell)
                ):
                    return solids, group_count
        return None

    def _place_secondary_group(
        self,
        solids: list[tuple[int, int, int, int, str]],
        door_mask: int,
        switch_cell: tuple[int, int],
        tags: tuple[str, ...],
        maximum_cells: int,
    ) -> list[tuple[int, int, int, int, str]] | None:
        patterns = self._secondary_patterns_for_tags(tags)
        self.rng.shuffle(patterns)

        occupied = self._blocked_cells(solids)
        for pattern in patterns:
            width = max(x + item_width for x, _, item_width, _, _ in pattern)
            height = max(y + item_height for _, y, _, item_height, _ in pattern)
            anchors = [
                (x, y)
                for y in range(2, ROOM_GRID_HEIGHT - height - 1)
                for x in range(2, ROOM_GRID_WIDTH - width - 1)
            ]
            self.rng.shuffle(anchors)
            for anchor_x, anchor_y in anchors[:80]:
                group = [
                    (
                        anchor_x + x,
                        anchor_y + y,
                        item_width,
                        item_height,
                        kind,
                    )
                    for x, y, item_width, item_height, kind in pattern
                ]
                group_cells = self._blocked_cells(group)
                if occupied & group_cells:
                    continue
                candidate = solids + group
                if len(occupied | group_cells) > maximum_cells:
                    continue
                if self._layout_is_valid(candidate, door_mask, switch_cell):
                    return candidate
        return None

    @staticmethod
    def _secondary_patterns_for_tags(
        tags: tuple[str, ...],
    ) -> list[tuple[tuple[int, int, int, int, str], ...]]:
        if "pit" in tags and "open" in tags:
            return [
                SECONDARY_SHORT_WALL_PATTERN,
                SECONDARY_LIGHT_COVER_PATTERN,
                SECONDARY_LONG_COVER_PATTERN,
            ]
        if "heavy" in tags or "split" in tags:
            return [SECONDARY_LONG_COVER_PATTERN]
        if "cover" in tags:
            return [SECONDARY_LIGHT_COVER_PATTERN, SECONDARY_LONG_COVER_PATTERN]
        if "pit" in tags:
            return [SECONDARY_PIT_PATTERN]
        if "open" in tags:
            return [
                SECONDARY_SHORT_WALL_PATTERN,
                SECONDARY_LIGHT_COVER_PATTERN,
                SECONDARY_LONG_COVER_PATTERN,
            ]
        return list(SECONDARY_PATTERNS)

    @staticmethod
    def _blocked_cells(
        solids: list[tuple[int, int, int, int, str]],
    ) -> set[tuple[int, int]]:
        return {
            (cell_x, cell_y)
            for x, y, width, height, _ in solids
            for cell_x in range(x, x + width)
            for cell_y in range(y, y + height)
        }

    @staticmethod
    def _switch_is_occluded_from_spawn(
        solids: list[tuple[int, int, int, int, str]],
        switch_cell: tuple[int, int],
    ) -> bool:
        spawn_x, spawn_y = PLAYER_SPAWN_CELL
        switch_x, switch_y = switch_cell
        switch_offset = (TILE_SIZE - SWITCH_SIZE) // 2 + SWITCH_SIZE // 2
        line = (
            spawn_x * TILE_SIZE,
            spawn_y * TILE_SIZE,
            switch_x * TILE_SIZE + switch_offset,
            switch_y * TILE_SIZE + switch_offset,
        )
        return any(
            pygame.Rect(
                x * TILE_SIZE,
                y * TILE_SIZE,
                width * TILE_SIZE,
                height * TILE_SIZE,
            )
            .inflate(-2, -2)
            .clipline(line)
            for x, y, width, height, _ in solids
        )

    def _layout_is_valid(
        self,
        solids: list[tuple[int, int, int, int, str]],
        door_mask: int,
        switch_cell: tuple[int, int],
    ) -> bool:
        blocked = self._blocked_cells(solids)
        spawn_x, spawn_y = PLAYER_SPAWN_CELL
        spawn_zone = {
            (x, y)
            for x in range(spawn_x - 1, spawn_x + 2)
            for y in range(spawn_y - 1, spawn_y + 2)
        }
        if blocked & spawn_zone or switch_cell in blocked:
            return False

        door_clearance: set[tuple[int, int]] = set()
        if door_mask & NORTH:
            door_clearance.update((x, y) for x in (15, 16) for y in (1, 2))
        if door_mask & EAST:
            door_clearance.update((x, y) for x in (29, 30) for y in (8, 9))
        if door_mask & SOUTH:
            door_clearance.update((x, y) for x in (15, 16) for y in (15, 16))
        if door_mask & WEST:
            door_clearance.update((x, y) for x in (1, 2) for y in (8, 9))
        if blocked & door_clearance:
            return False

        interior_cells = (ROOM_GRID_WIDTH - 2) * (ROOM_GRID_HEIGHT - 2)
        if interior_cells - len(blocked) < interior_cells * 0.45:
            return False
        if not self._has_charge_lane(blocked):
            return False

        targets = [switch_cell]
        if door_mask & NORTH:
            targets.append((16, 1))
        if door_mask & EAST:
            targets.append((30, 9))
        if door_mask & SOUTH:
            targets.append((16, 16))
        if door_mask & WEST:
            targets.append((1, 9))

        return self._has_two_cell_routes(blocked, targets)

    @classmethod
    def _has_two_cell_routes(
        cls,
        blocked: set[tuple[int, int]],
        targets: list[tuple[int, int]],
    ) -> bool:
        starts = cls._footprints_containing(PLAYER_SPAWN_CELL, blocked)
        if not starts:
            return False
        reachable = set(starts)
        queue = deque(starts)
        while queue:
            x, y = queue.popleft()
            for (dx, dy), _, _ in DIRECTIONS:
                neighbor = (x + dx, y + dy)
                if not (1 <= neighbor[0] <= 29 and 1 <= neighbor[1] <= 15):
                    continue
                if neighbor in reachable or not cls._footprint_is_open(
                    neighbor, blocked
                ):
                    continue
                reachable.add(neighbor)
                queue.append(neighbor)
        return all(
            reachable & cls._footprints_containing(target, blocked)
            for target in targets
        )

    @staticmethod
    def _footprint_is_open(
        top_left: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> bool:
        x, y = top_left
        return all(
            (cell_x, cell_y) not in blocked
            for cell_x in (x, x + 1)
            for cell_y in (y, y + 1)
        )

    @classmethod
    def _footprints_containing(
        cls,
        cell: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> set[tuple[int, int]]:
        cell_x, cell_y = cell
        return {
            (x, y)
            for x in (cell_x - 1, cell_x)
            for y in (cell_y - 1, cell_y)
            if 1 <= x <= 29 and 1 <= y <= 15 and cls._footprint_is_open((x, y), blocked)
        }

    @staticmethod
    def _has_charge_lane(blocked: set[tuple[int, int]]) -> bool:
        minimum_length = 10
        for y in range(1, ROOM_GRID_HEIGHT - 2):
            run = 0
            for x in range(1, ROOM_GRID_WIDTH - 1):
                if (x, y) not in blocked and (x, y + 1) not in blocked:
                    run += 1
                    if run >= minimum_length:
                        return True
                else:
                    run = 0
        for x in range(1, ROOM_GRID_WIDTH - 2):
            run = 0
            for y in range(1, ROOM_GRID_HEIGHT - 1):
                if (x, y) not in blocked and (x + 1, y) not in blocked:
                    run += 1
                    if run >= minimum_length:
                        return True
                else:
                    run = 0
        return False

    def _spawn_position(self, rect: pygame.Rect) -> pygame.Vector2:
        return self._position_at_cell(rect, PLAYER_SPAWN_CELL, PLAYER_SIZE)

    @staticmethod
    def _position_at_cell(
        rect: pygame.Rect,
        cell: tuple[int, int],
        size: int,
    ) -> pygame.Vector2:
        cell_x, cell_y = cell
        return pygame.Vector2(
            rect.left + cell_x * TILE_SIZE - size // 2,
            rect.top + cell_y * TILE_SIZE - size // 2,
        )

    def _build_walls(self, rect: pygame.Rect, door_mask: int) -> list[pygame.Rect]:
        walls: list[pygame.Rect] = []
        half_door = DOOR_WIDTH // 2
        t = WALL_THICKNESS

        def horizontal(y: int, has_door: bool) -> None:
            if not has_door:
                walls.append(pygame.Rect(rect.left - t, y, rect.width + 2 * t, t))
                return
            gap_left = rect.centerx - half_door
            gap_right = rect.centerx + half_door
            walls.append(pygame.Rect(rect.left - t, y, gap_left - rect.left + t, t))
            walls.append(pygame.Rect(gap_right, y, rect.right + t - gap_right, t))

        def vertical(x: int, has_door: bool) -> None:
            if not has_door:
                walls.append(pygame.Rect(x, rect.top, t, rect.height))
                return
            gap_top = rect.centery - half_door
            gap_bottom = rect.centery + half_door
            walls.append(pygame.Rect(x, rect.top, t, gap_top - rect.top))
            walls.append(pygame.Rect(x, gap_bottom, t, rect.bottom - gap_bottom))

        horizontal(rect.top - t, bool(door_mask & NORTH))
        horizontal(rect.bottom, bool(door_mask & SOUTH))
        vertical(rect.left - t, bool(door_mask & WEST))
        vertical(rect.right, bool(door_mask & EAST))
        return walls

    def _make_door(self, first: int, second: int) -> Door:
        first_room = self.rooms[first]
        second_room = self.rooms[second]
        dx = second_room.coord[0] - first_room.coord[0]
        dy = second_room.coord[1] - first_room.coord[1]
        t = WALL_THICKNESS
        if dx == 1:
            rect = pygame.Rect(
                first_room.rect.right - t,
                first_room.rect.centery - DOOR_WIDTH // 2,
                2 * t,
                DOOR_WIDTH,
            )
        elif dx == -1:
            rect = pygame.Rect(
                first_room.rect.left - t,
                first_room.rect.centery - DOOR_WIDTH // 2,
                2 * t,
                DOOR_WIDTH,
            )
        elif dy == 1:
            rect = pygame.Rect(
                first_room.rect.centerx - DOOR_WIDTH // 2,
                first_room.rect.bottom - t,
                DOOR_WIDTH,
                2 * t,
            )
        else:
            rect = pygame.Rect(
                first_room.rect.centerx - DOOR_WIDTH // 2,
                first_room.rect.top - t,
                DOOR_WIDTH,
                2 * t,
            )
        return Door(rect, (first, second))

    def _cell_rect(self, room: Room, cell: tuple[int, int], size: int) -> pygame.Rect:
        x, y = cell
        return pygame.Rect(
            room.rect.left + x * TILE_SIZE + (TILE_SIZE - size) // 2,
            room.rect.top + y * TILE_SIZE + (TILE_SIZE - size) // 2,
            size,
            size,
        )

    def _place_boxes(self) -> None:
        low, high = BOX_EXTRA_RANGE[self.level_number]
        counts = [1] * len(self.rooms)
        for _ in range(self.rng.randint(low, high)):
            counts[self.rng.randrange(len(counts))] += 1

        for room, count in zip(self.rooms, counts, strict=True):
            cells = room.crate_cells.copy()
            self.rng.shuffle(cells)
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
            for cell in cells:
                if len(room.boxes) >= count:
                    break
                rect = self._cell_rect(room, cell, BOX_SIZE)
                if rect.collidelist(room.static_blockers()) != -1:
                    continue
                if not self._has_two_cell_routes(
                    blocked | {cell}, self._room_route_targets(room)
                ):
                    continue
                room.boxes.append(Box(rect))
                blocked.add(cell)
            if len(room.boxes) != count:
                raise RuntimeError("房间没有足够的箱子候选点")

    @staticmethod
    def _room_route_targets(room: Room) -> list[tuple[int, int]]:
        targets = [room.switch_cells[0]]
        if room.door_mask & NORTH:
            targets.append((16, 1))
        if room.door_mask & EAST:
            targets.append((30, 9))
        if room.door_mask & SOUTH:
            targets.append((16, 16))
        if room.door_mask & WEST:
            targets.append((1, 9))
        return targets

    def _place_switches(self) -> None:
        for room in self.rooms:
            for cell in room.switch_cells:
                rect = self._cell_rect(room, cell, SWITCH_SIZE)
                if rect.collidelist(room.static_blockers()) == -1:
                    room.switch = Switch(rect)
                    break
            if room.switch is None:
                raise RuntimeError("房间没有可用的机关位置")

    def spawn_zombies(
        self,
        count_range: tuple[int, int],
        create: Callable,
    ) -> None:
        if not self.rooms:
            return
        low, high = count_range
        counts = [self.rng.randint(low, high) for _ in self.rooms]

        for room, room_count in zip(self.rooms, counts, strict=True):
            candidates = room.enemy_cells.copy()
            self.rng.shuffle(candidates)
            attempts = 0
            while len(room.zombies) < room_count and attempts < 200:
                attempts += 1
                if candidates:
                    cell = candidates.pop()
                else:
                    cell = (
                        self.rng.randint(3, ROOM_GRID_WIDTH - 4),
                        self.rng.randint(3, ROOM_GRID_HEIGHT - 4),
                    )
                zombie = create(pygame.Vector2())
                zombie.pos.update(
                    room.rect.left
                    + cell[0] * TILE_SIZE
                    + (TILE_SIZE - zombie.size) / 2,
                    room.rect.top + cell[1] * TILE_SIZE + (TILE_SIZE - zombie.size) / 2,
                )
                if zombie.rect.collidelist(room.static_blockers()) != -1:
                    continue
                if (
                    pygame.Vector2(zombie.rect.center).distance_to(
                        pygame.Vector2(room.spawn) + pygame.Vector2(PLAYER_SIZE / 2)
                    )
                    < 6 * TILE_SIZE
                ):
                    continue
                if any(
                    pygame.Vector2(zombie.rect.center).distance_to(other.rect.center)
                    < zombie.separation_radius
                    + other.separation_radius
                    + ZOMBIE_SPAWN_GAP
                    for other in room.zombies
                ):
                    continue
                room.zombies.append(zombie)
            if len(room.zombies) != room_count:
                raise RuntimeError("房间没有足够的敌人出生点")

    def doors_of(self, room_index: int) -> list[Door]:
        return [door for door in self.doors if room_index in door.rooms]

    def blockers_for(self, room_index: int) -> list[pygame.Rect]:
        room = self.rooms[room_index]
        closed_doors = [
            door.rect for door in self.doors_of(room_index) if not door.open
        ]
        return room.static_blockers() + closed_doors

    def projectile_blockers_for(self, room_index: int) -> list[pygame.Rect]:
        room = self.rooms[room_index]
        closed_doors = [
            door.rect for door in self.doors_of(room_index) if not door.open
        ]
        return room.terrain_blockers() + closed_doors

    def update_doors(self, current_room: int) -> None:
        for door in self.doors_of(current_room):
            door.set_open(self.rooms[current_room].cleared)

    def update_animations(self, dt: float) -> None:
        for door in self.doors:
            door.update(dt)

    def room_at(self, point: tuple[float, float], current_room: int) -> int:
        for room in self.rooms:
            if room.index != current_room and room.rect.collidepoint(point):
                return room.index
        return current_room

    def place_inside_room(
        self,
        position: pygame.Vector2,
        player_size: int,
        old_room: int,
        new_room: int,
    ) -> pygame.Vector2:
        old = self.rooms[old_room]
        new = self.rooms[new_room]
        result = pygame.Vector2(position)
        padding = WALL_THICKNESS + 4
        dx = new.coord[0] - old.coord[0]
        dy = new.coord[1] - old.coord[1]
        if dx == 1:
            result.x = new.rect.left + padding
        elif dx == -1:
            result.x = new.rect.right - padding - player_size
        elif dy == 1:
            result.y = new.rect.top + padding
        elif dy == -1:
            result.y = new.rect.bottom - padding - player_size
        return result

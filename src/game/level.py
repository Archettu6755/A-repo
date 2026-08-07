import random
from collections import deque
from collections.abc import Callable

import pygame

from .config import (
    BOX_EXTRA_RANGE,
    BOX_HP,
    BOX_SIZE,
    DOOR_WIDTH,
    PLAYER_SIZE,
    ROOM_COUNT_RANGE,
    ROOM_GRID_HEIGHT,
    ROOM_GRID_WIDTH,
    ROOM_HEIGHT,
    ROOM_TOP_OFFSET,
    ROOM_WIDTH,
    SWITCH_COLOR,
    SWITCH_COLOR_ACTIVE,
    SWITCH_SIZE,
    TILE_SIZE,
    WALL_THICKNESS,
    WINDOW_HEIGHT,
    ZOMBIE_SPAWN_GAP,
)
from .room_templates import (
    BOSS_EXIT_SWITCH_CELL,
    CRATE_CELLS,
    ENEMY_CELLS,
    PLAYER_SPAWN_CELL,
    ROOM_TEMPLATES,
    SWITCH_CELLS,
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
        *,
        is_boss: bool = False,
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
        self.obstacles: list[Obstacle] = []
        self.boxes: list[Box] = []
        self.zombies = []
        self.switch: Switch | None = None
        self.lit = is_boss
        self.is_boss = is_boss
        self.boss_spawn = None

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
    ) -> None:
        self.level_number = level_number
        self.rng = rng or random.Random()
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
        self.rooms.append(
            Room(
                0,
                (0, 0),
                rect,
                walls,
                spawn,
                "BOSS_PLACEHOLDER",
                [],
                [],
                [BOSS_EXIT_SWITCH_CELL],
                is_boss=True,
            )
        )
        self._place_switches()

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
            template, transform, solids, switch_cell = self._choose_layout(mask)
            room = Room(
                index,
                (grid_x, grid_y),
                rect,
                self._build_walls(rect, mask),
                self._spawn_position(rect),
                template.template_id,
                [transform_cell(cell, transform) for cell in ENEMY_CELLS],
                [transform_cell(cell, transform) for cell in CRATE_CELLS],
                [switch_cell],
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

    def _choose_layout(self, door_mask: int):
        choices = [
            (template, transform)
            for template in ROOM_TEMPLATES
            for transform in ("identity", "hflip", "vflip", "rot180")
        ]
        self.rng.shuffle(choices)
        for template, transform in choices:
            solids = [transform_rect(rect, transform) for rect in template.solids]
            switch_cells = [transform_cell(cell, transform) for cell in SWITCH_CELLS]
            self.rng.shuffle(switch_cells)
            for switch_cell in switch_cells:
                if self._layout_is_valid(solids, door_mask, switch_cell):
                    return template, transform, solids, switch_cell
        raise RuntimeError("没有符合门掩码的房间模板")

    def _layout_is_valid(
        self,
        solids: list[tuple[int, int, int, int, str]],
        door_mask: int,
        switch_cell: tuple[int, int],
    ) -> bool:
        blocked = {
            (cell_x, cell_y)
            for x, y, width, height, _ in solids
            for cell_x in range(x, x + width)
            for cell_y in range(y, y + height)
        }
        if PLAYER_SPAWN_CELL in blocked or switch_cell in blocked:
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

        reachable = {PLAYER_SPAWN_CELL}
        queue = deque([PLAYER_SPAWN_CELL])
        while queue:
            x, y = queue.popleft()
            for (dx, dy), _, _ in DIRECTIONS:
                neighbor = (x + dx, y + dy)
                if not (1 <= neighbor[0] < 31 and 1 <= neighbor[1] < 17):
                    continue
                if neighbor in blocked or neighbor in reachable:
                    continue
                reachable.add(neighbor)
                queue.append(neighbor)
        return all(target in reachable for target in targets)

    def _spawn_position(self, rect: pygame.Rect) -> pygame.Vector2:
        cell_x, cell_y = PLAYER_SPAWN_CELL
        return pygame.Vector2(
            rect.left + cell_x * TILE_SIZE - PLAYER_SIZE // 2,
            rect.top + cell_y * TILE_SIZE - PLAYER_SIZE // 2,
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
            for cell in cells:
                if len(room.boxes) >= count:
                    break
                rect = self._cell_rect(room, cell, BOX_SIZE)
                if rect.collidelist(room.static_blockers()) != -1:
                    continue
                room.boxes.append(Box(rect))
            if len(room.boxes) != count:
                raise RuntimeError("房间没有足够的箱子候选点")

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
            door.open = self.rooms[current_room].cleared

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

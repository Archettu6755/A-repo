import random

import pygame

from .config import (
    BOX_COLOR,
    BOX_COUNT_RANGE,
    BOX_HP,
    BOX_SIZE,
    BOX_SIZE_VARIATION,
    OBSTACLE_BORDER,
    OBSTACLE_COLORS,
    OBSTACLE_COUNT_RANGE,
    OBSTACLE_KINDS,
    OBSTACLE_MARGIN,
    OBSTACLE_SIZE_VARIATION,
    OBSTACLE_SIZES,
    ROOM_COUNT_RANGE,
    ROOM_HEIGHT,
    ROOM_TOP_OFFSET,
    ROOM_WIDTH,
    SWITCH_COLOR,
    SWITCH_COLOR_ACTIVE,
    SWITCH_SIZE,
    WALL_THICKNESS,
    WINDOW_HEIGHT,
    ZOMBIE_SPAWN_MARGIN,
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

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, OBSTACLE_COLORS[self.kind], self.rect)
        pygame.draw.rect(surface, OBSTACLE_BORDER, self.rect, 2)


class Box:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.hp = BOX_HP

    def hit(self, damage: int) -> bool:
        self.hp -= damage
        return self.hp <= 0

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BOX_COLOR, self.rect)


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
        rect: pygame.Rect,
        walls: list[pygame.Rect],
        spawn: pygame.Vector2,
    ) -> None:
        self.rect = rect
        self.walls = walls
        self.spawn = spawn
        self.obstacles: list[Obstacle] = []
        self.boxes: list[Box] = []
        self.zombies = []
        self.switch: Switch | None = None
        self.lit = False

    @property
    def cleared(self) -> bool:
        return len(self.zombies) == 0

    def all_blockers(self) -> list[pygame.Rect]:
        return (
            self.walls + [o.rect for o in self.obstacles] + [b.rect for b in self.boxes]
        )

    def clamp_rect(self, rect: pygame.Rect) -> pygame.Rect:
        rect.left = max(rect.left, self.rect.left)
        rect.right = min(rect.right, self.rect.right)
        rect.top = max(rect.top, self.rect.top)
        rect.bottom = min(rect.bottom, self.rect.bottom)
        return rect

    def random_position(
        self,
        margin: int = 30,
        avoid: list[pygame.Rect] | None = None,
        avoid_margin: int = 40,
    ) -> pygame.Vector2:
        avoid = avoid or []
        for _ in range(100):
            pos = pygame.Vector2(
                random.randint(self.rect.left + margin, self.rect.right - margin),
                random.randint(self.rect.top + margin, self.rect.bottom - margin),
            )
            rect = pygame.Rect(0, 0, 1, 1).move(pos)
            if any(
                rect.inflate(avoid_margin, avoid_margin).colliderect(r) for r in avoid
            ):
                continue
            return pos
        return pygame.Vector2(
            (self.rect.left + self.rect.right) // 2,
            (self.rect.top + self.rect.bottom) // 2,
        )


class Level:
    def __init__(self, level_number: int) -> None:
        self.level_number = level_number
        self.rooms: list[Room] = []
        self.doors: list[Door] = []
        self._build()

    def _build(self) -> None:
        room_count = random.randint(*ROOM_COUNT_RANGE)
        top = (WINDOW_HEIGHT - ROOM_HEIGHT) // 2 + ROOM_TOP_OFFSET
        t = WALL_THICKNESS

        rects: list[pygame.Rect] = []
        x = 0
        for _ in range(room_count):
            rects.append(pygame.Rect(x, top, ROOM_WIDTH, ROOM_HEIGHT))
            x += ROOM_WIDTH

        for i in range(room_count - 1):
            rect = rects[i]
            door_rect = pygame.Rect(rect.right - t, rect.centery - 26, 2 * t, 52)
            self.doors.append(Door(door_rect, (i, i + 1)))

        for i, rect in enumerate(rects):
            walls = [
                pygame.Rect(rect.left - t, rect.top - t, rect.width + 2 * t, t),
                pygame.Rect(rect.left - t, rect.bottom, rect.width + 2 * t, t),
            ]
            if i == 0:
                walls.append(
                    pygame.Rect(rect.left - t, rect.top, t, rect.height + 2 * t)
                )
            else:
                door_top = rect.centery - 26
                door_bottom = rect.centery + 26
                walls.append(
                    pygame.Rect(rect.left - t, rect.top, t, door_top - rect.top)
                )
                walls.append(
                    pygame.Rect(
                        rect.left - t, door_bottom, t, rect.bottom - door_bottom
                    )
                )
            if i == room_count - 1:
                walls.append(pygame.Rect(rect.right, rect.top, t, rect.height + 2 * t))
            else:
                door_top = rect.centery - 26
                door_bottom = rect.centery + 26
                walls.append(pygame.Rect(rect.right, rect.top, t, door_top - rect.top))
                walls.append(
                    pygame.Rect(rect.right, door_bottom, t, rect.bottom - door_bottom)
                )
            spawn = pygame.Vector2(rect.centerx, rect.centery)
            self.rooms.append(Room(rect, walls, spawn))

        self._place_obstacles()
        self._place_boxes()
        self._place_switches()

    def _vary_size(self, base: tuple[int, int], variation: float) -> tuple[int, int]:
        w, h = base
        return (
            max(16, int(w * random.uniform(1 - variation, 1 + variation))),
            max(16, int(h * random.uniform(1 - variation, 1 + variation))),
        )

    def _place_obstacles(self) -> None:
        low, high = OBSTACLE_COUNT_RANGE[self.level_number]
        total = random.randint(low, high)
        if not self.rooms:
            return
        per_room = total // len(self.rooms)
        remainder = total % len(self.rooms)
        for i, room in enumerate(self.rooms):
            count = per_room + (1 if i < remainder else 0)
            avoid = [pygame.Rect(0, 0, 1, 1).move(room.spawn)] + [
                d.rect for d in self.doors
            ]
            for _ in range(count):
                kind = random.choice(OBSTACLE_KINDS)
                w, h = self._vary_size(OBSTACLE_SIZES[kind], OBSTACLE_SIZE_VARIATION)
                pos = room.random_position(OBSTACLE_MARGIN, avoid, 50)
                rect = pygame.Rect(0, 0, w, h).move(pos)
                if rect.left < room.rect.left or rect.right > room.rect.right:
                    continue
                if rect.top < room.rect.top or rect.bottom > room.rect.bottom:
                    continue
                room.obstacles.append(Obstacle(rect, kind))
                avoid.append(rect)

    def _place_boxes(self) -> None:
        low, high = BOX_COUNT_RANGE[self.level_number]
        for room in self.rooms:
            count = random.randint(low, high)
            avoid = [o.rect for o in room.obstacles] + [d.rect for d in self.doors]
            for _ in range(count):
                w, h = self._vary_size((BOX_SIZE, BOX_SIZE), BOX_SIZE_VARIATION)
                pos = room.random_position(50, avoid, 44)
                room.boxes.append(Box(pygame.Rect(0, 0, w, h).move(pos)))

    def _place_switches(self) -> None:
        for room in self.rooms:
            avoid = (
                [pygame.Rect(0, 0, 1, 1).move(room.spawn)]
                + [o.rect for o in room.obstacles]
                + [b.rect for b in room.boxes]
            )
            pos = room.random_position(70, avoid, 50)
            room.switch = Switch(pygame.Rect(0, 0, SWITCH_SIZE, SWITCH_SIZE).move(pos))

    def spawn_zombies(self, count: int, create) -> None:
        if not self.rooms:
            return
        per_room = count // len(self.rooms)
        remainder = count % len(self.rooms)
        for i, room in enumerate(self.rooms):
            n = per_room + (1 if i < remainder else 0)
            avoid = [o.rect for o in room.obstacles] + [b.rect for b in room.boxes]
            for _ in range(n):
                pos = room.random_position(ZOMBIE_SPAWN_MARGIN, avoid, 50)
                room.zombies.append(create(pos))

    def doors_of(self, room_index: int) -> list[Door]:
        return [d for d in self.doors if room_index in d.rooms]

    def room_at(self, point: pygame.Vector2) -> int:
        for i, room in enumerate(self.rooms):
            if room.rect.collidepoint(point):
                return i
        return 0

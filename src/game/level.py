import random

import pygame

from .config import (
    ROOM_MAX_HEIGHT,
    ROOM_MAX_WIDTH,
    ROOM_MIN_HEIGHT,
    ROOM_MIN_WIDTH,
    WALL_THICKNESS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)


class Room:
    def __init__(self) -> None:
        self.randomize()

    def randomize(self) -> None:
        width = random.randint(ROOM_MIN_WIDTH, ROOM_MAX_WIDTH)
        height = random.randint(ROOM_MIN_HEIGHT, ROOM_MAX_HEIGHT)
        left = (WINDOW_WIDTH - width) // 2
        top = (WINDOW_HEIGHT - height) // 2
        self.rect = pygame.Rect(left, top, width, height)
        self.walls = self._build_walls()

    def _build_walls(self) -> list[pygame.Rect]:
        r = self.rect
        t = WALL_THICKNESS
        return [
            pygame.Rect(r.left - t, r.top - t, r.width + 2 * t, t),
            pygame.Rect(r.left - t, r.bottom, r.width + 2 * t, t),
            pygame.Rect(r.left - t, r.top, t, r.height + 2 * t),
            pygame.Rect(r.right, r.top, t, r.height + 2 * t),
        ]

    def clamp_rect(self, rect: pygame.Rect) -> pygame.Rect:
        rect.left = max(rect.left, self.rect.left)
        rect.right = min(rect.right, self.rect.right)
        rect.top = max(rect.top, self.rect.top)
        rect.bottom = min(rect.bottom, self.rect.bottom)
        return rect

    def random_spawn(self, margin: int = 30) -> pygame.Vector2:
        return pygame.Vector2(
            random.randint(self.rect.left + margin, self.rect.right - margin),
            random.randint(self.rect.top + margin, self.rect.bottom - margin),
        )

    def random_spawn_far_from(
        self, point: pygame.Vector2, min_distance: int = 120
    ) -> pygame.Vector2:
        for _ in range(50):
            pos = self.random_spawn()
            if pos.distance_to(point) >= min_distance:
                return pos
        return self.random_spawn()

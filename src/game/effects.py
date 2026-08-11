from collections.abc import Sequence

import pygame

from .resources import SPRITES


class VisualEffect:
    def __init__(
        self,
        paths: Sequence[str],
        pos: pygame.Vector2,
        size: tuple[int, int],
        duration: float | None,
        room_index: int,
        *,
        anchor: str = "center",
        layer: str = "actor",
    ) -> None:
        self.paths = tuple(paths)
        self.pos = pygame.Vector2(pos)
        self.size = size
        self.duration = duration
        self.room_index = room_index
        self.anchor = anchor
        self.layer = layer
        self.elapsed = 0.0

    @property
    def sort_y(self) -> float:
        return self.pos.y

    def update(self, dt: float) -> bool:
        if self.duration is None:
            return True
        self.elapsed += dt
        return self.elapsed < self.duration

    def draw(
        self,
        surface: pygame.Surface,
        cam_x: float = 0,
        cam_y: float = 0,
    ) -> None:
        if not self.paths:
            return
        if self.duration is None:
            index = 0
        else:
            progress = min(0.999, self.elapsed / self.duration)
            index = min(len(self.paths) - 1, int(progress * len(self.paths)))
        sprite = SPRITES.load(self.paths[index], self.size)
        if sprite is None:
            return
        point = (round(self.pos.x - cam_x), round(self.pos.y - cam_y))
        if self.anchor == "midbottom":
            rect = sprite.get_rect(midbottom=point)
        else:
            rect = sprite.get_rect(center=point)
        surface.blit(sprite, rect)


def numbered_paths(prefix: str, frames: int) -> tuple[str, ...]:
    return tuple(f"{prefix}_{index}.png" for index in range(frames))

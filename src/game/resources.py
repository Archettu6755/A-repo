from pathlib import Path

import pygame

ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets"


class SpriteLibrary:
    def __init__(self, root: Path = ASSET_ROOT) -> None:
        self.root = root
        self._cache: dict[tuple[str, tuple[int, int]], pygame.Surface | None] = {}
        self._native_cache: dict[str, pygame.Surface | None] = {}
        self._panel_cache: dict[
            tuple[str, tuple[int, int], int], pygame.Surface | None
        ] = {}

    def load_native(self, relative_path: str) -> pygame.Surface | None:
        if relative_path in self._native_cache:
            return self._native_cache[relative_path]
        path = self.root / relative_path
        if not path.is_file():
            self._native_cache[relative_path] = None
            return None
        try:
            image = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        except pygame.error:
            image = None
        self._native_cache[relative_path] = image
        return image

    def load(self, relative_path: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = relative_path, size
        if key in self._cache:
            return self._cache[key]
        source = self.load_native(relative_path)
        image = None if source is None else source
        if image is not None and image.get_size() != size:
            image = pygame.transform.scale(image, size)
        self._cache[key] = image
        return image

    def panel(
        self,
        relative_path: str,
        size: tuple[int, int],
        border: int = 12,
    ) -> pygame.Surface | None:
        key = relative_path, size, border
        if key in self._panel_cache:
            return self._panel_cache[key]
        source = self.load_native(relative_path)
        if source is None:
            self._panel_cache[key] = None
            return None
        border = min(border, source.get_width() // 2, source.get_height() // 2)
        target = pygame.Surface(size, pygame.SRCALPHA)
        source_width, source_height = source.get_size()
        target_width, target_height = size
        source_parts = (
            (0, 0, border, border),
            (border, 0, source_width - border * 2, border),
            (source_width - border, 0, border, border),
            (0, border, border, source_height - border * 2),
            (
                border,
                border,
                source_width - border * 2,
                source_height - border * 2,
            ),
            (
                source_width - border,
                border,
                border,
                source_height - border * 2,
            ),
            (0, source_height - border, border, border),
            (
                border,
                source_height - border,
                source_width - border * 2,
                border,
            ),
            (source_width - border, source_height - border, border, border),
        )
        target_parts = (
            (0, 0, border, border),
            (border, 0, target_width - border * 2, border),
            (target_width - border, 0, border, border),
            (0, border, border, target_height - border * 2),
            (
                border,
                border,
                target_width - border * 2,
                target_height - border * 2,
            ),
            (
                target_width - border,
                border,
                border,
                target_height - border * 2,
            ),
            (0, target_height - border, border, border),
            (
                border,
                target_height - border,
                target_width - border * 2,
                border,
            ),
            (target_width - border, target_height - border, border, border),
        )
        for source_rect, target_rect in zip(source_parts, target_parts, strict=True):
            part = source.subsurface(source_rect)
            if part.get_size() != target_rect[2:]:
                part = pygame.transform.scale(part, target_rect[2:])
            target.blit(part, target_rect[:2])
        self._panel_cache[key] = target
        return target


class RoomArt:
    def __init__(self, sprites: SpriteLibrary) -> None:
        self.sprites = sprites
        self._floor_cache: dict[tuple[int, str, tuple[int, int]], pygame.Surface] = {}

    def floor(
        self,
        level: int,
        template_id: str,
        size: tuple[int, int],
    ) -> pygame.Surface:
        key = level, template_id, size
        if key in self._floor_cache:
            return self._floor_cache[key]
        choices = {
            1: ("floor_01.png", "floor_02.png"),
            2: ("floor_02.png", "floor_03.png"),
            3: ("floor_03.png", "floor_04.png"),
        }[level]
        seed = sum(ord(character) for character in template_id)
        result = pygame.Surface(size)
        for y in range(0, size[1], 32):
            for x in range(0, size[0], 32):
                variant = ((x // 32) * 3 + (y // 32) * 5 + seed) % 9 == 0
                tile = self.sprites.load(
                    f"environment/shared/{choices[int(variant)]}",
                    (32, 32),
                )
                if tile is not None:
                    result.blit(tile, (x, y))
        tint = {1: (150, 160, 166), 2: (132, 145, 154), 3: (118, 132, 142)}[level]
        result.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        grid_color = {1: (52, 61, 66), 2: (44, 53, 60), 3: (38, 47, 54)}[level]
        for x in range(0, size[0], 32):
            pygame.draw.line(result, grid_color, (x, 0), (x, size[1]))
        for y in range(0, size[1], 32):
            pygame.draw.line(result, grid_color, (0, y), (size[0], y))
        self._floor_cache[key] = result
        return result


SPRITES = SpriteLibrary()
ROOM_ART = RoomArt(SPRITES)

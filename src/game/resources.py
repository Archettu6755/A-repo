from pathlib import Path

import pygame

ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets"


class SpriteLibrary:
    def __init__(self, root: Path = ASSET_ROOT) -> None:
        self.root = root
        self._cache: dict[tuple[str, tuple[int, int]], pygame.Surface | None] = {}

    def load(self, relative_path: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = relative_path, size
        if key in self._cache:
            return self._cache[key]
        path = self.root / relative_path
        if not path.is_file():
            self._cache[key] = None
            return None
        try:
            image = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            if image.get_size() != size:
                image = pygame.transform.scale(image, size)
        except pygame.error:
            image = None
        self._cache[key] = image
        return image


SPRITES = SpriteLibrary()

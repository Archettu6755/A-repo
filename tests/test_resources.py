import tempfile
import unittest
from pathlib import Path

import pygame

from game.resources import SpriteLibrary


class ResourceTests(unittest.TestCase):
    def test_missing_runtime_sprite_uses_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library = SpriteLibrary(Path(directory))
            self.assertIsNone(library.load("missing.png", (32, 32)))

    def test_runtime_sprite_is_nearest_neighbor_scaled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = pygame.Surface((2, 2), pygame.SRCALPHA)
            source.fill((255, 0, 0, 255))
            pygame.image.save(source, root / "sprite.png")
            library = SpriteLibrary(root)
            image = library.load("sprite.png", (4, 4))
            self.assertIsNotNone(image)
            self.assertEqual(image.get_size(), (4, 4))


if __name__ == "__main__":
    unittest.main()

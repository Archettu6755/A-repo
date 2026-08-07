import tempfile
import unittest
from pathlib import Path

import pygame

from game.resources import ASSET_ROOT, SpriteLibrary


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

    def test_required_runtime_art_is_present_and_loadable(self) -> None:
        expected = {
            "environment/shared/floor_01.png": (32, 32),
            "environment/shared/floor_02.png": (32, 32),
            "environment/shared/floor_03.png": (32, 32),
            "environment/shared/floor_04.png": (32, 32),
            "environment/shared/wall.png": (64, 48),
            "environment/shared/wall_broken.png": (64, 48),
            "environment/shared/door_closed.png": (64, 64),
            "environment/shared/door_open.png": (64, 64),
            "environment/shared/pillar.png": (32, 64),
            "environment/shared/low_wall.png": (64, 48),
            "environment/shared/pit.png": (96, 64),
            "props/crate_intact.png": (32, 40),
            "props/crate_damage_01.png": (32, 40),
            "props/crate_damage_02.png": (32, 40),
            "props/switch_off.png": (24, 36),
            "props/switch_on.png": (24, 36),
            "props/coin.png": (16, 16),
            "props/bullet.png": (8, 8),
            "ui/panel.png": (192, 144),
            "ui/hp_frame.png": (256, 32),
            "ui/icon_attack.png": (32, 32),
            "ui/icon_health.png": (32, 32),
            "ui/icon_fire_speed.png": (32, 32),
            "ui/icon_move_speed.png": (32, 32),
            "ui/icon_heal.png": (32, 32),
            "ui/icon_coin.png": (24, 24),
            "ui/title_background.png": (1280, 720),
        }
        directions = ("down", "left", "right", "up")
        characters = {
            "player": ((32, 48), ("idle", "walk", "shoot", "hurt")),
            "zombie_normal": ((32, 48), ("idle", "charge", "stun")),
            "zombie_fast": ((32, 40), ("idle", "charge", "leap", "stun")),
            "zombie_heavy": (
                (48, 56),
                ("idle", "charge_prepare", "charge", "stun"),
            ),
        }
        for character, (size, actions) in characters.items():
            for action in actions:
                for direction in directions:
                    expected[
                        f"characters/{character}/{character}_{action}_{direction}.png"
                    ] = size
        library = SpriteLibrary(ASSET_ROOT)
        for path, size in expected.items():
            image = library.load(path, size)
            self.assertIsNotNone(image, path)
            self.assertEqual(image.get_size(), size, path)
            self.assertGreater(pygame.mask.from_surface(image, 1).count(), 0, path)


if __name__ == "__main__":
    unittest.main()

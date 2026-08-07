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
            "ui/heart_full.png": (24, 24),
            "ui/heart_empty.png": (24, 24),
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

    def test_heart_icons_have_hard_transparent_edges(self) -> None:
        for name in ("heart_full.png", "heart_empty.png"):
            image = pygame.image.load(ASSET_ROOT / "ui" / name)
            self.assertEqual(image.get_size(), (24, 24))
            self.assertEqual(image.get_at((0, 0)).a, 0)
            alphas = {
                image.get_at((x, y)).a
                for x in range(image.get_width())
                for y in range(image.get_height())
            }
            self.assertLessEqual(alphas, {0, 255})

    def test_new_character_and_effect_art_is_present(self) -> None:
        directions = ("down", "left", "right", "up")
        expected: dict[str, tuple[int, int]] = {}
        for phase in (1, 2):
            for action, frames in (("idle", 2), ("charge", 3), ("stun", 2)):
                for direction in directions:
                    expected[
                        f"characters/boss/boss_phase{phase}_{action}_{direction}.png"
                    ] = (80, 88)
                    expected[
                        "characters/boss/"
                        f"boss_phase{phase}_{action}_{direction}_sheet.png"
                    ] = (80 * frames, 88)
        expected["characters/boss/boss_death_sheet.png"] = (80 * 8, 88)

        for direction in directions:
            for frame in range(4):
                expected[f"effects/fx_muzzle_{direction}_{frame}.png"] = (16, 16)
        for name, size in (
            ("fx_bullet_impact", (16, 16)),
            ("fx_charge_warning", (32, 32)),
            ("fx_wall_dust", (24, 24)),
            ("fx_coin_pop", (24, 24)),
        ):
            for frame in range(4):
                expected[f"effects/{name}_{frame}.png"] = size
        for frame in range(5):
            expected[f"effects/fx_crate_debris_{frame}.png"] = (32, 32)
        for frame in range(4):
            expected[f"effects/fx_player_hurt_{frame}.png"] = (32, 48)
        for index in range(1, 9):
            expected[f"effects/blood_{index:02d}.png"] = (32, 32)

        library = SpriteLibrary(ASSET_ROOT)
        for path, size in expected.items():
            image = library.load_native(path)
            self.assertIsNotNone(image, path)
            self.assertEqual(image.get_size(), size, path)
            self.assertEqual(image.get_at((0, 0)).a, 0, path)
            self.assertGreater(pygame.mask.from_surface(image, 1).count(), 0, path)

    def test_theme_decals_and_shop_cards_are_present(self) -> None:
        expected = {
            "environment/checkpoint/floor_clean_01.png": (32, 32),
            "environment/checkpoint/floor_clean_02.png": (32, 32),
            "environment/laboratory/floor_damaged_01.png": (32, 32),
            "environment/laboratory/floor_damaged_02.png": (32, 32),
            "ui/shop_card_normal.png": (160, 208),
            "ui/shop_card_selected.png": (160, 208),
            "ui/shop_card_unavailable.png": (160, 208),
            "ui/shop_card_maxed.png": (160, 208),
        }
        for index in range(1, 7):
            expected[f"environment/checkpoint/marking_{index:02d}.png"] = (32, 32)
        for index in range(1, 5):
            expected[f"environment/laboratory/crack_{index:02d}.png"] = (32, 32)
            expected[f"environment/laboratory/stain_{index:02d}.png"] = (32, 32)

        library = SpriteLibrary(ASSET_ROOT)
        for path, size in expected.items():
            image = library.load_native(path)
            self.assertIsNotNone(image, path)
            self.assertEqual(image.get_size(), size, path)
            self.assertGreater(pygame.mask.from_surface(image, 1).count(), 0, path)

        decal_paths = (
            [f"environment/checkpoint/marking_{index:02d}.png" for index in range(1, 7)]
            + [f"environment/laboratory/crack_{index:02d}.png" for index in range(1, 5)]
            + [f"environment/laboratory/stain_{index:02d}.png" for index in range(1, 5)]
        )
        for path in decal_paths:
            image = pygame.image.load(ASSET_ROOT / path)
            alphas = {
                image.get_at((x, y)).a
                for x in range(image.get_width())
                for y in range(image.get_height())
            }
            self.assertLessEqual(alphas, {0, 255}, path)


if __name__ == "__main__":
    unittest.main()

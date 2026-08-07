import os
import unittest
from unittest.mock import patch

import pygame

from game.fonts import BUNDLED_FONT_PATH, find_cjk_font_path, load_font


class FontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.font.init()

    def test_windows_font_file_is_used_before_system_enumeration(self) -> None:
        expected = os.path.join("C:\\Windows", "Fonts", "msyh.ttc")
        with (
            patch.dict(os.environ, {"WINDIR": "C:\\Windows"}),
            patch(
                "game.fonts.os.path.isfile", side_effect=lambda path: path == expected
            ),
            patch("game.fonts.pygame.font.match_font") as match_font,
        ):
            self.assertEqual(find_cjk_font_path(), expected)
            match_font.assert_not_called()

    def test_bundled_font_is_used_before_system_fonts(self) -> None:
        with patch("game.fonts.pygame.font.match_font") as match_font:
            self.assertEqual(find_cjk_font_path(), BUNDLED_FONT_PATH)
            match_font.assert_not_called()

    def test_bundled_font_renders_chinese_text(self) -> None:
        surface = load_font(24).render("后续内容正在开发", False, "white")
        self.assertGreater(surface.get_width(), 0)
        self.assertGreater(pygame.mask.from_surface(surface, 1).count(), 0)

    def test_broken_system_font_registry_falls_back_without_crashing(self) -> None:
        with (
            patch("game.fonts.os.path.isfile", return_value=False),
            patch("game.fonts.pygame.font.match_font", side_effect=TypeError),
            patch("game.fonts.pygame.font.SysFont", side_effect=TypeError),
        ):
            self.assertIsNone(find_cjk_font_path())
            self.assertIsInstance(load_font(20), pygame.font.Font)


if __name__ == "__main__":
    unittest.main()

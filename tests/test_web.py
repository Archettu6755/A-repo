import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game.web import WEB_KEYS, WebInputBridge
from tools.build_web import (
    inject_web_controls,
    prepare_web_app,
    runtime_asset_paths,
    verify_web_build,
)


class FakeWindow:
    def __init__(self) -> None:
        self.commands = []
        self.suspended = False
        self.release_calls = 0

    def gameConsumeInput(self) -> str:
        commands = self.commands
        self.commands = []
        return json.dumps(commands)

    def gameIsSuspended(self) -> bool:
        return self.suspended

    def gameReleaseControls(self) -> None:
        self.release_calls += 1


class WebInputTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))
        pygame.event.clear()

    def tearDown(self) -> None:
        pygame.quit()

    def test_bridge_posts_supported_key_events(self) -> None:
        window = FakeWindow()
        window.commands = [
            {"type": "down", "key": "ArrowLeft"},
            {"type": "down", "key": "KeyF"},
            {"type": "up", "key": "KeyF"},
            {"type": "down", "key": "Unknown"},
            "invalid",
        ]
        bridge = WebInputBridge(window)

        self.assertFalse(bridge.pump())
        events = [
            event
            for event in pygame.event.get()
            if event.type in (pygame.KEYDOWN, pygame.KEYUP)
        ]
        self.assertEqual(
            [(event.type, event.key) for event in events],
            [
                (pygame.KEYDOWN, pygame.K_LEFT),
                (pygame.KEYDOWN, pygame.K_f),
                (pygame.KEYUP, pygame.K_f),
            ],
        )

    def test_bridge_reports_suspension_and_releases_on_pause_transition(self) -> None:
        window = FakeWindow()
        window.suspended = True
        bridge = WebInputBridge(window)

        self.assertTrue(bridge.pump())
        bridge.sync_state("playing")
        bridge.sync_state("paused")
        bridge.sync_state("paused")
        self.assertEqual(window.release_calls, 1)

    def test_bridge_ignores_invalid_json(self) -> None:
        window = FakeWindow()
        window.gameConsumeInput = lambda: "not-json"
        bridge = WebInputBridge(window)
        self.assertFalse(bridge.pump())
        self.assertFalse(pygame.event.get())

    def test_web_key_map_matches_desktop_controls(self) -> None:
        self.assertEqual(
            set(WEB_KEYS),
            {
                "ArrowLeft",
                "ArrowRight",
                "ArrowUp",
                "ArrowDown",
                "KeyF",
                "KeyE",
                "Escape",
                "Enter",
            },
        )


class WebBuildTests(unittest.TestCase):
    def test_runtime_assets_exclude_concepts_and_masters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = (
                "ui/panel.png",
                "ui/ui_master_v1.png",
                "characters/character_turnarounds_v1.png",
                "concepts/board.png",
                "fonts/game.ttf",
                "fonts/license.txt",
                "props/bullet_0.png",
                "props/bullet_sheet.png",
            )
            for name in files:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test")
            self.assertEqual(
                runtime_asset_paths(root),
                [
                    Path("fonts/game.ttf"),
                    Path("props/bullet_sheet.png"),
                    Path("ui/panel.png"),
                ],
            )

    def test_prepare_web_app_copies_runtime_code_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            copied = prepare_web_app(stage=stage)
            self.assertTrue((stage / "main.py").is_file())
            self.assertTrue((stage / "game" / "game.py").is_file())
            self.assertTrue(
                (stage / "game" / "assets" / "ui" / "title_background.png").is_file()
            )
            self.assertTrue((stage / "static" / "web_controls.js").is_file())
            self.assertNotIn(Path("concepts/art_direction_board_v1.png"), copied)
            self.assertFalse(
                any("master" in path.name.casefold() for path in copied)
            )

    def test_inject_controls_adds_css_markup_and_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "index.html"
            controls = root / "controls.html"
            index.write_text("<html><head></head><body><canvas></canvas></body></html>")
            controls.write_text('<div id="game-touch-controls"></div>')
            inject_web_controls(index, controls)
            html = index.read_text()
            self.assertIn('href="web_controls.css"', html)
            self.assertIn('id="game-touch-controls"', html)
            self.assertIn('src="web_controls.js"', html)

    def test_verify_web_build_rejects_master_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "favicon.png",
                "web_controls.css",
                "web_controls.js",
            ):
                (root / name).write_bytes(b"test")
            (root / "index.html").write_text(
                '<html><link href="web_controls.css"><div id="game-touch-controls">'
                '</div><script src="web_controls.js"></script></html>'
            )
            with zipfile.ZipFile(root / "app.apk", "w") as archive:
                for name in (
                    "assets/main.py",
                    "assets/game/game.py",
                    "assets/game/web.py",
                    "assets/game/assets/fonts/fusion_pixel_12px_zh_hans.ttf",
                    "assets/game/assets/ui/title_background.png",
                    "assets/game/assets/characters/boss/boss_phase1_idle_down_sheet.png",
                    "assets/game/assets/ui/ui_master_v1.png",
                ):
                    archive.writestr(name, b"test")
            with self.assertRaisesRegex(RuntimeError, "母版资源"):
                verify_web_build(root)


class WebGameLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        pygame.display.set_mode((1, 1))
        pygame.event.clear()

    def tearDown(self) -> None:
        pygame.quit()

    def test_run_frame_updates_and_draws_when_active(self) -> None:
        from game.game import Game

        game = object.__new__(Game)
        game.running = True
        with (
            patch.object(game, "handle_events") as handle_events,
            patch.object(game, "update") as update,
            patch.object(game, "draw") as draw,
        ):
            game.run_frame(0.25)
        handle_events.assert_called_once_with()
        update.assert_called_once_with(0.25)
        draw.assert_called_once_with()

    def test_run_frame_clears_input_and_skips_update_when_suspended(self) -> None:
        from game.game import Game

        game = object.__new__(Game)
        game.running = True
        game.controls = Mock()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        with (
            patch.object(game, "handle_events") as handle_events,
            patch.object(game, "update") as update,
            patch.object(game, "draw") as draw,
        ):
            game.run_frame(0.25, active=False)
        handle_events.assert_not_called()
        update.assert_not_called()
        game.controls.clear.assert_called_once_with()
        draw.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

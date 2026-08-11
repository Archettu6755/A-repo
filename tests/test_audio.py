import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from game.audio import AudioManager


class AudioManagerTests(unittest.TestCase):
    def test_missing_audio_directory_is_a_safe_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = AudioManager(Path(directory) / "missing")
            with patch(
                "game.audio.pygame.mixer.get_init", return_value=(44100, -16, 2)
            ):
                manager.initialize()
            manager.play("shoot")
            self.assertEqual(manager.sounds, {})

    def test_mixer_failure_disables_audio_without_crashing(self) -> None:
        manager = AudioManager()
        with (
            patch("game.audio.pygame.mixer.get_init", return_value=None),
            patch(
                "game.audio.pygame.mixer.init",
                side_effect=pygame.error("no audio device"),
            ),
        ):
            manager.initialize()
        self.assertFalse(manager.enabled)
        manager.play("shoot")


if __name__ == "__main__":
    unittest.main()

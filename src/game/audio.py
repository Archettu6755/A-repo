from pathlib import Path

import pygame

from .resources import ASSET_ROOT


class AudioManager:
    def __init__(self, root: Path = ASSET_ROOT / "audio") -> None:
        self.root = root
        self.enabled = True
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def initialize(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
        except pygame.error:
            self.enabled = False
            return
        if not self.root.is_dir():
            return
        for path in self.root.glob("*.ogg"):
            try:
                self.sounds[path.stem] = pygame.mixer.Sound(path)
            except pygame.error:
                continue

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled


AUDIO = AudioManager()

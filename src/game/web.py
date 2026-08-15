import json
import sys
from typing import Any

import pygame

WEB_KEYS = {
    "ArrowLeft": pygame.K_LEFT,
    "ArrowRight": pygame.K_RIGHT,
    "ArrowUp": pygame.K_UP,
    "ArrowDown": pygame.K_DOWN,
    "KeyF": pygame.K_f,
    "KeyE": pygame.K_e,
    "Escape": pygame.K_ESCAPE,
    "Enter": pygame.K_RETURN,
}


class WebInputBridge:
    def __init__(self, window: Any | None = None) -> None:
        if window is None and sys.platform == "emscripten":
            import platform

            window = platform.window
        self.window = window
        self.previous_state: str | None = None

    @property
    def available(self) -> bool:
        return self.window is not None

    def pump(self) -> bool:
        if self.window is None:
            return False
        try:
            payload = str(self.window.gameConsumeInput())
            commands = json.loads(payload or "[]")
        except (AttributeError, TypeError, ValueError):
            commands = []
        for command in commands:
            if not isinstance(command, dict):
                continue
            key = WEB_KEYS.get(command.get("key"))
            event_type = {
                "down": pygame.KEYDOWN,
                "up": pygame.KEYUP,
            }.get(command.get("type"))
            if key is None or event_type is None:
                continue
            pygame.event.post(pygame.event.Event(event_type, key=key))
        try:
            return bool(self.window.gameIsSuspended())
        except (AttributeError, TypeError):
            return False

    def sync_state(self, state: str) -> None:
        if (
            self.window is not None
            and state == "paused"
            and self.previous_state != "paused"
        ):
            try:
                self.window.gameReleaseControls()
            except (AttributeError, TypeError):
                pass
        self.previous_state = state

import pygame

MOVEMENT_KEYS = (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)
SCANCODE_KEYS = {
    pygame.KSCAN_LEFT: pygame.K_LEFT,
    pygame.KSCAN_RIGHT: pygame.K_RIGHT,
    pygame.KSCAN_UP: pygame.K_UP,
    pygame.KSCAN_DOWN: pygame.K_DOWN,
    pygame.KSCAN_E: pygame.K_e,
    pygame.KSCAN_F: pygame.K_f,
    pygame.KSCAN_ESCAPE: pygame.K_ESCAPE,
}
UNICODE_KEYS = {"e": pygame.K_e, "f": pygame.K_f}


def event_key(event: pygame.event.Event) -> int:
    text = getattr(event, "unicode", "").casefold()
    if text in UNICODE_KEYS:
        return UNICODE_KEYS[text]
    return SCANCODE_KEYS.get(getattr(event, "scancode", None), event.key)


class Controls:
    def __init__(self) -> None:
        self.movement_held: set[int] = set()
        self.movement_pressed: set[int] = set()
        self.last_horizontal: int | None = None
        self.last_vertical: int | None = None
        self.fire_held = False
        self.fire_scancode: int | None = None
        self.fire_buffer = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            key = event_key(event)
            if key == pygame.K_f:
                scancode = getattr(event, "scancode", None)
                self.fire_held = True
                self.fire_scancode = scancode
                self.fire_buffer = 0.15
            elif key in MOVEMENT_KEYS:
                self.movement_held.add(key)
                self.movement_pressed.add(key)
                if key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.last_horizontal = key
                else:
                    self.last_vertical = key
        elif event.type == pygame.KEYUP:
            key = event_key(event)
            scancode = getattr(event, "scancode", None)
            same_fire_scancode = (
                self.fire_held
                and self.fire_scancode is not None
                and scancode == self.fire_scancode
            )
            if key == pygame.K_f or same_fire_scancode:
                self.fire_held = False
                self.fire_scancode = None
            elif key in MOVEMENT_KEYS:
                self.movement_held.discard(key)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.clear()

    def movement_axis(self) -> tuple[int, int]:
        active = self.movement_held | self.movement_pressed
        dx = self._axis(
            pygame.K_LEFT,
            pygame.K_RIGHT,
            self.last_horizontal,
            active,
        )
        dy = self._axis(
            pygame.K_UP,
            pygame.K_DOWN,
            self.last_vertical,
            active,
        )
        self.movement_pressed.difference_update(MOVEMENT_KEYS)
        return dx, dy

    @staticmethod
    def _axis(
        negative: int, positive: int, latest: int | None, active: set[int]
    ) -> int:
        negative_down = negative in active
        positive_down = positive in active
        if negative_down and positive_down:
            if latest == positive:
                return 1
            if latest == negative:
                return -1
            return 0
        return int(positive_down) - int(negative_down)

    def wants_fire(self) -> bool:
        return self.fire_held or self.fire_buffer > 0

    def consume_fire(self) -> None:
        self.fire_buffer = 0.0

    def update(self, dt: float) -> None:
        self.fire_buffer = max(0.0, self.fire_buffer - dt)

    def clear(self) -> None:
        self.movement_held.clear()
        self.movement_pressed.clear()
        self.last_horizontal = None
        self.last_vertical = None
        self.fire_held = False
        self.fire_scancode = None
        self.fire_buffer = 0.0

import pygame

MOVEMENT_KEYS = (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)


class Controls:
    def __init__(self) -> None:
        self.held: set[int] = set()
        self.pressed: set[int] = set()
        self.fire_buffer = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self.held.add(event.key)
            self.pressed.add(event.key)
            if event.key == pygame.K_f:
                self.fire_buffer = 0.15
        elif event.type == pygame.KEYUP:
            self.held.discard(event.key)
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.clear()

    def movement_axis(self) -> tuple[int, int]:
        dx = int(pygame.K_RIGHT in self.held or pygame.K_RIGHT in self.pressed) - int(
            pygame.K_LEFT in self.held or pygame.K_LEFT in self.pressed
        )
        dy = int(pygame.K_DOWN in self.held or pygame.K_DOWN in self.pressed) - int(
            pygame.K_UP in self.held or pygame.K_UP in self.pressed
        )
        self.pressed.difference_update(MOVEMENT_KEYS)
        return dx, dy

    def wants_fire(self) -> bool:
        return pygame.K_f in self.held or self.fire_buffer > 0

    def consume_fire(self) -> None:
        self.pressed.discard(pygame.K_f)
        self.fire_buffer = 0.0

    def update(self, dt: float) -> None:
        self.fire_buffer = max(0.0, self.fire_buffer - dt)

    def clear(self) -> None:
        self.held.clear()
        self.pressed.clear()
        self.fire_buffer = 0.0

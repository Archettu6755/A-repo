import random

import pygame

from .config import (
    BULLET_COLOR,
    BULLET_RANGE,
    BULLET_SIZE,
    BULLET_SPEED,
    COIN_COLOR,
    COIN_DROP_CHANCE,
    COIN_LIFETIME,
    COIN_SIZE,
    INVINCIBLE_TIME,
    PLAYER_COLOR,
    PLAYER_SIZE,
    ZOMBIE_CHARGE_DIST,
    ZOMBIE_CHARGE_SPEED_MULT,
    ZOMBIE_COLORS,
    ZOMBIE_MAX_CHARGE_DIST,
    ZOMBIE_STUN_TIME,
    ZOMBIE_TYPES,
)


class Player:
    def __init__(
        self,
        pos: pygame.Vector2,
        max_hp: int,
        attack: int,
        cooldown: float,
        speed: float,
    ) -> None:
        self.pos = pos
        self.size = PLAYER_SIZE
        self.max_hp = max_hp
        self.hp = max_hp
        self.attack = attack
        self.cooldown = cooldown
        self.speed = speed
        self.facing = pygame.Vector2(1, 0)
        self.fire_timer = 0.0
        self.invincible_timer = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def move(self, dx: float, dy: float, room) -> None:
        if dx != 0 or dy != 0:
            self.facing = pygame.Vector2(dx, dy)
            if self.facing.length_squared() > 0:
                self.facing.normalize_ip()
        self.pos.x += dx
        self.pos.y += dy
        rect = self.rect
        room.clamp_rect(rect)
        self.pos.update(rect.x, rect.y)

    def try_fire(self) -> bool:
        if self.fire_timer > 0:
            return False
        self.fire_timer = self.cooldown
        return True

    def take_hit(self, damage: int) -> bool:
        if self.invincible_timer > 0:
            return False
        self.hp -= damage
        self.invincible_timer = INVINCIBLE_TIME
        return True

    def update(self, dt: float) -> None:
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def draw(self, surface: pygame.Surface) -> None:
        if self.invincible_timer > 0 and int(self.invincible_timer * 20) % 2 == 0:
            return
        pygame.draw.rect(surface, PLAYER_COLOR, self.rect)


class Zombie:
    def __init__(self, kind: str, pos: pygame.Vector2) -> None:
        data = ZOMBIE_TYPES[kind]
        self.kind = kind
        self.pos = pos
        self.size = data["size"]
        self.hp = data["hp"]
        self.damage = data["damage"]
        self.base_speed = data["speed"]
        self.speed = data["speed"]
        self.state = "wander"
        self.state_timer = 0.0
        self.charge_dir = pygame.Vector2(0, 0)
        self.charge_origin = pygame.Vector2(pos)
        self.color = ZOMBIE_COLORS[data["color"]]

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def update(self, dt: float, player_pos: pygame.Vector2, room) -> None:
        if self.state == "stun":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "wander"
            return

        if self.state == "charge":
            self.pos += self.charge_dir * self.speed * dt * 60
            if self.pos.distance_to(self.charge_origin) >= ZOMBIE_MAX_CHARGE_DIST:
                self._stun()
                return
            rect = self.rect
            room.clamp_rect(rect)
            if rect.x != self.pos.x or rect.y != self.pos.y:
                self._stun()
                self.pos.update(rect.x, rect.y)
            return

        dist = self.pos.distance_to(player_pos)
        if dist <= ZOMBIE_CHARGE_DIST:
            self.state = "charge"
            self.charge_dir = (player_pos - self.pos).normalize()
            self.charge_origin = pygame.Vector2(self.pos)
            self.speed = self.base_speed * ZOMBIE_CHARGE_SPEED_MULT
            return

        move = player_pos - self.pos
        if move.length_squared() > 0:
            move = move.normalize()
        self.pos += move * self.base_speed * dt * 60

        rect = self.rect
        room.clamp_rect(rect)
        self.pos.update(rect.x, rect.y)

    def _stun(self) -> None:
        self.state = "stun"
        self.state_timer = ZOMBIE_STUN_TIME
        self.speed = self.base_speed

    def stun(self) -> None:
        if self.state == "charge":
            self._stun()

    def take_damage(self, amount: int) -> bool:
        self.hp -= amount
        return self.hp <= 0

    def hits_player(self, player_rect: pygame.Rect) -> bool:
        return self.rect.colliderect(player_rect)

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, self.color, self.rect)
        if self.state == "stun":
            pygame.draw.circle(surface, (255, 255, 255), self.rect.center, 4)


class Bullet:
    def __init__(self, pos: pygame.Vector2, direction: pygame.Vector2) -> None:
        self.pos = pygame.Vector2(pos)
        self.direction = direction.normalize()
        self.origin = pygame.Vector2(pos)
        self.size = BULLET_SIZE

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def update(self, dt: float) -> bool:
        self.pos += self.direction * BULLET_SPEED * dt * 60
        return self.pos.distance_to(self.origin) <= BULLET_RANGE

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, BULLET_COLOR, self.rect)


class Coin:
    def __init__(self, pos: pygame.Vector2) -> None:
        self.pos = pygame.Vector2(pos)
        self.size = COIN_SIZE
        self.timer = COIN_LIFETIME

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def update(self, dt: float) -> bool:
        self.timer -= dt
        return self.timer > 0

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COIN_COLOR, self.rect)


def spawn_zombie(kind_weights: dict[str, int], pos: pygame.Vector2) -> Zombie:
    kind = random.choices(
        list(kind_weights.keys()), weights=list(kind_weights.values())
    )[0]
    return Zombie(kind, pos)


def drop_coin(pos: pygame.Vector2) -> Coin | None:
    if random.random() <= COIN_DROP_CHANCE:
        return Coin(pos)
    return None

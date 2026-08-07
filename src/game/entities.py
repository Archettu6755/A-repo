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
    PLAYER_SEPARATION_RADIUS,
    PLAYER_SIZE,
    ZOMBIE_CHARGE_DIST,
    ZOMBIE_COLORS,
    ZOMBIE_TYPES,
)
from .resources import SPRITES


def _direction_name(vector: pygame.Vector2) -> str:
    if abs(vector.x) >= abs(vector.y):
        return "right" if vector.x >= 0 else "left"
    return "down" if vector.y >= 0 else "up"


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
        self.separation_radius = PLAYER_SEPARATION_RADIUS
        self.max_hp = max_hp
        self.hp = max_hp
        self.attack = attack
        self.cooldown = cooldown
        self.speed = speed
        self.facing = pygame.Vector2(1, 0)
        self.moving = False
        self.animation_clock = 0.0
        self.shoot_pose_timer = 0.0
        self.fire_timer = 0.0
        self.invincible_timer = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def move(self, dx: float, dy: float, blockers: list[pygame.Rect]) -> None:
        self.moving = dx != 0 or dy != 0
        if dx != 0 or dy != 0:
            self.facing = pygame.Vector2(dx, dy)
            if self.facing.length_squared() > 0:
                self.facing.normalize_ip()
        if dx != 0:
            self.pos.x += dx
            if self.rect.collidelist(blockers) != -1:
                self.pos.x -= dx
        if dy != 0:
            self.pos.y += dy
            if self.rect.collidelist(blockers) != -1:
                self.pos.y -= dy

    def push(self, delta: pygame.Vector2, blockers: list[pygame.Rect]) -> None:
        facing = self.facing.copy()
        self.move(delta.x, delta.y, blockers)
        self.facing = facing

    def try_fire(self) -> bool:
        if self.fire_timer > 0:
            return False
        self.fire_timer = self.cooldown
        self.shoot_pose_timer = 0.1
        return True

    def take_hit(self, damage: int) -> bool:
        if self.invincible_timer > 0:
            return False
        self.hp -= damage
        self.invincible_timer = INVINCIBLE_TIME
        return True

    def update(self, dt: float) -> None:
        self.animation_clock += dt
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.shoot_pose_timer = max(0.0, self.shoot_pose_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        if self.invincible_timer > 0 and int(self.invincible_timer * 20) % 2 == 0:
            return
        rect = self.rect.move(-cam_x, -cam_y)
        direction = _direction_name(self.facing)
        if self.shoot_pose_timer > 0:
            action = "shoot"
        elif self.invincible_timer > 0:
            action = "hurt"
        elif self.moving:
            action = "walk"
        else:
            action = "idle"
        sprite = SPRITES.load(
            f"characters/player/player_{action}_{direction}.png",
            (32, 48),
        )
        if sprite is None:
            pygame.draw.rect(surface, PLAYER_COLOR, rect)
        else:
            shadow = SPRITES.load("props/shadow_small.png", (24, 10))
            if shadow is not None:
                surface.blit(
                    shadow, shadow.get_rect(midbottom=(rect.centerx, rect.bottom + 2))
                )
            bob = -1 if self.moving and int(self.animation_clock * 10) % 2 else 0
            recoil = -self.facing * 2 if self.shoot_pose_timer > 0 else pygame.Vector2()
            surface.blit(
                sprite,
                sprite.get_rect(
                    midbottom=(
                        rect.centerx + round(recoil.x),
                        rect.bottom + bob + round(recoil.y),
                    )
                ),
            )
        if self.shoot_pose_timer > 0:
            muzzle = pygame.Vector2(rect.center) + self.facing * (self.size / 2 + 5)
            pygame.draw.circle(surface, (255, 166, 70), muzzle, 5)
            pygame.draw.circle(surface, (255, 240, 178), muzzle, 2)


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
        self.separation_radius = data["separation_radius"]
        self.warning_time = data["warning"]
        self.charge_mult = data["charge_mult"]
        self.max_charge_dist = data["max_charge_dist"]
        self.stun_time = data["stun"]
        self.state = "wander"
        self.state_timer = 0.0
        self.charge_dir = pygame.Vector2(0, 0)
        self.facing = pygame.Vector2(1, 0)
        self.animation_clock = 0.0
        self.charge_origin = pygame.Vector2(pos)
        self.color = ZOMBIE_COLORS[data["color"]]

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def update(
        self,
        dt: float,
        player_pos: pygame.Vector2,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        self.animation_clock += dt
        if self.state == "stun":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "wander"
            return

        if self.state == "warning":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "charge"
                self.speed = self.base_speed * self.charge_mult
                self.charge_origin = pygame.Vector2(self.pos)
            return

        if self.state == "charge":
            old = pygame.Vector2(self.pos)
            self.pos += self.charge_dir * self.speed * dt * 60
            rect = self.rect
            room.clamp_rect(rect)
            if rect.x != self.pos.x or rect.y != self.pos.y:
                self._stun()
                self.pos.update(rect.x, rect.y)
                return
            if rect.collidelist(blockers) != -1:
                self._stun()
                self.pos.update(old)
                return
            if self.pos.distance_to(self.charge_origin) >= self.max_charge_dist:
                self._stun()
            return

        center = pygame.Vector2(self.rect.center)
        dist = center.distance_to(player_pos)
        if dist <= ZOMBIE_CHARGE_DIST:
            direction = player_pos - center
            if direction.length_squared() == 0:
                direction = pygame.Vector2(1, 0)
            self.state = "warning"
            self.state_timer = self.warning_time
            self.charge_dir = direction.normalize()
            self.facing = self.charge_dir.copy()
            return

        move = player_pos - self.pos
        if move.length_squared() > 0:
            move = move.normalize()
            self.facing = move.copy()
        new_pos = self.pos + move * self.base_speed * dt * 60
        rect = pygame.Rect(0, 0, self.size, self.size).move(new_pos)
        if rect.collidelist(blockers) == -1:
            self.pos = new_pos
            rect = self.rect
            room.clamp_rect(rect)
            self.pos.update(rect.x, rect.y)

    def _stun(self) -> None:
        self.state = "stun"
        self.state_timer = self.stun_time
        self.speed = self.base_speed

    def stun(self) -> None:
        if self.state == "charge":
            self._stun()

    def take_damage(self, amount: int) -> bool:
        self.hp -= amount
        return self.hp <= 0

    def hits_player(self, player: Player) -> bool:
        return pygame.Vector2(self.rect.center).distance_to(player.rect.center) < (
            self.separation_radius + player.separation_radius
        )

    def push(
        self,
        delta: pygame.Vector2,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        old = pygame.Vector2(self.pos)
        self.pos.x += delta.x
        rect = self.rect
        room.clamp_rect(rect)
        self.pos.update(rect.x, rect.y)
        if self.rect.collidelist(blockers) != -1:
            self.pos.x = old.x

        old_y = self.pos.y
        self.pos.y += delta.y
        rect = self.rect
        room.clamp_rect(rect)
        self.pos.update(rect.x, rect.y)
        if self.rect.collidelist(blockers) != -1:
            self.pos.y = old_y

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        rect = self.rect.move(-cam_x, -cam_y)
        action = {
            "wander": "idle",
            "warning": "charge_prepare" if self.kind == "heavy" else "charge",
            "charge": "leap" if self.kind == "fast" else "charge",
            "stun": "stun",
        }[self.state]
        direction = _direction_name(self.facing)
        canvas = {"normal": (32, 48), "fast": (32, 40), "heavy": (48, 56)}[self.kind]
        sprite = SPRITES.load(
            f"characters/zombie_{self.kind}/zombie_{self.kind}_{action}_{direction}.png",
            canvas,
        )
        if sprite is None:
            pygame.draw.rect(surface, self.color, rect)
        else:
            shadow_size = (36, 14) if self.kind == "heavy" else (24, 10)
            shadow = SPRITES.load("props/shadow_small.png", shadow_size)
            if shadow is not None:
                surface.blit(
                    shadow, shadow.get_rect(midbottom=(rect.centerx, rect.bottom + 2))
                )
            bob = (
                -1
                if self.state == "wander" and int(self.animation_clock * 8) % 2
                else 0
            )
            surface.blit(
                sprite,
                sprite.get_rect(midbottom=(rect.centerx, rect.bottom + bob)),
            )
        if self.state == "warning":
            pygame.draw.circle(surface, (220, 70, 65), rect.center, rect.width // 2, 2)
        elif self.state == "stun":
            pygame.draw.circle(surface, (255, 255, 255), rect.center, 4)


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

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        rect = self.rect.move(-cam_x, -cam_y)
        center = pygame.Vector2(rect.center)
        tail = center - self.direction * 8
        pygame.draw.line(surface, (255, 142, 52), tail, center, 3)
        sprite = SPRITES.load("props/bullet.png", (self.size, self.size))
        if sprite is None:
            pygame.draw.rect(surface, BULLET_COLOR, rect)
        else:
            surface.blit(sprite, rect)
        pygame.draw.circle(surface, (255, 244, 190), center, 2)


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

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        rect = self.rect.move(-cam_x, -cam_y)
        sprite = SPRITES.load("props/coin.png", (16, 16))
        if sprite is None:
            pygame.draw.rect(surface, COIN_COLOR, rect)
        else:
            surface.blit(sprite, sprite.get_rect(center=rect.center))


def spawn_zombie(kind_weights: dict[str, int], pos: pygame.Vector2) -> Zombie:
    kind = random.choices(
        list(kind_weights.keys()), weights=list(kind_weights.values())
    )[0]
    return Zombie(kind, pos)


def drop_coin(pos: pygame.Vector2) -> Coin | None:
    if random.random() <= COIN_DROP_CHANCE:
        return Coin(pos)
    return None

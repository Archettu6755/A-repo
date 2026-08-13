import random

import pygame

from .config import (
    BOSS_CANVAS_SIZE,
    BOSS_CHARGE_SUBSTEP,
    BOSS_DEATH_TIME,
    BOSS_PHASE_STATS,
    BOSS_SEPARATION_RADIUS,
    BOSS_SIZE,
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
    ZOMBIE_COLORS,
    ZOMBIE_RECOVERY_TIME,
    ZOMBIE_TYPES,
    ZOMBIE_WANDER_INTERVAL,
)
from .resources import SPRITES


def _direction_name(vector: pygame.Vector2) -> str:
    if abs(vector.x) >= abs(vector.y):
        return "right" if vector.x >= 0 else "left"
    return "down" if vector.y >= 0 else "up"


def _animation_sprite(
    path: str,
    size: tuple[int, int],
    clock: float,
    frames: int,
    fps: float,
    *,
    loop: bool = True,
) -> pygame.Surface | None:
    frame = int(clock * fps)
    frame = frame % frames if loop else min(frame, frames - 1)
    return SPRITES.frame(path, size, frame)


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
        self.dead = False
        self.death_clock = 0.0

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
        self.shoot_pose_timer = 0.15
        return True

    def take_hit(self, damage: int) -> bool:
        if self.invincible_timer > 0:
            return False
        self.hp -= damage
        self.invincible_timer = INVINCIBLE_TIME
        if self.hp <= 0:
            self.dead = True
            self.death_clock = 0.0
            self.moving = False
            self.shoot_pose_timer = 0.0
        return True

    def update(self, dt: float) -> None:
        self.animation_clock += dt
        if self.dead:
            self.death_clock += dt
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.shoot_pose_timer = max(0.0, self.shoot_pose_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        if (
            not self.dead
            and self.invincible_timer > 0
            and int(self.invincible_timer * 20) % 2 == 0
        ):
            return
        rect = self.rect.move(-cam_x, -cam_y)
        direction = _direction_name(self.facing)
        if self.dead:
            action = "death"
        elif self.shoot_pose_timer > 0:
            action = "shoot"
        elif self.invincible_timer > 0:
            action = "hurt"
        elif self.moving:
            action = "walk"
        else:
            action = "idle"
        if action == "death":
            sprite = _animation_sprite(
                "characters/player/player_death_sheet.png",
                (32, 48),
                self.death_clock,
                6,
                12.0,
                loop=False,
            )
            if sprite is None:
                sprite = SPRITES.load("characters/player/player_death_3.png", (32, 48))
        else:
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
            recoil = -self.facing * 2 if self.shoot_pose_timer > 0 else pygame.Vector2()
            surface.blit(
                sprite,
                sprite.get_rect(
                    midbottom=(
                        rect.centerx + round(recoil.x),
                        rect.bottom + round(recoil.y),
                    )
                ),
            )


class Zombie:
    def __init__(
        self,
        kind: str,
        pos: pygame.Vector2,
        level: int = 1,
        rng: random.Random | None = None,
    ) -> None:
        data = ZOMBIE_TYPES[kind]
        self.rng = rng or random.Random()
        self.kind = kind
        self.pos = pos
        self.size = data["size"]
        self.hp = data["hp"] + level - 1
        self.max_hp = self.hp
        self.damage = data["damage"] + (1 if level == 3 else 0)
        self.base_speed = data["speed"]
        self.speed = data["speed"]
        self.separation_radius = data["separation_radius"]
        self.warning_time = data["warning"]
        self.sensing_distance = data["sensing_distance"]
        self.charge_mult = data["charge_mult"]
        self.max_charge_dist = data["max_charge_dist"]
        self.stun_time = data["stun"]
        self.state = "wander"
        self.state_timer = self.rng.uniform(*ZOMBIE_WANDER_INTERVAL)
        self.state_clock = 0.0
        self.charge_dir = pygame.Vector2(0, 0)
        self.facing = pygame.Vector2(1, 0)
        self.animation_clock = 0.0
        self.charge_origin = pygame.Vector2(pos)
        self.wander_target: pygame.Vector2 | None = None
        self.moving = False
        self.hurt_timer = 0.0
        self.wall_impact_pending = False
        self.movement_trace: list[pygame.Vector2] = []
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
        self.state_clock += dt
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.moving = False
        self.movement_trace = [pygame.Vector2(self.rect.center)]
        if self.state == "stun":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self._set_state("recover", self.rng.uniform(*ZOMBIE_RECOVERY_TIME))
            return

        if self.state == "recover":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self._set_state("wander", 0.0)
                self.wander_target = None
            return

        if self.state == "warning":
            self.state_timer -= dt
            if self.state_timer <= 0:
                center = pygame.Vector2(self.rect.center)
                direction = player_pos - center
                if direction.length_squared() == 0:
                    direction = self.facing.copy()
                self.charge_dir = direction.normalize()
                self.facing = self.charge_dir.copy()
                self._set_state("charge")
                self.speed = self.base_speed * self.charge_mult
                self.charge_origin = pygame.Vector2(self.pos)
            return

        if self.state == "charge":
            self._advance_charge(dt, room, blockers)
            return

        center = pygame.Vector2(self.rect.center)
        if center.distance_to(player_pos) <= self.sensing_distance and self._line_clear(
            center, player_pos, blockers
        ):
            direction = player_pos - center
            if direction.length_squared() == 0:
                direction = pygame.Vector2(1, 0)
            self._set_state("warning", self.warning_time)
            self.facing = direction.normalize()
            return

        self.state_timer -= dt
        if self.wander_target is None or self.state_timer <= 0:
            self._choose_wander_target(room, blockers)
        if self.wander_target is None:
            return
        move = self.wander_target - center
        if move.length_squared() <= 16:
            self._choose_wander_target(room, blockers)
            return
        move = move.normalize()
        self.facing = move.copy()
        distance = self.base_speed * dt * 60
        moved_x = self._move_axis(move.x * distance, 0, room, blockers)
        moved_y = self._move_axis(0, move.y * distance, room, blockers)
        self.moving = moved_x or moved_y
        if not self.moving:
            self._choose_wander_target(room, blockers)

    @staticmethod
    def _line_clear(
        start: pygame.Vector2,
        end: pygame.Vector2,
        blockers: list[pygame.Rect],
    ) -> bool:
        line = (round(start.x), round(start.y), round(end.x), round(end.y))
        return not any(blocker.clipline(line) for blocker in blockers)

    def _choose_wander_target(self, room, blockers: list[pygame.Rect]) -> None:
        margin = max(self.size, 32)
        for _ in range(20):
            target = pygame.Vector2(
                self.rng.uniform(room.rect.left + margin, room.rect.right - margin),
                self.rng.uniform(room.rect.top + margin, room.rect.bottom - margin),
            )
            target_rect = pygame.Rect(0, 0, self.size, self.size)
            target_rect.center = (round(target.x), round(target.y))
            if target_rect.collidelist(blockers) == -1 and self._line_clear(
                pygame.Vector2(self.rect.center), target, blockers
            ):
                self.wander_target = target
                self.state_timer = self.rng.uniform(*ZOMBIE_WANDER_INTERVAL)
                return
        self.wander_target = None
        self.state_timer = 0.2

    def _move_axis(
        self,
        dx: float,
        dy: float,
        room,
        blockers: list[pygame.Rect],
    ) -> bool:
        old = pygame.Vector2(self.pos)
        self.pos.x = min(
            max(self.pos.x + dx, float(room.rect.left)),
            float(room.rect.right - self.size),
        )
        self.pos.y = min(
            max(self.pos.y + dy, float(room.rect.top)),
            float(room.rect.bottom - self.size),
        )
        if self.rect.collidelist(blockers) != -1:
            self.pos.update(old)
            return False
        return self.pos != old

    def _advance_charge(
        self,
        dt: float,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        travelled = self.pos.distance_to(self.charge_origin)
        remaining = min(self.speed * dt * 60, self.max_charge_dist - travelled)
        while remaining > 0:
            distance = min(8.0, remaining)
            old = pygame.Vector2(self.pos)
            target = self.pos + self.charge_dir * distance
            next_x = min(
                max(target.x, float(room.rect.left)),
                float(room.rect.right - self.size),
            )
            next_y = min(
                max(target.y, float(room.rect.top)),
                float(room.rect.bottom - self.size),
            )
            boundary_hit = next_x != target.x or next_y != target.y
            self.pos.update(next_x, next_y)
            if boundary_hit:
                self.movement_trace.append(pygame.Vector2(self.rect.center))
                self._stun(wall_impact=True)
                return
            if self.rect.collidelist(blockers) != -1:
                self.pos.update(old)
                self._stun(wall_impact=True)
                return
            self.movement_trace.append(pygame.Vector2(self.rect.center))
            remaining -= distance
        if self.pos.distance_to(self.charge_origin) >= self.max_charge_dist - 0.01:
            self._stun()

    def _set_state(self, state: str, timer: float = 0.0) -> None:
        self.state = state
        self.state_timer = timer
        self.state_clock = 0.0

    def _stun(self, *, wall_impact: bool = False) -> None:
        self._set_state("stun", self.stun_time)
        self.speed = self.base_speed
        self.wall_impact_pending = wall_impact

    def stun(self) -> None:
        if self.state == "charge":
            self._stun()

    def consume_wall_impact(self) -> bool:
        pending = self.wall_impact_pending
        self.wall_impact_pending = False
        return pending

    def take_damage(self, amount: int) -> bool:
        self.hp -= amount
        self.hurt_timer = 0.12
        self.state_clock = 0.0
        return self.hp <= 0

    def hits_player(self, player: Player) -> bool:
        player_center = pygame.Vector2(player.rect.center)
        minimum = self.separation_radius + player.separation_radius
        return any(
            point.distance_to(player_center) < minimum
            for point in (*self.movement_trace, pygame.Vector2(self.rect.center))
        )

    def push(
        self,
        delta: pygame.Vector2,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        old = pygame.Vector2(self.pos)
        self.pos.x = min(
            max(self.pos.x + delta.x, float(room.rect.left)),
            float(room.rect.right - self.size),
        )
        if self.rect.collidelist(blockers) != -1:
            self.pos.x = old.x

        old_y = self.pos.y
        self.pos.y = min(
            max(self.pos.y + delta.y, float(room.rect.top)),
            float(room.rect.bottom - self.size),
        )
        if self.rect.collidelist(blockers) != -1:
            self.pos.y = old_y

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        rect = self.rect.move(-cam_x, -cam_y)
        move_action = {"normal": "walk", "fast": "run", "heavy": "walk"}[self.kind]
        action = {
            "wander": move_action if self.moving else "idle",
            "recover": "idle",
            "warning": "charge_prepare" if self.kind == "heavy" else "charge",
            "charge": "leap" if self.kind == "fast" else "charge",
            "stun": "stun",
        }[self.state]
        if self.hurt_timer > 0:
            action = "hurt"
        direction = _direction_name(self.facing)
        canvas = {"normal": (32, 48), "fast": (32, 40), "heavy": (48, 56)}[self.kind]
        frame_counts = {
            "idle": 2,
            "walk": 4,
            "run": 4,
            "charge_prepare": 2,
            "charge": 3,
            "leap": 3,
            "hurt": 2,
            "stun": 2,
        }
        frame_rates = {
            "idle": 3.0,
            "walk": 7.0,
            "run": 10.0,
            "charge_prepare": 5.0,
            "charge": 12.0,
            "leap": 12.0,
            "hurt": 12.0,
            "stun": 6.0,
        }
        loop = True
        if self.state == "warning":
            if self.kind == "fast":
                frame_counts["charge"] = 4
            frame_rates[action] = frame_counts[action] / self.warning_time
            loop = False
        sprite = _animation_sprite(
            f"characters/zombie_{self.kind}/"
            f"zombie_{self.kind}_{action}_{direction}_sheet.png",
            canvas,
            self.state_clock,
            frame_counts[action],
            frame_rates[action],
            loop=loop,
        )
        if sprite is None:
            sprite = SPRITES.load(
                f"characters/zombie_{self.kind}/"
                f"zombie_{self.kind}_{action}_{direction}.png",
                canvas,
            )
        if sprite is not None and self.hurt_timer > 0:
            sprite = sprite.copy()
            sprite.fill((180, 180, 180, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if sprite is None:
            pygame.draw.rect(surface, self.color, rect)
        else:
            if self.kind == "heavy":
                shadow_path = "props/shadow_large.png"
                shadow_size = (36, 14)
            else:
                shadow_path = "props/shadow_small.png"
                shadow_size = (24, 10)
            shadow = SPRITES.load(shadow_path, shadow_size)
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
            progress = 1.0 - max(0.0, self.state_timer) / self.warning_time
            frame = min(3, int(progress * 4))
            warning = SPRITES.load(f"effects/fx_charge_warning_{frame}.png", (32, 32))
            if warning is None:
                pygame.draw.circle(
                    surface, (220, 70, 65), rect.center, rect.width // 2, 2
                )
            else:
                surface.blit(
                    warning,
                    warning.get_rect(center=(rect.centerx, rect.bottom - 4)),
                )
        elif self.state == "stun":
            pygame.draw.circle(surface, (255, 255, 255), rect.center, 4)


class Boss:
    def __init__(self, pos: pygame.Vector2) -> None:
        self.pos = pygame.Vector2(pos)
        self.size = BOSS_SIZE
        self.separation_radius = BOSS_SEPARATION_RADIUS
        self.phase = 1
        self.facing = pygame.Vector2(-1, 0)
        self.charge_dir = pygame.Vector2(-1, 0)
        self.charge_origin = pygame.Vector2(pos)
        self.animation_clock = 0.0
        self.state_clock = 0.0
        self.hurt_timer = 0.0
        self.death_clock = 0.0
        self.dead = False
        self.wall_impact_pending = False
        self.movement_trace: list[pygame.Vector2] = []
        self.charge_trace_active = False
        self.contact_available = False
        self.contact_damage = 0
        self._load_phase(1)
        self.charges_remaining = 0
        self.state = "recover"
        self.state_timer = self.recovery_time

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    @property
    def center(self) -> pygame.Vector2:
        return self.pos + pygame.Vector2(self.size / 2)

    @property
    def death_finished(self) -> bool:
        return self.dead and self.death_clock >= BOSS_DEATH_TIME

    def _load_phase(self, phase: int) -> None:
        data = BOSS_PHASE_STATS[phase]
        self.phase = phase
        self.max_hp = int(data["hp"])
        self.hp = self.max_hp
        self.base_speed = float(data["base_speed"])
        self.warning_time = float(data["warning"])
        self.charge_speed = float(data["charge_speed"])
        self.max_charge_dist = float(data["max_charge_dist"])
        self.charge_count = int(data["charges"])
        self.stun_time = float(data["stun"])
        self.recovery_time = float(data["recovery"])
        self.damage = int(data["damage"])

    def update(
        self,
        dt: float,
        player_pos: pygame.Vector2,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        self.animation_clock += dt
        self.state_clock += dt
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.movement_trace = [self.center]
        self.charge_trace_active = False
        if self.dead:
            self.death_clock += dt
            return

        if self.state == "stun":
            self.state_timer -= dt
            if self.state_timer <= 1e-9:
                self._set_state("recover", self.recovery_time)
            return

        if self.state == "recover":
            active_dt = min(dt, max(0.0, self.state_timer))
            self._approach_player(active_dt, player_pos, room, blockers)
            self.state_timer -= dt
            if self.state_timer <= 1e-9:
                self._start_attack()
            return

        if self.state == "warning":
            direction = player_pos - self.center
            if direction.length_squared() > 0:
                self.facing = direction.normalize()
            self.state_timer -= dt
            if self.state_timer <= 1e-9:
                self._begin_charge(player_pos)
            return

        self._advance_charge(dt, room, blockers)

    def _approach_player(
        self,
        dt: float,
        player_pos: pygame.Vector2,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        remaining = self.base_speed * dt * 60
        while remaining > 1e-9:
            direction = player_pos - self.center
            distance_to_player = direction.length()
            if distance_to_player <= 1e-9:
                return
            direction /= distance_to_player
            self.facing = direction.copy()
            distance = min(BOSS_CHARGE_SUBSTEP, remaining, distance_to_player)
            moved_x = self._move_axis(direction.x * distance, 0, room, blockers)
            moved_y = self._move_axis(0, direction.y * distance, room, blockers)
            if not moved_x and not moved_y:
                return
            remaining -= distance

    def _move_axis(
        self,
        dx: float,
        dy: float,
        room,
        blockers: list[pygame.Rect],
    ) -> bool:
        old = pygame.Vector2(self.pos)
        self.pos.x = min(
            max(self.pos.x + dx, float(room.rect.left)),
            float(room.rect.right - self.size),
        )
        self.pos.y = min(
            max(self.pos.y + dy, float(room.rect.top)),
            float(room.rect.bottom - self.size),
        )
        if self.rect.collidelist(blockers) != -1:
            self.pos.update(old)
            return False
        return self.pos != old

    def _start_attack(self) -> None:
        self.charges_remaining = self.charge_count
        self._set_state("warning", self.warning_time)

    def _begin_charge(self, player_pos: pygame.Vector2) -> None:
        direction = player_pos - self.center
        if direction.length_squared() == 0:
            direction = self.facing.copy()
        self.charge_dir = direction.normalize()
        self.facing = self.charge_dir.copy()
        self.charge_origin = pygame.Vector2(self.pos)
        self.charges_remaining -= 1
        self.contact_available = True
        self.contact_damage = self.damage
        self._set_state("charge")

    def _advance_charge(
        self,
        dt: float,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        self.charge_trace_active = True
        travelled = self.pos.distance_to(self.charge_origin)
        remaining = min(
            self.charge_speed * dt * 60,
            max(0.0, self.max_charge_dist - travelled),
        )
        while remaining > 0:
            distance = min(BOSS_CHARGE_SUBSTEP, remaining)
            old = pygame.Vector2(self.pos)
            target = self.pos + self.charge_dir * distance
            next_x = min(
                max(target.x, float(room.rect.left)),
                float(room.rect.right - self.size),
            )
            next_y = min(
                max(target.y, float(room.rect.top)),
                float(room.rect.bottom - self.size),
            )
            boundary_hit = (
                abs(next_x - target.x) > 1e-6 or abs(next_y - target.y) > 1e-6
            )
            self.pos.update(next_x, next_y)
            if boundary_hit:
                self.movement_trace.append(self.center)
                self._enter_stun(wall_impact=True)
                return
            if self.rect.collidelist(blockers) != -1:
                self.pos.update(old)
                self._enter_stun(wall_impact=True)
                return
            self.movement_trace.append(self.center)
            remaining -= distance

        if self.pos.distance_to(self.charge_origin) >= self.max_charge_dist - 0.01:
            if self.charges_remaining > 0:
                self._set_state("warning", self.warning_time)
            else:
                self._enter_stun()

    def _enter_stun(self, *, wall_impact: bool = False) -> None:
        self.charges_remaining = 0
        self.wall_impact_pending = self.wall_impact_pending or wall_impact
        self._set_state("stun", self.stun_time)

    def _set_state(self, state: str, timer: float = 0.0) -> None:
        self.state = state
        self.state_timer = timer
        self.state_clock = 0.0

    def take_damage(self, amount: int) -> str:
        if self.dead:
            return "dead"
        self.hp = max(0, self.hp - amount)
        self.hurt_timer = 0.12
        if self.hp > 0:
            return "hit"
        if self.phase == 1:
            self._load_phase(2)
            self.charges_remaining = 0
            self.contact_available = False
            self.charge_trace_active = False
            self.movement_trace.clear()
            self._set_state("recover", self.recovery_time)
            return "phase_changed"
        self.dead = True
        self.death_clock = 0.0
        self.hp = 0
        self.charges_remaining = 0
        self.contact_available = False
        self.charge_trace_active = False
        self.movement_trace.clear()
        self._set_state("dead")
        return "dead"

    def contact_with_player(self, player: Player) -> int:
        if not self.charge_trace_active or not self.contact_available:
            return 0
        player_center = pygame.Vector2(player.rect.center)
        minimum = self.separation_radius + player.separation_radius
        point_hit = any(
            point.distance_to(player_center) < minimum for point in self.movement_trace
        )
        segment_hit = any(
            self._distance_to_segment(player_center, start, end) < minimum
            for start, end in zip(
                self.movement_trace,
                self.movement_trace[1:],
                strict=False,
            )
        )
        if not point_hit and not segment_hit:
            return 0
        self.contact_available = False
        return self.contact_damage

    @staticmethod
    def _distance_to_segment(
        point: pygame.Vector2,
        start: pygame.Vector2,
        end: pygame.Vector2,
    ) -> float:
        segment = end - start
        length_squared = segment.length_squared()
        if length_squared == 0:
            return point.distance_to(start)
        progress = max(0.0, min(1.0, (point - start).dot(segment) / length_squared))
        return point.distance_to(start + segment * progress)

    def consume_wall_impact(self) -> bool:
        pending = self.wall_impact_pending
        self.wall_impact_pending = False
        return pending

    def push(
        self,
        delta: pygame.Vector2,
        room,
        blockers: list[pygame.Rect],
    ) -> None:
        old = pygame.Vector2(self.pos)
        self.pos.x = min(
            max(self.pos.x + delta.x, float(room.rect.left)),
            float(room.rect.right - self.size),
        )
        if self.rect.collidelist(blockers) != -1:
            self.pos.x = old.x
        old_y = self.pos.y
        self.pos.y = min(
            max(self.pos.y + delta.y, float(room.rect.top)),
            float(room.rect.bottom - self.size),
        )
        if self.rect.collidelist(blockers) != -1:
            self.pos.y = old_y

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        rect = self.rect.move(-cam_x, -cam_y)
        if self.dead:
            action = "death"
            clock = self.death_clock
            frames = 8
            fps = frames / BOSS_DEATH_TIME
            loop = False
            path = "characters/boss/boss_death_sheet.png"
        else:
            action = {
                "recover": "idle",
                "warning": "charge",
                "charge": "charge",
                "stun": "stun",
            }[self.state]
            clock = self.state_clock
            frames = {"idle": 2, "charge": 3, "stun": 2}[action]
            fps = {"idle": 3.0, "charge": 12.0, "stun": 5.0}[action]
            loop = self.state != "warning"
            if self.state == "warning":
                fps = frames / self.warning_time
            elif self.state == "charge":
                clock = frames - 1
                fps = 1.0
                loop = False
            direction = _direction_name(self.facing)
            path = (
                f"characters/boss/boss_phase{self.phase}_{action}_{direction}_sheet.png"
            )
        sprite = _animation_sprite(
            path,
            BOSS_CANVAS_SIZE,
            clock,
            frames,
            fps,
            loop=loop,
        )
        if sprite is None:
            fallback = (
                "characters/boss/boss_death_7.png"
                if action == "death"
                else path.removesuffix("_sheet.png") + ".png"
            )
            sprite = SPRITES.load(fallback, BOSS_CANVAS_SIZE)
        if sprite is not None and self.hurt_timer > 0:
            sprite = sprite.copy()
            sprite.fill((180, 180, 180, 0), special_flags=pygame.BLEND_RGBA_ADD)
        shadow = SPRITES.load("props/shadow_large.png", (48, 18))
        if shadow is not None and not self.dead:
            surface.blit(
                shadow,
                shadow.get_rect(midbottom=(rect.centerx, rect.bottom + 3)),
            )
        if sprite is None:
            pygame.draw.rect(surface, (105, 110, 105), rect)
        else:
            surface.blit(sprite, sprite.get_rect(midbottom=rect.midbottom))
        if self.state == "warning" and not self.dead:
            progress = 1.0 - max(0.0, self.state_timer) / self.warning_time
            frame = min(3, int(progress * 4))
            warning = SPRITES.load(f"effects/fx_charge_warning_{frame}.png", (64, 64))
            if warning is not None:
                surface.blit(warning, warning.get_rect(center=rect.center))


class Bullet:
    def __init__(self, pos: pygame.Vector2, direction: pygame.Vector2) -> None:
        self.pos = pygame.Vector2(pos)
        self.direction = direction.normalize()
        self.origin = pygame.Vector2(pos)
        self.size = BULLET_SIZE
        self.animation_clock = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.size, self.size).move(self.pos.x, self.pos.y)

    def update(self, dt: float) -> bool:
        self.animation_clock += dt
        self.pos += self.direction * BULLET_SPEED * dt * 60
        return self.pos.distance_to(self.origin) <= BULLET_RANGE

    def draw(self, surface: pygame.Surface, cam_x: float = 0, cam_y: float = 0) -> None:
        rect = self.rect.move(-cam_x, -cam_y)
        center = pygame.Vector2(rect.center)
        tail = center - self.direction * 8
        pygame.draw.line(surface, (255, 142, 52), tail, center, 3)
        sprite = SPRITES.frame(
            "props/bullet_sheet.png",
            (self.size, self.size),
            int(self.animation_clock * 16) % 2,
        )
        if sprite is None:
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
        elapsed = COIN_LIFETIME - self.timer
        sprite = SPRITES.frame(
            "props/coin_sheet.png",
            (16, 16),
            int(elapsed * 8) % 4,
        )
        if sprite is None:
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


def drop_coin(pos: pygame.Vector2, rng: random.Random | None = None) -> Coin | None:
    source = rng or random
    if source.random() <= COIN_DROP_CHANCE:
        return Coin(pos)
    return None

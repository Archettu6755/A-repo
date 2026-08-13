import pygame

from .audio import AUDIO
from .config import (
    BOX_COLOR,
    BULLET_SIZE,
    COIN_VALUE,
    COLORS,
    FPS,
    HEART_GAP,
    HEART_ORIGIN,
    HEART_SIZE,
    HEARTS_PER_ROW,
    LEVEL_CLEAR_DELAY,
    MAX_VISUAL_EFFECTS,
    OBSTACLE_BORDER,
    OBSTACLE_COLORS,
    PLAYER_ATTACK,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_MAX_HP,
    PLAYER_SPEED,
    ROOM_SCREEN_LEFT,
    ROOM_SCREEN_TOP,
    VISION_RADIUS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    ZOMBIE_COUNT_PER_ROOM_RANGE,
    ZOMBIE_TYPE_WEIGHTS,
)
from .controls import Controls, event_key
from .effects import VisualEffect, numbered_paths
from .entities import Boss, Bullet, Coin, Player, Zombie, drop_coin
from .fonts import load_font, warn_if_no_cjk_font
from .level import Level
from .resources import ROOM_ART, SPRITES
from .shop import ShopScreen


class Game:
    def __init__(self) -> None:
        pygame.init()
        AUDIO.initialize()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.key.stop_text_input()
        pygame.display.set_caption("像素士兵 VS 僵尸")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.controls = Controls()
        self.font_title = load_font(48, bold=True)
        self.font_hud = load_font(28)
        self.font_hint = load_font(20)
        self.player = Player(
            pygame.Vector2(0, 0),
            PLAYER_MAX_HP,
            PLAYER_ATTACK,
            PLAYER_FIRE_COOLDOWN,
            PLAYER_SPEED,
        )
        self.coins = 0
        self.level = 1
        self.level_map = Level(1)
        self.current_room = 0
        self.bullets: list[Bullet] = []
        self.coin_items: list[Coin] = []
        self.effects: list[VisualEffect] = []
        self.boss: Boss | None = None
        self.shop: ShopScreen | None = None
        self.purchase_counts: dict[str, int] = {}
        self.clear_timer = 0.0
        self.screen_shake_timer = 0.0
        self.paused_from = "playing"
        self.paused_selection = 0
        self.stats_from = "playing"
        self.state = "title"

    def start_level(self, level: int, fresh: bool) -> None:
        self.controls.clear()
        self.level = level
        self.level_map = Level(level)
        self.boss = None
        if fresh:
            self.player.max_hp = PLAYER_MAX_HP
            self.player.attack = PLAYER_ATTACK
            self.player.cooldown = PLAYER_FIRE_COOLDOWN
            self.player.speed = PLAYER_SPEED
            self.coins = 0
            self.purchase_counts.clear()
        self.player.hp = self.player.max_hp
        self.player.dead = False
        self.player.death_clock = 0.0
        self.player.moving = False
        self.player.fire_timer = 0.0
        self.player.shoot_pose_timer = 0.0
        self.player.invincible_timer = 0.0
        self.current_room = 0
        self.player.pos = self.room.spawn.copy()
        self._spawn_zombies()
        self.level_map.update_doors(self.current_room)
        self.bullets.clear()
        self.coin_items.clear()
        self.effects.clear()
        self.clear_timer = 0.0
        self.state = "playing"

    def start_boss_room(self) -> None:
        self.controls.clear()
        self.level = 3
        self.shop = None
        self.level_map = Level(3, boss_only=True)
        self.current_room = 0
        self.player.pos = self.room.spawn.copy()
        self.player.moving = False
        self.player.fire_timer = 0.0
        self.player.shoot_pose_timer = 0.0
        self.player.invincible_timer = 0.0
        if self.room.boss_spawn is None:
            raise RuntimeError("Boss 房缺少 Boss 出生点")
        self.boss = Boss(self.room.boss_spawn)
        self.bullets.clear()
        self.coin_items.clear()
        self.effects.clear()
        self.state = "boss_room"

    @property
    def room(self):
        return self.level_map.rooms[self.current_room]

    @property
    def camera(self) -> tuple[float, float]:
        room_rect = self.room.rect
        cam_x = room_rect.left - ROOM_SCREEN_LEFT
        cam_y = room_rect.top - ROOM_SCREEN_TOP
        if self.screen_shake_timer > 0:
            phase = int(self.screen_shake_timer * 120)
            cam_x += -2 if phase % 2 else 2
            cam_y += (phase % 3 - 1) * 2
        return cam_x, cam_y

    def _to_screen(self, pos: tuple[float, float]) -> tuple[float, float]:
        cam_x, cam_y = self.camera
        return pos[0] - cam_x, pos[1] - cam_y

    def _spawn_zombies(self) -> None:
        count_range = ZOMBIE_COUNT_PER_ROOM_RANGE[self.level]
        weights = ZOMBIE_TYPE_WEIGHTS[self.level]

        def create(pos: pygame.Vector2) -> Zombie:
            kind = self.level_map.rng.choices(
                list(weights),
                weights=list(weights.values()),
                k=1,
            )[0]
            return Zombie(kind, pos, self.level, self.level_map.rng)

        self.level_map.spawn_zombies(count_range, create)

    def _room_blockers(self) -> list[pygame.Rect]:
        return self.level_map.blockers_for(self.current_room)

    def _add_effect(self, effect: VisualEffect) -> None:
        if len(self.effects) >= MAX_VISUAL_EFFECTS:
            temporary = next(
                (item for item in self.effects if item.duration is not None), None
            )
            self.effects.remove(temporary or self.effects[0])
        self.effects.append(effect)

    def _update_effects(self, dt: float) -> None:
        self.effects = [effect for effect in self.effects if effect.update(dt)]

    @staticmethod
    def _direction_name(direction: pygame.Vector2) -> str:
        if abs(direction.x) >= abs(direction.y):
            return "right" if direction.x >= 0 else "left"
        return "down" if direction.y >= 0 else "up"

    def _pause(self) -> None:
        self.paused_from = self.state
        self.paused_selection = 0
        self.state = "paused"

    def _resume(self) -> None:
        self.controls.clear()
        self.state = self.paused_from

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if self.state == "boss_death":
                continue
            self.controls.handle_event(event)
            key = event_key(event) if event.type == pygame.KEYDOWN else None
            if self.state == "title":
                if event.type == pygame.KEYDOWN:
                    self.start_level(1, fresh=True)
            elif self.state == "stats":
                if event.type == pygame.KEYDOWN and key in (
                    pygame.K_e,
                    pygame.K_ESCAPE,
                ):
                    self.controls.clear()
                    self.state = self.stats_from
            elif self.state == "paused":
                self._handle_pause_event(event)
            elif self.state == "game_over":
                if event.type == pygame.KEYDOWN:
                    self.coins = 0
                    self.start_level(self.level, fresh=False)
            elif self.state == "shop":
                self._handle_shop_event(event)
            elif self.state == "coming_soon":
                if event.type == pygame.KEYDOWN:
                    self.controls.clear()
                    self.state = "title"
            elif self.state in ("playing", "boss_room"):
                if event.type == pygame.KEYDOWN and key == pygame.K_ESCAPE:
                    self._pause()
                elif event.type == pygame.KEYDOWN and key == pygame.K_e:
                    self.stats_from = self.state
                    self.state = "stats"

    def _handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        key = event_key(event)
        if key == pygame.K_ESCAPE:
            self._resume()
        elif key in (pygame.K_UP, pygame.K_DOWN):
            self.paused_selection = 1 - self.paused_selection
        elif key == pygame.K_f:
            if self.paused_selection == 0:
                self._resume()
            else:
                self.state = "title"

    def _handle_shop_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN or self.shop is None:
            return
        result = self.shop.handle_event(event)
        if result != "exit":
            return
        self.coins = self.shop.coins
        if self.level == 3:
            self.start_boss_room()
        else:
            self.start_level(self.level + 1, fresh=False)

    def update(self, dt: float) -> None:
        if self.state in (
            "playing",
            "boss_room",
            "boss_death",
            "level_clear",
            "game_over",
        ):
            self._update_effects(dt)
            self.level_map.update_animations(dt)
        self.screen_shake_timer = max(0.0, self.screen_shake_timer - dt)
        if self.state == "playing":
            self._update_playing(dt)
        elif self.state == "boss_room":
            self._update_boss_room(dt)
        elif self.state == "boss_death":
            self._update_boss_death(dt)
        elif self.state == "level_clear":
            self._update_clear(dt)
        elif self.state == "game_over":
            self.player.update(dt)
        elif self.state == "shop" and self.shop is not None:
            self.shop.update(dt)
        self.controls.update(dt)

    def _player_input(self, dt: float) -> tuple[float, float]:
        axis_x, axis_y = self.controls.movement_axis()
        frame_scale = dt * 60
        dx = axis_x * self.player.speed * frame_scale
        dy = axis_y * self.player.speed * frame_scale
        return dx, dy

    def _update_clear(self, dt: float) -> None:
        dx, dy = self._player_input(dt)
        self.player.move(dx, dy, self._room_blockers())
        self.player.update(dt)
        self._update_room_transition()
        self._update_coins(dt)
        self.clear_timer -= dt
        if self.clear_timer <= 0:
            self.player.hp = self.player.max_hp
            self.shop = ShopScreen(
                self.level,
                self.coins,
                self.player,
                self.purchase_counts,
            )
            self.state = "shop"

    def _update_playing(self, dt: float) -> None:
        dx, dy = self._player_input(dt)
        self.player.move(dx, dy, self._room_blockers())
        self.player.update(dt)
        self._update_room_transition()
        self._activate_switch()
        self._try_fire()
        self._update_projectiles(dt, can_hit_enemies=True)

        blockers = self._room_blockers()
        player_center = pygame.Vector2(self.player.rect.center)
        for zombie in self.room.zombies:
            zombie.update(dt, player_center, self.room, blockers)
            if zombie.consume_wall_impact():
                AUDIO.play("charge_wall")
                self._add_effect(
                    VisualEffect(
                        numbered_paths("effects/fx_wall_dust", 4),
                        pygame.Vector2(zombie.rect.center),
                        (24, 24),
                        0.2,
                        self.current_room,
                        layer="foreground",
                    )
                )

        self._resolve_zombie_overlaps()
        for zombie in self.room.zombies:
            if not zombie.hits_player(self.player):
                continue
            zombie.stun()
            self._separate_player_and_zombie(zombie)
            if self.player.take_hit(zombie.damage):
                AUDIO.play("player_hurt")
                self.screen_shake_timer = 0.16
                self._add_effect(
                    VisualEffect(
                        numbered_paths("effects/fx_player_hurt", 4),
                        pygame.Vector2(self.player.rect.midbottom),
                        (32, 48),
                        0.2,
                        self.current_room,
                        anchor="midbottom",
                    )
                )
                if self.player.hp <= 0:
                    self.state = "game_over"
                    return

        self._update_coins(dt)
        self.level_map.update_doors(self.current_room)
        if all(room.cleared for room in self.level_map.rooms):
            self.clear_timer = LEVEL_CLEAR_DELAY
            self.state = "level_clear"

    def _update_boss_room(self, dt: float) -> None:
        if self.boss is None:
            raise RuntimeError("Boss 房没有 Boss 实体")
        dx, dy = self._player_input(dt)
        self.player.move(dx, dy, self._room_blockers())
        self.player.update(dt)
        self._try_fire()
        self._update_projectiles(dt, can_hit_enemies=False, can_hit_boss=True)
        if self.state == "boss_death":
            return

        blockers = self._room_blockers()
        self.boss.update(
            dt,
            pygame.Vector2(self.player.rect.center),
            self.room,
            blockers,
        )
        if self.boss.consume_wall_impact():
            AUDIO.play("charge_wall")
            self._add_effect(
                VisualEffect(
                    numbered_paths("effects/fx_wall_dust", 4),
                    pygame.Vector2(self.boss.rect.center),
                    (32, 32),
                    0.2,
                    self.current_room,
                    layer="foreground",
                )
            )

        damage = self.boss.contact_with_player(self.player)
        self._separate_player_and_boss()
        if damage and self.player.take_hit(damage):
            AUDIO.play("player_hurt")
            self.screen_shake_timer = 0.2
            self._add_effect(
                VisualEffect(
                    numbered_paths("effects/fx_player_hurt", 4),
                    pygame.Vector2(self.player.rect.midbottom),
                    (32, 48),
                    0.2,
                    self.current_room,
                    anchor="midbottom",
                )
            )
            if self.player.hp <= 0:
                self.state = "game_over"

    def _begin_boss_death(self) -> None:
        self.controls.clear()
        self.player.moving = False
        self.state = "boss_death"

    def _update_boss_death(self, dt: float) -> None:
        if self.boss is None:
            raise RuntimeError("Boss 死亡状态缺少 Boss 实体")
        self.boss.update(
            dt,
            pygame.Vector2(self.player.rect.center),
            self.room,
            self._room_blockers(),
        )
        if self.boss.death_finished:
            self.controls.clear()
            self.state = "coming_soon"

    def _update_room_transition(self) -> None:
        previous = self.current_room
        current = self.level_map.room_at(self.player.rect.center, previous)
        if current == previous:
            return
        self.player.pos = self.level_map.place_inside_room(
            self.player.pos,
            self.player.size,
            previous,
            current,
        )
        self.current_room = current
        self.bullets.clear()
        self.level_map.update_doors(self.current_room)

    def _activate_switch(self) -> None:
        switch = self.room.switch
        if switch is None or switch.active:
            return
        if switch.rect.colliderect(self.player.rect):
            switch.active = True
            self.room.lit = True
            AUDIO.play("switch")

    def _try_fire(self) -> None:
        if not self.controls.wants_fire() or not self.player.try_fire():
            return
        self.controls.consume_fire()
        direction = self.player.facing.copy()
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        muzzle = (
            pygame.Vector2(self.player.rect.center)
            + direction * (self.player.size / 2 + BULLET_SIZE / 2)
            - pygame.Vector2(BULLET_SIZE / 2)
        )
        self.bullets.append(Bullet(muzzle, direction))
        AUDIO.play("shoot")
        flash_pos = pygame.Vector2(self.player.rect.center) + direction * (
            self.player.size / 2 + 8
        )
        name = self._direction_name(direction)
        self._add_effect(
            VisualEffect(
                numbered_paths(f"effects/fx_muzzle_{name}", 4),
                flash_pos,
                (16, 16),
                0.12,
                self.current_room,
            )
        )

    def _update_projectiles(
        self,
        dt: float,
        *,
        can_hit_enemies: bool,
        can_hit_boss: bool = False,
    ) -> None:
        for bullet in list(self.bullets):
            alive = bullet.update(dt)
            if alive and not self.room.rect.colliderect(bullet.rect):
                alive = False
            projectile_blockers = self.level_map.projectile_blockers_for(
                self.current_room
            )
            if alive and bullet.rect.collidelist(projectile_blockers) != -1:
                alive = False
                AUDIO.play("bullet_impact")
                self._add_effect(
                    VisualEffect(
                        numbered_paths("effects/fx_bullet_impact", 4),
                        pygame.Vector2(bullet.rect.center),
                        (16, 16),
                        0.14,
                        self.current_room,
                        layer="foreground",
                    )
                )
            if alive:
                alive = not self._bullet_hit_box(bullet)
            if alive and can_hit_enemies:
                alive = not self._bullet_hit_zombie(bullet)
            if alive and can_hit_boss:
                alive = not self._bullet_hit_boss(bullet)
            if not alive:
                self.bullets.remove(bullet)
            if self.state == "boss_death":
                self.bullets.clear()
                return

    def _bullet_hit_box(self, bullet: Bullet) -> bool:
        for box in list(self.room.boxes):
            if not bullet.rect.colliderect(box.rect):
                continue
            if box.hit(self.player.attack):
                self.room.boxes.remove(box)
                AUDIO.play("crate_break")
                self._add_effect(
                    VisualEffect(
                        numbered_paths("effects/fx_crate_debris", 5),
                        pygame.Vector2(box.rect.center),
                        (32, 32),
                        0.3,
                        self.current_room,
                    )
                )
                coin = drop_coin(
                    pygame.Vector2(box.rect.center),
                    self.level_map.rng,
                )
                if coin:
                    self.coin_items.append(coin)
                    self._add_effect(
                        VisualEffect(
                            numbered_paths("effects/fx_coin_pop", 4),
                            pygame.Vector2(box.rect.center),
                            (24, 24),
                            0.25,
                            self.current_room,
                        )
                    )
            else:
                AUDIO.play("bullet_impact")
                self._add_effect(
                    VisualEffect(
                        numbered_paths("effects/fx_bullet_impact", 4),
                        pygame.Vector2(bullet.rect.center),
                        (16, 16),
                        0.14,
                        self.current_room,
                        layer="foreground",
                    )
                )
            return True
        return False

    def _bullet_hit_zombie(self, bullet: Bullet) -> bool:
        for zombie in list(self.room.zombies):
            if not bullet.rect.colliderect(zombie.rect):
                continue
            self._add_effect(
                VisualEffect(
                    numbered_paths("effects/fx_bullet_impact", 4),
                    pygame.Vector2(bullet.rect.center),
                    (16, 16),
                    0.14,
                    self.current_room,
                    layer="foreground",
                )
            )
            zombie.push(
                bullet.direction * 5,
                self.room,
                self._room_blockers(),
            )
            if zombie.take_damage(self.player.attack):
                AUDIO.play("zombie_death")
                self.room.zombies.remove(zombie)
                canvas = {
                    "normal": (32, 48),
                    "fast": (32, 40),
                    "heavy": (48, 56),
                }[zombie.kind]
                self._add_effect(
                    VisualEffect(
                        tuple(
                            f"characters/zombie_{zombie.kind}/"
                            f"zombie_{zombie.kind}_death_{index}.png"
                            for index in (0, 1, 2, 2, 3, 3)
                        ),
                        pygame.Vector2(zombie.rect.midbottom),
                        canvas,
                        0.5,
                        self.current_room,
                        anchor="midbottom",
                    )
                )
                blood_index = self.level_map.rng.randint(1, 8)
                self._add_effect(
                    VisualEffect(
                        (f"effects/blood_{blood_index:02d}.png",),
                        pygame.Vector2(zombie.rect.center),
                        (32, 32),
                        None,
                        self.current_room,
                        layer="ground",
                    )
                )
                coin = drop_coin(
                    pygame.Vector2(zombie.rect.center),
                    self.level_map.rng,
                )
                if coin:
                    self.coin_items.append(coin)
                    self._add_effect(
                        VisualEffect(
                            numbered_paths("effects/fx_coin_pop", 4),
                            pygame.Vector2(zombie.rect.center),
                            (24, 24),
                            0.25,
                            self.current_room,
                        )
                    )
            else:
                AUDIO.play("zombie_hit")
            return True
        return False

    def _bullet_hit_boss(self, bullet: Bullet) -> bool:
        if self.boss is None or self.boss.dead:
            return False
        if not bullet.rect.colliderect(self.boss.rect):
            return False
        self._add_effect(
            VisualEffect(
                numbered_paths("effects/fx_bullet_impact", 4),
                pygame.Vector2(bullet.rect.center),
                (16, 16),
                0.14,
                self.current_room,
                layer="foreground",
            )
        )
        result = self.boss.take_damage(self.player.attack)
        if result == "dead":
            AUDIO.play("zombie_death")
            self._begin_boss_death()
        else:
            AUDIO.play("zombie_hit")
        return True

    def _resolve_zombie_overlaps(self) -> None:
        zombies = self.room.zombies
        blockers = self._room_blockers()
        for first_index, first in enumerate(zombies):
            for second in zombies[first_index + 1 :]:
                first_center = pygame.Vector2(first.rect.center)
                second_center = pygame.Vector2(second.rect.center)
                delta = second_center - first_center
                distance = delta.length()
                minimum = first.separation_radius + second.separation_radius
                if distance >= minimum:
                    continue
                if distance == 0:
                    direction = pygame.Vector2(1, 0)
                else:
                    direction = delta / distance
                overlap = minimum - distance
                if first.state == "charge" and second.state != "charge":
                    second.push(direction * overlap, self.room, blockers)
                elif second.state == "charge" and first.state != "charge":
                    first.push(-direction * overlap, self.room, blockers)
                else:
                    first.push(-direction * overlap / 2, self.room, blockers)
                    second.push(direction * overlap / 2, self.room, blockers)

    def _separate_player_and_zombie(self, zombie: Zombie) -> None:
        player_center = pygame.Vector2(self.player.rect.center)
        zombie_center = pygame.Vector2(zombie.rect.center)
        delta = zombie_center - player_center
        distance = delta.length()
        minimum = self.player.separation_radius + zombie.separation_radius
        if distance >= minimum:
            return
        direction = pygame.Vector2(1, 0) if distance == 0 else delta / distance
        overlap = minimum - distance + 1
        blockers = self._room_blockers()
        self.player.push(-direction * overlap / 2, blockers)
        zombie.push(direction * overlap / 2, self.room, blockers)

    def _separate_player_and_boss(self) -> None:
        if self.boss is None:
            return
        player_center = pygame.Vector2(self.player.rect.center)
        boss_center = pygame.Vector2(self.boss.rect.center)
        delta = boss_center - player_center
        distance = delta.length()
        minimum = self.player.separation_radius + self.boss.separation_radius
        if distance >= minimum:
            return
        direction = pygame.Vector2(1, 0) if distance == 0 else delta / distance
        overlap = minimum - distance + 1
        blockers = self._room_blockers()
        self.player.push(-direction * overlap, blockers)
        remaining = minimum - pygame.Vector2(self.boss.rect.center).distance_to(
            self.player.rect.center
        )
        if remaining > 0 and self.boss.state != "charge":
            self.boss.push(direction * (remaining + 1), self.room, blockers)

    def _update_coins(self, dt: float) -> None:
        for coin in list(self.coin_items):
            if not coin.update(dt):
                self.coin_items.remove(coin)
            elif coin.rect.colliderect(self.player.rect):
                self.coins += COIN_VALUE
                self.coin_items.remove(coin)
                AUDIO.play("coin")

    def draw(self) -> None:
        pygame.mouse.set_visible(False)
        self.screen.fill(COLORS["background"])
        if self.state == "title":
            self._draw_title()
        elif self.state in (
            "playing",
            "boss_room",
            "boss_death",
            "paused",
            "game_over",
            "stats",
            "level_clear",
            "coming_soon",
        ):
            self._draw_level()
            if self.state == "paused":
                self._draw_paused()
            elif self.state == "game_over":
                self._draw_game_over()
            elif self.state == "stats":
                self._draw_stats()
            elif self.state == "level_clear":
                self._draw_level_clear()
            elif self.state == "coming_soon":
                self._draw_coming_soon()
        elif self.state == "shop" and self.shop is not None:
            self.shop.draw(self.screen)
        pygame.display.flip()

    def _draw_title(self) -> None:
        background = SPRITES.load(
            "ui/title_background.png", (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
        if background is not None:
            self.screen.blit(background, (0, 0))
            shade = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            shade.fill((8, 12, 18, 135))
            self.screen.blit(shade, (0, 0))
        title = self.font_title.render("像素士兵 VS 僵尸", True, COLORS["title"])
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 180))
        hint = self.font_hint.render("按任意键开始", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 260))

    def _draw_level(self) -> None:
        cam_x, cam_y = self.camera
        room_rect = self.room.rect.move(-cam_x, -cam_y)
        floor = ROOM_ART.floor(
            self.level,
            self.room.template_id,
            self.room.rect.size,
            self.room.visual_seed,
            self.room.decal_cells,
        )
        self.screen.blit(floor, room_rect)
        for effect in self.effects:
            if effect.room_index == self.current_room and effect.layer == "ground":
                effect.draw(self.screen, cam_x, cam_y)

        for coin in self.coin_items:
            if self.room.rect.colliderect(coin.rect):
                coin.draw(self.screen, cam_x, cam_y)

        renderables = [
            (obstacle.rect.bottom, "obstacle", obstacle)
            for obstacle in self.room.obstacles
        ]
        renderables.extend((wall.bottom, "wall", wall) for wall in self.room.walls)
        renderables.extend(
            (door.rect.bottom, "door", door)
            for door in self.level_map.doors_of(self.current_room)
        )
        renderables.extend((box.rect.bottom, "box", box) for box in self.room.boxes)
        if self.room.switch is not None:
            renderables.append(
                (self.room.switch.rect.bottom, "switch", self.room.switch)
            )
        actors = [self.player, *self.room.zombies]
        if self.boss is not None and self.room.is_boss:
            actors.append(self.boss)
        renderables.extend((actor.rect.bottom, "actor", actor) for actor in actors)
        renderables.extend(
            (effect.sort_y, "effect", effect)
            for effect in self.effects
            if effect.room_index == self.current_room and effect.layer == "actor"
        )
        for _, kind, item in sorted(renderables, key=lambda entry: entry[0]):
            if kind in {"actor", "effect"}:
                item.draw(self.screen, cam_x, cam_y)
            else:
                self._draw_scene_item(kind, item, cam_x, cam_y)

        for bullet in self.bullets:
            bullet.draw(self.screen, cam_x, cam_y)
        for effect in self.effects:
            if effect.room_index == self.current_room and effect.layer == "foreground":
                effect.draw(self.screen, cam_x, cam_y)
        self._draw_vision()
        self._draw_hud()

    def _draw_tiled_wall(self, rect: pygame.Rect) -> None:
        horizontal = rect.width >= rect.height
        if horizontal:
            path = (
                "environment/shared/wall_broken.png"
                if self.level == 3
                else "environment/shared/wall.png"
            )
            tile_size = (64, 48)
        else:
            path = "environment/shared/wall_end.png"
            tile_size = (32, 48)
        tile = SPRITES.load(path, tile_size)
        if tile is None:
            pygame.draw.rect(self.screen, COLORS["wall"], rect)
            return
        clip = pygame.Rect(rect.left, rect.top - 16, rect.width, rect.height + 16)
        self.screen.set_clip(clip)
        if horizontal:
            for x in range(rect.left, rect.right, 64):
                self.screen.blit(tile, tile.get_rect(midbottom=(x + 32, rect.bottom)))
        else:
            for y in range(rect.top, rect.bottom, 32):
                self.screen.blit(tile, tile.get_rect(midbottom=(rect.centerx, y + 32)))
        self.screen.set_clip(None)

    def _draw_door(self, door, cam_x: float, cam_y: float) -> None:
        rect = door.rect.move(-cam_x, -cam_y)
        if door.opening_timer > 0:
            path = "environment/shared/door_opening.png"
        elif door.open:
            path = "environment/shared/door_open.png"
        else:
            path = "environment/shared/door_closed.png"
        sprite = SPRITES.load(path, (64, 64))
        if sprite is None:
            color = (60, 160, 80) if door.open else (110, 80, 60)
            pygame.draw.rect(self.screen, color, rect)
        else:
            self.screen.blit(sprite, sprite.get_rect(center=rect.center))

    def _draw_scene_item(self, kind: str, item, cam_x: float, cam_y: float) -> None:
        if kind == "wall":
            self._draw_tiled_wall(item.move(-cam_x, -cam_y))
            return
        if kind == "door":
            self._draw_door(item, cam_x, cam_y)
            return
        rect = item.rect.move(-cam_x, -cam_y)
        if kind == "obstacle":
            if item.kind == "pillar":
                pillar_name = "pillar_variant_02" if self.level == 3 else "pillar"
                sprite = SPRITES.load(f"environment/shared/{pillar_name}.png", (32, 64))
                if sprite is not None:
                    self.screen.blit(sprite, sprite.get_rect(midbottom=rect.midbottom))
                else:
                    pygame.draw.rect(self.screen, OBSTACLE_COLORS[item.kind], rect)
                    pygame.draw.rect(self.screen, OBSTACLE_BORDER, rect, 2)
            elif item.kind == "wall":
                self._draw_low_wall(rect)
            else:
                self._draw_block_cluster(rect)
            return
        if kind == "box":
            damage = max(0, min(2, 3 - item.hp))
            name = ("crate_intact", "crate_damage_01", "crate_damage_02")[damage]
            sprite = SPRITES.load(f"props/{name}.png", (32, 40))
            if sprite is None:
                pygame.draw.rect(self.screen, BOX_COLOR, rect)
            else:
                self.screen.blit(sprite, sprite.get_rect(midbottom=rect.midbottom))
            return
        path = "props/switch_on.png" if item.active else "props/switch_off.png"
        sprite = SPRITES.load(path, (24, 36))
        if sprite is None:
            item.draw(self.screen, cam_x, cam_y)
        else:
            self.screen.blit(sprite, sprite.get_rect(midbottom=rect.midbottom))

    def _draw_low_wall(self, rect: pygame.Rect) -> None:
        if rect.width >= rect.height:
            long_name = "low_wall_broken" if self.level == 3 else "low_wall"
            long_tile = SPRITES.load(f"environment/shared/{long_name}.png", (64, 48))
            end_tile = SPRITES.load("environment/shared/low_wall_end.png", (32, 48))
            for offset in range(0, rect.width, 64):
                remaining = rect.width - offset
                tile = long_tile if remaining >= 64 else end_tile
                if tile is not None:
                    center_x = rect.left + offset + min(remaining, 64) // 2
                    self.screen.blit(
                        tile, tile.get_rect(midbottom=(center_x, rect.bottom))
                    )
            return
        tile = SPRITES.load("environment/shared/low_wall_end.png", (32, 48))
        if tile is None:
            pygame.draw.rect(self.screen, OBSTACLE_COLORS["wall"], rect)
            return
        for y in range(rect.top, rect.bottom, 32):
            self.screen.blit(tile, tile.get_rect(midbottom=(rect.centerx, y + 32)))

    def _draw_block_cluster(self, rect: pygame.Rect) -> None:
        if rect.width >= 96:
            path = (
                "environment/shared/water_large.png"
                if self.level == 1
                else "environment/shared/pit.png"
            )
            tile = SPRITES.load(path, (96, 64))
            step_x = 96
        else:
            path = (
                "environment/shared/water_vertical.png"
                if self.level == 1
                else "environment/shared/pit_vertical.png"
            )
            tile = SPRITES.load(path, (32, 64))
            step_x = 32
        if tile is None:
            pygame.draw.rect(self.screen, OBSTACLE_COLORS["block"], rect)
            return
        self.screen.set_clip(rect.inflate(0, 32))
        for x in range(rect.left, rect.right, step_x):
            for y in range(rect.top, rect.bottom, 64):
                bottom = min(rect.bottom, y + 64)
                self.screen.blit(
                    tile, tile.get_rect(midbottom=(x + step_x // 2, bottom))
                )
        self.screen.set_clip(None)

    def _draw_vision(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 255))
        room_rect = self.room.rect
        cam_x, cam_y = self.camera
        screen_room = room_rect.move(-cam_x, -cam_y)
        if self.room.lit:
            overlay.fill((0, 0, 0, 0), screen_room)
        player_center = self._to_screen(self.player.rect.center)
        pygame.draw.circle(
            overlay,
            (0, 0, 0, 0),
            (int(player_center[0]), int(player_center[1])),
            VISION_RADIUS,
        )
        for wall in self.room.walls:
            screen_wall = wall.move(-cam_x, -cam_y)
            visual_bounds = pygame.Rect(
                screen_wall.left,
                screen_wall.top - 16,
                screen_wall.width,
                screen_wall.height + 16,
            )
            overlay.fill((0, 0, 0, 0), visual_bounds)
        for door in self.level_map.doors_of(self.current_room):
            overlay.fill((0, 0, 0, 0), door.rect.move(-cam_x, -cam_y))
        self.screen.blit(overlay, (0, 0))

    @staticmethod
    def _heart_rect(index: int) -> pygame.Rect:
        column = index % HEARTS_PER_ROW
        row = index // HEARTS_PER_ROW
        return pygame.Rect(
            HEART_ORIGIN[0] + column * (HEART_SIZE + HEART_GAP),
            HEART_ORIGIN[1] + row * (HEART_SIZE + HEART_GAP),
            HEART_SIZE,
            HEART_SIZE,
        )

    def _draw_hud(self) -> None:
        current_hp = max(0, self.player.hp)
        for index in range(self.player.max_hp):
            filled = index < current_hp
            rect = self._heart_rect(index)
            path = "ui/heart_full.png" if filled else "ui/heart_empty.png"
            sprite = SPRITES.load(path, rect.size)
            if sprite is not None:
                self.screen.blit(sprite, rect)
            else:
                color = (205, 48, 58) if filled else (63, 43, 48)
                pygame.draw.rect(self.screen, color, rect)
        if self.room.is_boss:
            label = "关卡 3  Boss 房"
        else:
            label = (
                f"关卡 {self.level}  "
                f"房间 {self.current_room + 1}/{len(self.level_map.rooms)}"
            )
        room_text = self.font_hud.render(label, True, COLORS["hud"])
        self.screen.blit(
            room_text,
            (WINDOW_WIDTH - room_text.get_width() - 30, 20),
        )

    def _draw_coming_soon(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        panel = SPRITES.panel("ui/panel.png", (620, 280), 16)
        if panel is not None:
            self.screen.blit(panel, ((WINDOW_WIDTH - 620) // 2, 220))
        title = self.font_title.render("后续内容正在开发", True, COLORS["hud"])
        hint = self.font_hint.render("按任意键返回标题画面", True, COLORS["info"])
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 290))
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 390))

    def _draw_paused(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        panel = SPRITES.panel("ui/panel.png", (500, 350), 16)
        if panel is not None:
            self.screen.blit(panel, ((WINDOW_WIDTH - 500) // 2, 180))
        text = self.font_title.render("已暂停", True, COLORS["hud"])
        self.screen.blit(text, ((WINDOW_WIDTH - text.get_width()) // 2, 220))
        labels = ("继续游戏", "返回标题")
        for index, label in enumerate(labels):
            color = (
                COLORS["highlight"] if index == self.paused_selection else COLORS["hud"]
            )
            item = self.font_hud.render(label, True, color)
            self.screen.blit(
                item, ((WINDOW_WIDTH - item.get_width()) // 2, 310 + index * 54)
            )
        hint = self.font_hint.render(
            "方向键选择，F 确认，ESC 继续", True, COLORS["info"]
        )
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 450))

    def _draw_stats(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        panel_w, panel_h = 440, 380
        panel = pygame.Rect(
            (WINDOW_WIDTH - panel_w) // 2,
            (WINDOW_HEIGHT - panel_h) // 2,
            panel_w,
            panel_h,
        )
        panel_sprite = SPRITES.panel("ui/panel.png", panel.size, 16)
        if panel_sprite is None:
            pygame.draw.rect(self.screen, (40, 42, 52), panel)
            pygame.draw.rect(self.screen, COLORS["info"], panel, 2)
        else:
            self.screen.blit(panel_sprite, panel)
        title = self.font_title.render("属性面板", True, COLORS["highlight"])
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 24))
        rows = [
            ("生命值", f"{self.player.hp}/{self.player.max_hp}"),
            ("攻击力", str(self.player.attack)),
            ("射速", f"{self.player.cooldown:.2f} 秒/发"),
            ("移速", f"{self.player.speed:.1f}"),
            ("金币", str(self.coins)),
        ]
        y = panel.y + 96
        for name, value in rows:
            name_surf = self.font_hud.render(name, True, COLORS["hud"])
            value_surf = self.font_hud.render(value, True, COLORS["info"])
            self.screen.blit(name_surf, (panel.x + 48, y))
            self.screen.blit(value_surf, (panel.right - value_surf.get_width() - 48, y))
            y += 48
        hint = self.font_hint.render("按 E 或 ESC 关闭", True, COLORS["info"])
        self.screen.blit(
            hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 48)
        )

    def _draw_game_over(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        panel = SPRITES.panel("ui/panel.png", (560, 300), 16)
        if panel is not None:
            self.screen.blit(panel, ((WINDOW_WIDTH - 560) // 2, 190))
        text = self.font_title.render("失败！重开本关", True, COLORS["title"])
        self.screen.blit(text, ((WINDOW_WIDTH - text.get_width()) // 2, 240))
        hint = self.font_hint.render("按任意键重新挑战本关", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 330))

    def _draw_level_clear(self) -> None:
        text = self.font_title.render("敌人已清除！", True, COLORS["ok"])
        self.screen.blit(text, ((WINDOW_WIDTH - text.get_width()) // 2, 260))
        hint = self.font_hint.render("快捡金币，即将进入商店…", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 340))

    def run(self) -> None:
        warn_if_no_cjk_font()
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

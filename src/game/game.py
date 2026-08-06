import random

import pygame

from .config import (
    BOX_COLOR,
    COIN_VALUE,
    COLORS,
    FPS,
    LEVEL_CLEAR_DELAY,
    OBSTACLE_BORDER,
    OBSTACLE_COLORS,
    PLAYER_ATTACK,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_MAX_HP,
    PLAYER_SPEED,
    VISION_RADIUS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    ZOMBIE_COUNT_RANGE,
    ZOMBIE_TYPE_WEIGHTS,
)
from .entities import Bullet, Coin, Player, Zombie, drop_coin
from .fonts import load_font, warn_if_no_cjk_font
from .level import Level
from .shop import ShopScreen


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("像素士兵 VS 僵尸")
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
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
        self.shop: ShopScreen | None = None
        self.purchase_counts: dict[str, int] = {}
        self.clear_timer = 0.0
        self.paused_from = "playing"
        self.paused_selection = 0
        self.stats_from = "playing"
        self.state = "title"

    def start_level(self, level: int, fresh: bool) -> None:
        self.level = level
        self.level_map = Level(level)
        if fresh:
            self.player.max_hp = PLAYER_MAX_HP
            self.player.attack = PLAYER_ATTACK
            self.player.cooldown = PLAYER_FIRE_COOLDOWN
            self.player.speed = PLAYER_SPEED
            self.coins = 0
            self.purchase_counts.clear()
        self.player.hp = self.player.max_hp
        self.current_room = 0
        self.player.pos = self.room.spawn.copy()
        self._spawn_zombies()
        self.level_map.update_doors(self.current_room)
        self.bullets.clear()
        self.coin_items.clear()
        self.clear_timer = 0.0
        self.state = "playing"

    def start_boss_room(self) -> None:
        self.level_map = Level(3, boss_only=True)
        self.current_room = 0
        self.player.pos = self.room.spawn.copy()
        self.bullets.clear()
        self.coin_items.clear()
        self.state = "boss_room"

    @property
    def room(self):
        return self.level_map.rooms[self.current_room]

    @property
    def camera(self) -> tuple[float, float]:
        room_rect = self.room.rect
        return (
            room_rect.centerx - WINDOW_WIDTH // 2,
            room_rect.centery - WINDOW_HEIGHT // 2,
        )

    def _to_screen(self, pos: tuple[float, float]) -> tuple[float, float]:
        cam_x, cam_y = self.camera
        return pos[0] - cam_x, pos[1] - cam_y

    def _spawn_zombies(self) -> None:
        low, high = ZOMBIE_COUNT_RANGE[self.level]
        count = random.randint(low, high)
        weights = ZOMBIE_TYPE_WEIGHTS[self.level]

        def create(pos: pygame.Vector2) -> Zombie:
            kind = random.choices(
                list(weights),
                weights=list(weights.values()),
                k=1,
            )[0]
            return Zombie(kind, pos)

        self.level_map.spawn_zombies(count, create)

    def _room_blockers(self) -> list[pygame.Rect]:
        return self.level_map.blockers_for(self.current_room)

    def _pause(self) -> None:
        self.paused_from = self.state
        self.paused_selection = 0
        self.state = "paused"

    def _resume(self) -> None:
        self.state = self.paused_from

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if self.state == "title":
                if event.type == pygame.KEYDOWN:
                    self.start_level(1, fresh=True)
            elif self.state == "stats":
                if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_e,
                    pygame.K_ESCAPE,
                ):
                    self.state = self.stats_from
            elif self.state == "paused":
                self._handle_pause_event(event)
            elif self.state == "game_over":
                if event.type == pygame.KEYDOWN:
                    self.coins = 0
                    self.start_level(self.level, fresh=False)
            elif self.state == "shop":
                self._handle_shop_event(event)
            elif self.state in ("playing", "boss_room"):
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._pause()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                    self.stats_from = self.state
                    self.state = "stats"

    def _handle_pause_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._resume()
        elif event.key in (pygame.K_UP, pygame.K_DOWN):
            self.paused_selection = 1 - self.paused_selection
        elif event.key == pygame.K_f:
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
        if self.state == "playing":
            self._update_playing(dt)
        elif self.state == "boss_room":
            self._update_boss_room(dt)
        elif self.state == "level_clear":
            self._update_clear(dt)
        elif self.state == "shop" and self.shop is not None:
            self.shop.update(dt)

    def _player_input(self) -> tuple[float, float]:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.player.speed
        dy = (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * self.player.speed
        return dx, dy

    def _update_clear(self, dt: float) -> None:
        dx, dy = self._player_input()
        self.player.move(dx, dy, self._room_blockers())
        self.player.update(dt)
        self._update_room_transition()
        self._update_coins(dt)
        self.clear_timer -= dt
        if self.clear_timer <= 0:
            self.shop = ShopScreen(
                self.level,
                self.coins,
                self.player,
                self.purchase_counts,
            )
            self.state = "shop"

    def _update_playing(self, dt: float) -> None:
        dx, dy = self._player_input()
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

        self._resolve_zombie_overlaps()
        for zombie in self.room.zombies:
            if not zombie.hits_player(self.player):
                continue
            zombie.stun()
            self._separate_player_and_zombie(zombie)
            if self.player.take_hit(zombie.damage) and self.player.hp <= 0:
                self.state = "game_over"
                return

        self._update_coins(dt)
        self.level_map.update_doors(self.current_room)
        if all(room.cleared for room in self.level_map.rooms):
            self.clear_timer = LEVEL_CLEAR_DELAY
            self.state = "level_clear"

    def _update_boss_room(self, dt: float) -> None:
        dx, dy = self._player_input()
        self.player.move(dx, dy, self._room_blockers())
        self.player.update(dt)
        self._try_fire()
        self._update_projectiles(dt, can_hit_enemies=False)

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

    def _try_fire(self) -> None:
        if not pygame.key.get_pressed()[pygame.K_f] or not self.player.try_fire():
            return
        direction = self.player.facing.copy()
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        self.bullets.append(Bullet(pygame.Vector2(self.player.rect.center), direction))

    def _update_projectiles(self, dt: float, *, can_hit_enemies: bool) -> None:
        for bullet in list(self.bullets):
            alive = bullet.update(dt)
            if alive and not self.room.rect.colliderect(bullet.rect):
                alive = False
            projectile_blockers = self.level_map.projectile_blockers_for(
                self.current_room
            )
            if alive and bullet.rect.collidelist(projectile_blockers) != -1:
                alive = False
            if alive:
                alive = not self._bullet_hit_box(bullet)
            if alive and can_hit_enemies:
                alive = not self._bullet_hit_zombie(bullet)
            if not alive:
                self.bullets.remove(bullet)

    def _bullet_hit_box(self, bullet: Bullet) -> bool:
        for box in list(self.room.boxes):
            if not bullet.rect.colliderect(box.rect):
                continue
            if box.hit(self.player.attack):
                self.room.boxes.remove(box)
                coin = drop_coin(pygame.Vector2(box.rect.center))
                if coin:
                    self.coin_items.append(coin)
            return True
        return False

    def _bullet_hit_zombie(self, bullet: Bullet) -> bool:
        for zombie in list(self.room.zombies):
            if not bullet.rect.colliderect(zombie.rect):
                continue
            if zombie.take_damage(self.player.attack):
                self.room.zombies.remove(zombie)
                coin = drop_coin(pygame.Vector2(zombie.rect.center))
                if coin:
                    self.coin_items.append(coin)
            return True
        return False

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

    def _update_coins(self, dt: float) -> None:
        for coin in list(self.coin_items):
            if not coin.update(dt):
                self.coin_items.remove(coin)
            elif coin.rect.colliderect(self.player.rect):
                self.coins += COIN_VALUE
                self.coin_items.remove(coin)

    def draw(self) -> None:
        pygame.mouse.set_visible(False)
        self.screen.fill(COLORS["background"])
        if self.state == "title":
            self._draw_title()
        elif self.state in (
            "playing",
            "boss_room",
            "paused",
            "game_over",
            "stats",
            "level_clear",
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
        elif self.state == "shop" and self.shop is not None:
            self.shop.draw(self.screen)
        pygame.display.flip()

    def _draw_title(self) -> None:
        title = self.font_title.render("像素士兵 VS 僵尸", True, COLORS["title"])
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 240))
        hint = self.font_hint.render("按任意键开始", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 330))

    def _draw_level(self) -> None:
        cam_x, cam_y = self.camera
        room_rect = self.room.rect.move(-cam_x, -cam_y)
        pygame.draw.rect(self.screen, (48, 56, 62), room_rect)
        for wall in self.room.walls:
            pygame.draw.rect(self.screen, COLORS["wall"], wall.move(-cam_x, -cam_y))
        for obstacle in self.room.obstacles:
            rect = obstacle.rect.move(-cam_x, -cam_y)
            pygame.draw.rect(self.screen, OBSTACLE_COLORS[obstacle.kind], rect)
            pygame.draw.rect(self.screen, OBSTACLE_BORDER, rect, 2)
        for box in self.room.boxes:
            pygame.draw.rect(self.screen, BOX_COLOR, box.rect.move(-cam_x, -cam_y))
        if self.room.switch is not None:
            self.room.switch.draw(self.screen, cam_x, cam_y)
        for door in self.level_map.doors_of(self.current_room):
            door.draw(self.screen, cam_x, cam_y)

        actors = [self.player, *self.room.zombies]
        for actor in sorted(actors, key=lambda item: item.rect.bottom):
            actor.draw(self.screen, cam_x, cam_y)
        for bullet in self.bullets:
            bullet.draw(self.screen, cam_x, cam_y)
        for coin in self.coin_items:
            if self.room.rect.colliderect(coin.rect):
                coin.draw(self.screen, cam_x, cam_y)
        self._draw_vision()
        self._draw_hud()

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
            overlay.fill((0, 0, 0, 0), wall.move(-cam_x, -cam_y))
        self.screen.blit(overlay, (0, 0))

    def _draw_hud(self) -> None:
        bar_w, bar_h = 240, 22
        bar_x, bar_y = 24, 24
        bg_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(self.screen, (60, 60, 70), bg_rect)
        ratio = self.player.hp / self.player.max_hp
        if ratio > 0.5:
            color = COLORS["ok"]
        elif ratio > 0.25:
            color = COLORS["highlight"]
        else:
            color = COLORS["error"]
        fg_rect = pygame.Rect(bar_x, bar_y, int(bar_w * ratio), bar_h)
        pygame.draw.rect(self.screen, color, fg_rect)
        hp_text = self.font_hud.render(
            f"{self.player.hp}/{self.player.max_hp}",
            True,
            COLORS["hud"],
        )
        self.screen.blit(hp_text, (bar_x + bar_w + 16, bar_y - 4))
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
            (WINDOW_WIDTH - room_text.get_width() - 30, bar_y - 4),
        )

    def _draw_paused(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
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
        pygame.draw.rect(self.screen, (40, 42, 52), panel)
        pygame.draw.rect(self.screen, COLORS["info"], panel, 2)
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

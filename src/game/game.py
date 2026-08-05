import random

import pygame

from .config import (
    COIN_VALUE,
    COLORS,
    FPS,
    HEAVY_CHANCE,
    LEVEL_CLEAR_DELAY,
    LEVEL_COUNT,
    PLAYER_ATTACK,
    PLAYER_FIRE_COOLDOWN,
    PLAYER_MAX_HP,
    PLAYER_SPEED,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    ZOMBIE_COUNT_RANGE,
)
from .entities import Bullet, Coin, Player, Zombie, drop_coin
from .fonts import load_font, warn_if_no_cjk_font
from .level import Room
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
        self.state = "title"
        self.player = Player(
            pygame.Vector2(0, 0),
            PLAYER_MAX_HP,
            PLAYER_ATTACK,
            PLAYER_FIRE_COOLDOWN,
            PLAYER_SPEED,
        )
        self.coins = 0
        self.level = 1
        self.room = Room()
        self.zombies: list[Zombie] = []
        self.bullets: list[Bullet] = []
        self.coin_items: list[Coin] = []
        self.shop: ShopScreen | None = None
        self.clear_timer = 0.0
        self.start_level(1, fresh=True)

    def start_level(self, level: int, fresh: bool) -> None:
        self.level = level
        self.room = Room()
        if fresh:
            self.player.max_hp = PLAYER_MAX_HP
            self.player.attack = PLAYER_ATTACK
            self.player.cooldown = PLAYER_FIRE_COOLDOWN
            self.player.speed = PLAYER_SPEED
            self.coins = 0
        self.player.hp = self.player.max_hp
        spawn = pygame.Vector2(
            self.room.rect.centerx - self.player.size / 2,
            self.room.rect.centery - self.player.size / 2,
        )
        self.player.pos = spawn
        self.zombies = self._spawn_zombies()
        self.bullets.clear()
        self.coin_items.clear()
        self.clear_timer = 0.0
        self.state = "playing"

    def _spawn_zombies(self) -> list[Zombie]:
        low, high = ZOMBIE_COUNT_RANGE[self.level]
        count = random.randint(low, high)
        weights = {"normal": 60}
        heavy_chance = HEAVY_CHANCE[self.level]
        if heavy_chance > 0:
            weights["heavy"] = int(heavy_chance * 100)
        weights["fast"] = 25
        zombies = []
        for _ in range(count):
            pos = self.room.random_spawn_far_from(self.player.pos, min_distance=150)
            kind = random.choices(
                list(weights.keys()), weights=list(weights.values()), k=1
            )[0]
            zombies.append(Zombie(kind, pos))
        return zombies

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if self.state == "title":
                if event.type == pygame.KEYDOWN:
                    self.state = "playing"
            elif self.state == "stats":
                if event.type == pygame.KEYDOWN and (
                    event.key == pygame.K_e or event.key == pygame.K_ESCAPE
                ):
                    self.state = "playing"
            elif self.state == "paused":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "playing"
            elif self.state == "game_over":
                if event.type == pygame.KEYDOWN:
                    self.coins = 0
                    self.start_level(self.level, fresh=False)
            elif self.state == "shop":
                if event.type == pygame.KEYDOWN:
                    result = self.shop.handle_event(event)
                    if result == "exit":
                        if self.level >= LEVEL_COUNT:
                            self.state = "title"
                        else:
                            self.start_level(self.level + 1, fresh=False)
            elif self.state == "playing" and (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                self.state = "paused"
            elif self.state == "playing" and (
                event.type == pygame.KEYDOWN and event.key == pygame.K_e
            ):
                self.state = "stats"

    def update(self, dt: float) -> None:
        if self.state == "playing":
            self._update_playing(dt)
        elif self.state == "level_clear":
            self._update_clear(dt)
        elif self.state == "shop":
            self.shop.update(dt)

    def _update_clear(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * self.player.speed
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * self.player.speed
        self.player.move(dx, dy, self.room)
        self.player.update(dt)
        for coin in list(self.coin_items):
            if not coin.update(dt):
                self.coin_items.remove(coin)
            elif coin.rect.colliderect(self.player.rect):
                self.coins += COIN_VALUE
                self.coin_items.remove(coin)
        self.clear_timer -= dt
        if self.clear_timer <= 0:
            self.shop = ShopScreen(self.level, self.coins, self.player)
            self.state = "shop"

    def _update_playing(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] - keys[pygame.K_a]) * self.player.speed
        dy = (keys[pygame.K_s] - keys[pygame.K_w]) * self.player.speed
        self.player.move(dx, dy, self.room)
        self.player.update(dt)

        if keys[pygame.K_f] and self.player.try_fire():
            origin = pygame.Vector2(self.player.rect.center)
            direction = self.player.facing.copy()
            if direction.length_squared() == 0:
                direction = pygame.Vector2(1, 0)
            self.bullets.append(Bullet(origin, direction))

        for bullet in list(self.bullets):
            alive = bullet.update(dt)
            if alive and not bullet.rect.colliderect(self.room.rect):
                alive = False
            if alive:
                for zombie in self.zombies:
                    if bullet.rect.colliderect(zombie.rect):
                        if zombie.take_damage(self.player.attack):
                            self.zombies.remove(zombie)
                            coin = drop_coin(pygame.Vector2(zombie.rect.center))
                            if coin:
                                self.coin_items.append(coin)
                        alive = False
                        break
            if not alive:
                self.bullets.remove(bullet)

        for zombie in self.zombies:
            zombie.update(dt, self.player.pos, self.room)
            if zombie.hits_player(self.player.rect):
                zombie.stun()
                if self.player.take_hit(zombie.damage) and self.player.hp <= 0:
                    self.state = "game_over"
                    return

        for coin in list(self.coin_items):
            if not coin.update(dt):
                self.coin_items.remove(coin)
            elif coin.rect.colliderect(self.player.rect):
                self.coins += COIN_VALUE
                self.coin_items.remove(coin)

        if not self.zombies and self.state == "playing":
            self.clear_timer = LEVEL_CLEAR_DELAY
            self.state = "level_clear"

    def draw(self) -> None:
        pygame.mouse.set_visible(False)
        self.screen.fill(COLORS["background"])
        if self.state == "title":
            self._draw_title()
        elif self.state in ("playing", "paused", "game_over", "stats", "level_clear"):
            self._draw_level()
            if self.state == "paused":
                self._draw_paused()
            elif self.state == "game_over":
                self._draw_game_over()
            elif self.state == "stats":
                self._draw_stats()
            elif self.state == "level_clear":
                self._draw_level_clear()
        elif self.state == "shop":
            self.shop.draw(self.screen)
        pygame.display.flip()

    def _draw_level_clear(self) -> None:
        text = self.font_title.render("敌人已清除！", True, COLORS["ok"])
        self.screen.blit(text, ((WINDOW_WIDTH - text.get_width()) // 2, 260))
        hint = self.font_hint.render("快捡金币，即将进入商店…", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 340))

    def _draw_title(self) -> None:
        title = self.font_title.render("像素士兵 VS 僵尸", True, COLORS["title"])
        self.screen.blit(title, ((WINDOW_WIDTH - title.get_width()) // 2, 240))
        hint = self.font_hint.render("按任意键开始", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 330))

    def _draw_level(self) -> None:
        for wall in self.room.walls:
            pygame.draw.rect(self.screen, COLORS["wall"], wall)
        self.player.draw(self.screen)
        for zombie in self.zombies:
            zombie.draw(self.screen)
        for bullet in self.bullets:
            bullet.draw(self.screen)
        for coin in self.coin_items:
            coin.draw(self.screen)
        self._draw_hud()

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
            f"{self.player.hp}/{self.player.max_hp}", True, COLORS["hud"]
        )
        self.screen.blit(hp_text, (bar_x + bar_w + 16, bar_y - 4))
        level_text = self.font_hud.render(f"关卡 {self.level}", True, COLORS["hud"])
        self.screen.blit(
            level_text, (WINDOW_WIDTH - level_text.get_width() - 30, bar_y - 4)
        )

    def _draw_paused(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        text = self.font_title.render("已暂停", True, COLORS["hud"])
        self.screen.blit(text, ((WINDOW_WIDTH - text.get_width()) // 2, 280))
        hint = self.font_hint.render("按 ESC 继续", True, COLORS["info"])
        self.screen.blit(hint, ((WINDOW_WIDTH - hint.get_width()) // 2, 360))

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

    def run(self) -> None:
        warn_if_no_cjk_font()
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

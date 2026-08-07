import pygame

from .config import COLORS, SHOP_ITEMS, WINDOW_WIDTH
from .controls import event_key
from .fonts import load_font
from .resources import SPRITES

CARD_WIDTH = 680
CARD_HEIGHT = 72
CARD_GAP = 12
CARD_START_X = (WINDOW_WIDTH - CARD_WIDTH) // 2


class ShopScreen:
    def __init__(
        self,
        level: int,
        coins: int,
        player,
        bought_count: dict[str, int] | None = None,
    ) -> None:
        self.level = level
        self.coins = coins
        self.player = player
        self.selected = 0
        self.error_message = ""
        self.error_timer = 0.0
        self.items = SHOP_ITEMS
        self.bought_count = bought_count if bought_count is not None else {}
        for item in self.items:
            self.bought_count.setdefault(item["key"], 0)
        self.exit_label = "进入 Boss 房" if level == 3 else "进入下一关"
        self.done = False
        self.title_font = load_font(48, bold=True)
        self.item_font = load_font(26)
        self.small_font = load_font(20)
        self.coin_font = load_font(24, bold=True)

    def _item_price(self, item: dict) -> int:
        return item["price"] + item["raise"] * self.bought_count[item["key"]]

    def _item_capped(self, item: dict) -> bool:
        key = item["key"]
        if key == "attack":
            return self.player.attack >= item.get("max_value", 99)
        if key == "max_hp":
            return self.player.max_hp >= item.get("max_value", 99)
        if key == "fire_speed":
            return self.player.cooldown <= item.get("min_value", 0.1) + 1e-9
        if key == "move_speed":
            return self.player.speed >= item.get("max_value", 99)
        return False

    def _can_afford(self, item: dict) -> bool:
        return self.coins >= self._item_price(item)

    def _purchase(self, item: dict) -> None:
        if self._item_capped(item):
            self.error_message = "已达成长上限！"
            self.error_timer = 1.5
            return
        if not self._can_afford(item):
            self.error_message = "金币不足！"
            self.error_timer = 1.5
            return
        self.coins -= self._item_price(item)
        self.bought_count[item["key"]] += 1
        key = item["key"]
        if key == "attack":
            self.player.attack += 1
        elif key == "max_hp":
            self.player.max_hp += 1
            self.player.hp += 1
        elif key == "fire_speed":
            minimum = item.get("min_value", 0.1)
            self.player.cooldown = max(
                minimum,
                round(self.player.cooldown - 0.05, 2),
            )
        elif key == "move_speed":
            self.player.speed += 0.5
        elif key == "heal":
            self.player.heal(3)
        self.error_message = "购买成功！"
        self.error_timer = 1.0

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            key = event_key(event)
            if key == pygame.K_UP:
                self.selected = (self.selected - 1) % (len(self.items) + 1)
                self.error_message = ""
            elif key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % (len(self.items) + 1)
                self.error_message = ""
            elif key == pygame.K_f:
                if self.selected < len(self.items):
                    self._purchase(self.items[self.selected])
                else:
                    self.done = True
                    return "exit"
            elif key == pygame.K_ESCAPE:
                self.done = True
                return "exit"
        return None

    def update(self, dt: float) -> None:
        self.error_timer = max(0.0, self.error_timer - dt)

    def _draw_coin_icon(self, surface: pygame.Surface, center: tuple[int, int]) -> None:
        icon = SPRITES.load("ui/icon_coin.png", (24, 24))
        if icon is None:
            pygame.draw.circle(surface, COLORS["highlight"], center, 12)
        else:
            surface.blit(icon, icon.get_rect(center=center))

    def _draw_coins(self, surface: pygame.Surface) -> None:
        x = (WINDOW_WIDTH - CARD_WIDTH) // 2
        self._draw_coin_icon(surface, (x + 16, 140))
        coin_text = f"金币：{self.coins}"
        surf = self.item_font.render(coin_text, True, COLORS["highlight"])
        surface.blit(surf, (x + 38, 120))

    def _card_y(self, index: int) -> int:
        return 190 + index * (CARD_HEIGHT + CARD_GAP)

    def _draw_card(
        self,
        surface: pygame.Surface,
        index: int,
        label: str,
        price: int | None,
        desc: str,
        selected: bool,
        can_afford: bool,
        *,
        key: str | None = None,
        capped: bool = False,
    ) -> None:
        rect = pygame.Rect(CARD_START_X, self._card_y(index), CARD_WIDTH, CARD_HEIGHT)
        background = SPRITES.panel("ui/panel.png", rect.size, 16)
        if background is None:
            pygame.draw.rect(surface, (40, 42, 52), rect)
            pygame.draw.rect(surface, COLORS["info"], rect, 2)
        else:
            surface.blit(background, rect)
            if capped:
                border = COLORS["ok"]
            elif selected:
                border = COLORS["highlight"]
            elif not can_afford:
                border = COLORS["disabled"]
            else:
                border = COLORS["info"]
            pygame.draw.rect(surface, border, rect, 2)

        color = COLORS["highlight"] if selected else COLORS["hud"]
        if not can_afford and not selected:
            color = COLORS["disabled"]
        text_x = rect.x + 24
        icon_paths = {
            "attack": "ui/icon_attack.png",
            "max_hp": "ui/icon_health.png",
            "fire_speed": "ui/icon_fire_speed.png",
            "move_speed": "ui/icon_move_speed.png",
            "heal": "ui/icon_heal.png",
        }
        if key in icon_paths:
            icon = SPRITES.load(icon_paths[key], (40, 40))
            if icon is not None:
                surface.blit(icon, (rect.x + 16, rect.y + 16))
                text_x = rect.x + 68
        label_surf = self.item_font.render(label, True, color)
        surface.blit(label_surf, (text_x, rect.y + 8))
        desc_surf = self.small_font.render(desc, True, COLORS["info"])
        surface.blit(desc_surf, (text_x, rect.y + 40))

        if price is not None:
            coin_center = (rect.right - 92, rect.centery)
            self._draw_coin_icon(surface, coin_center)
            price_color = COLORS["hud"] if can_afford else COLORS["disabled"]
            price_surf = self.coin_font.render(str(price), True, price_color)
            surface.blit(price_surf, (coin_center[0] + 18, coin_center[1] - 16))

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS["background"])
        panel = SPRITES.panel("ui/panel.png", (780, 680), 16)
        if panel is not None:
            surface.blit(panel, ((surface.get_width() - 780) // 2, 20))
        title = f"第 {self.level} 关通过！商店"
        title_surf = self.title_font.render(title, True, COLORS["title"])
        surface.blit(title_surf, ((WINDOW_WIDTH - title_surf.get_width()) // 2, 50))
        self._draw_coins(surface)

        for i, item in enumerate(self.items):
            capped = self._item_capped(item)
            afford = self._can_afford(item)
            self._draw_card(
                surface,
                i,
                item["name"],
                None if capped else self._item_price(item),
                item["desc"] if not capped else "已达成长上限",
                selected=i == self.selected,
                can_afford=afford and not capped,
                key=item["key"],
                capped=capped,
            )

        self._draw_card(
            surface,
            len(self.items),
            self.exit_label,
            None,
            "确认后进入 Boss 房" if self.level == 3 else "确认后进入下一关",
            selected=self.selected == len(self.items),
            can_afford=True,
        )

        if self.error_timer > 0:
            color = COLORS["error"] if "不足" in self.error_message else COLORS["ok"]
            error_surf = self.item_font.render(self.error_message, True, color)
            surface.blit(
                error_surf,
                (
                    (WINDOW_WIDTH - error_surf.get_width()) // 2,
                    self._card_y(len(self.items)) + CARD_HEIGHT + 16,
                ),
            )

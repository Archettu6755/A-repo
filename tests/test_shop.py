import unittest
from unittest.mock import patch

import pygame

from game.config import PLAYER_ATTACK, PLAYER_FIRE_COOLDOWN, PLAYER_MAX_HP, PLAYER_SPEED
from game.entities import Player
from game.resources import SPRITES
from game.shop import ERROR_Y, ShopScreen


class ShopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def make_player(self) -> Player:
        return Player(
            pygame.Vector2(),
            PLAYER_MAX_HP,
            PLAYER_ATTACK,
            PLAYER_FIRE_COOLDOWN,
            PLAYER_SPEED,
        )

    def test_third_shop_enters_boss_room(self) -> None:
        shop = ShopScreen(3, 0, self.make_player(), {})
        self.assertEqual(shop.exit_label, "进入 Boss 房")

    def test_shop_has_no_healing_item(self) -> None:
        shop = ShopScreen(1, 0, self.make_player(), {})
        self.assertNotIn("heal", {item["key"] for item in shop.items})

    def test_purchase_counts_persist_between_shops(self) -> None:
        counts: dict[str, int] = {}
        player = self.make_player()
        first_shop = ShopScreen(1, 20, player, counts)
        first_shop._purchase(first_shop.items[0])
        second_shop = ShopScreen(2, 20, player, counts)
        self.assertEqual(second_shop._item_price(second_shop.items[0]), 4)

    def test_fire_speed_stops_at_declared_minimum(self) -> None:
        player = self.make_player()
        shop = ShopScreen(1, 100, player, {})
        item = next(item for item in shop.items if item["key"] == "fire_speed")
        while not shop._item_capped(item):
            shop._purchase(item)
        self.assertEqual(player.cooldown, item["min_value"])
        coins = shop.coins
        shop._purchase(item)
        self.assertEqual(shop.coins, coins)

    def test_shop_uses_art_for_each_card_state(self) -> None:
        shop = ShopScreen(1, 0, self.make_player(), {})
        surface = pygame.Surface((1280, 720))
        cases = (
            (False, True, False, "ui/shop_card_normal.png"),
            (True, True, False, "ui/shop_card_selected.png"),
            (False, False, False, "ui/shop_card_unavailable.png"),
            (True, False, False, "ui/shop_card_unavailable.png"),
            (False, True, True, "ui/shop_card_maxed.png"),
        )
        for selected, can_afford, capped, expected in cases:
            with (
                self.subTest(expected=expected),
                patch.object(SPRITES, "panel", wraps=SPRITES.panel) as panel,
            ):
                shop._draw_card(
                    surface,
                    0,
                    "测试",
                    1,
                    "说明",
                    selected,
                    can_afford,
                    capped=capped,
                )
                self.assertEqual(panel.call_args.args[0], expected)

    def test_error_message_fits_inside_window(self) -> None:
        shop = ShopScreen(1, 0, self.make_player(), {})
        self.assertLessEqual(ERROR_Y + shop.item_font.get_height(), 720)


if __name__ == "__main__":
    unittest.main()

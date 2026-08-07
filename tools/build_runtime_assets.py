from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def crop(surface: pygame.Surface, rect: tuple[int, int, int, int]) -> pygame.Surface:
    return surface.subsurface(pygame.Rect(rect)).copy()


def tight_crop(surface: pygame.Surface, *, largest_only: bool) -> pygame.Surface:
    mask = pygame.mask.from_surface(surface, 1)
    if largest_only:
        components = mask.connected_components(20)
        if not components:
            return surface.copy()
        rect = max(components, key=lambda item: item.count()).get_bounding_rects()[0]
    else:
        rects = mask.get_bounding_rects()
        if not rects:
            return surface.copy()
        rect = rects[0].copy()
        for item in rects[1:]:
            rect.union_ip(item)
    return surface.subsurface(rect).copy()


def fit(
    source: pygame.Surface,
    size: tuple[int, int],
    *,
    padding: int = 0,
    largest_only: bool = False,
) -> pygame.Surface:
    source = tight_crop(source, largest_only=largest_only)
    available_width = max(1, size[0] - padding * 2)
    available_height = max(1, size[1] - padding * 2)
    scale = min(
        available_width / source.get_width(), available_height / source.get_height()
    )
    scaled_size = (
        max(1, round(source.get_width() * scale)),
        max(1, round(source.get_height() * scale)),
    )
    scaled = pygame.transform.scale(source, scaled_size)
    result = pygame.Surface(size, pygame.SRCALPHA)
    result.blit(
        scaled,
        (
            (size[0] - scaled_size[0]) // 2,
            size[1] - scaled_size[1] - padding,
        ),
    )
    return result


def cover(source: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    scale = max(size[0] / source.get_width(), size[1] / source.get_height())
    scaled_size = (
        round(source.get_width() * scale),
        round(source.get_height() * scale),
    )
    scaled = pygame.transform.scale(source, scaled_size)
    left = (scaled.get_width() - size[0]) // 2
    top = (scaled.get_height() - size[1]) // 2
    return scaled.subsurface((left, top, *size)).copy()


def harden_alpha(source: pygame.Surface) -> pygame.Surface:
    result = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    for y in range(source.get_height()):
        for x in range(source.get_width()):
            red, green, blue, alpha = source.get_at((x, y))
            if alpha >= 128:
                result.set_at((x, y), (red, green, blue, 255))
    return result


def save(surface: pygame.Surface, relative_path: str) -> None:
    path = ASSETS / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, path)


def build_characters() -> None:
    master = pygame.image.load(ASSETS / "characters/character_turnarounds_v1.png")
    directions = ("down", "left", "right", "up")
    rows = (
        ("player", (32, 48), ("idle", "walk", "shoot", "hurt")),
        ("zombie_normal", (32, 48), ("idle", "charge", "stun")),
        ("zombie_fast", (32, 40), ("idle", "charge", "leap", "stun")),
        (
            "zombie_heavy",
            (48, 56),
            ("idle", "charge_prepare", "charge", "stun"),
        ),
    )
    cell_width = master.get_width() // 4
    cell_height = master.get_height() // 4
    for row_index, (character, size, actions) in enumerate(rows):
        for column, direction in enumerate(directions):
            cell = crop(
                master,
                (
                    column * cell_width,
                    row_index * cell_height,
                    cell_width,
                    cell_height,
                ),
            )
            sprite = fit(cell, size, padding=1, largest_only=True)
            for action in actions:
                save(
                    sprite,
                    f"characters/{character}/{character}_{action}_{direction}.png",
                )


def build_environment() -> None:
    master = pygame.image.load(ASSETS / "environment/environment_props_master_v1.png")
    floor_specs = (
        ((96, 64, 78, 64), "environment/shared/floor_01.png"),
        ((362, 64, 78, 64), "environment/shared/floor_02.png"),
        ((648, 64, 80, 64), "environment/shared/floor_03.png"),
        ((930, 64, 80, 64), "environment/shared/floor_04.png"),
    )
    for source_rect, relative_path in floor_specs:
        save(pygame.transform.scale(crop(master, source_rect), (32, 32)), relative_path)

    specs = (
        ((60, 270, 220, 195), (64, 48), "environment/shared/wall.png"),
        ((915, 270, 285, 200), (64, 48), "environment/shared/wall_broken.png"),
        ((275, 465, 205, 220), (64, 64), "environment/shared/door_closed.png"),
        ((500, 465, 225, 235), (64, 64), "environment/shared/door_open.png"),
        ((1010, 450, 125, 260), (32, 64), "environment/shared/pillar.png"),
        ((50, 680, 145, 165), (32, 40), "props/crate_intact.png"),
        ((215, 680, 145, 165), (32, 40), "props/crate_damage_01.png"),
        ((370, 690, 150, 150), (32, 40), "props/crate_damage_02.png"),
        ((520, 700, 180, 135), (32, 32), "props/crate_broken.png"),
        ((710, 700, 175, 135), (64, 48), "environment/shared/low_wall.png"),
        ((250, 850, 225, 175), (96, 64), "environment/shared/pit.png"),
        ((50, 850, 100, 160), (24, 36), "props/switch_off.png"),
        ((150, 850, 100, 160), (24, 36), "props/switch_on.png"),
        ((55, 1010, 125, 120), (16, 16), "props/coin.png"),
        ((225, 1010, 115, 120), (8, 8), "props/bullet.png"),
        ((350, 1015, 250, 105), (24, 10), "props/shadow_small.png"),
        ((60, 1110, 170, 125), (32, 32), "effects/blood_01.png"),
    )
    for source_rect, size, relative_path in specs:
        save(fit(crop(master, source_rect), size), relative_path)


def build_ui() -> None:
    master = pygame.image.load(ASSETS / "ui/ui_master_v1.png")
    specs = (
        ((755, 40, 390, 325), (192, 144), "ui/panel.png"),
        ((90, 350, 635, 90), (256, 32), "ui/hp_frame.png"),
        ((100, 580, 150, 160), (32, 32), "ui/icon_attack.png"),
        ((285, 580, 150, 160), (32, 32), "ui/icon_health.png"),
        ((470, 580, 155, 160), (32, 32), "ui/icon_fire_speed.png"),
        ((650, 580, 160, 160), (32, 32), "ui/icon_move_speed.png"),
        ((830, 580, 155, 160), (32, 32), "ui/icon_heal.png"),
        ((760, 400, 130, 170), (24, 24), "ui/icon_coin.png"),
    )
    for source_rect, size, relative_path in specs:
        save(fit(crop(master, source_rect), size), relative_path)

    heart_master = pygame.image.load(ASSETS / "ui/heart_icons_master_v1.png")
    heart_mask = pygame.mask.from_surface(heart_master, 64)
    components = heart_mask.connected_components(1000)
    heart_rects: list[pygame.Rect] = []
    for component in components:
        rects = component.get_bounding_rects()
        if not rects:
            continue
        bounds = rects[0].copy()
        for rect in rects[1:]:
            bounds.union_ip(rect)
        heart_rects.append(bounds)
    heart_rects.sort(key=lambda rect: rect.x)
    if len(heart_rects) != 2:
        raise RuntimeError("红心母版必须恰好包含两个独立图标")
    for bounds, name in zip(
        heart_rects,
        ("heart_full", "heart_empty"),
        strict=True,
    ):
        heart = fit(crop(heart_master, bounds), (24, 24), padding=1)
        save(harden_alpha(heart), f"ui/{name}.png")

    concept = pygame.image.load(ASSETS / "concepts/art_direction_board_v1.png")
    room_scene = crop(concept, (0, 0, 996, 1024))
    save(cover(room_scene, (1280, 720)), "ui/title_background.png")


def main() -> None:
    pygame.init()
    build_characters()
    build_environment()
    build_ui()
    print("运行时美术资源已生成")


if __name__ == "__main__":
    main()

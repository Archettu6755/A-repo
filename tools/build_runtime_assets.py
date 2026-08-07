from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def crop(surface: pygame.Surface, rect: tuple[int, int, int, int]) -> pygame.Surface:
    return surface.subsurface(pygame.Rect(rect)).copy()


def grid_crop(
    surface: pygame.Surface,
    columns: int,
    rows: int,
    column: int,
    row: int,
) -> pygame.Surface:
    left = round(column * surface.get_width() / columns)
    right = round((column + 1) * surface.get_width() / columns)
    top = round(row * surface.get_height() / rows)
    bottom = round((row + 1) * surface.get_height() / rows)
    return crop(surface, (left, top, right - left, bottom - top))


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


def drop_tiny_components(
    source: pygame.Surface, minimum_pixels: int = 3
) -> pygame.Surface:
    result = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    for component in pygame.mask.from_surface(source, 1).connected_components():
        if component.count() < minimum_pixels:
            continue
        for rect in component.get_bounding_rects():
            result.blit(source, rect, rect)
    return result


def save(surface: pygame.Surface, relative_path: str) -> None:
    path = ASSETS / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, path)


def shifted(source: pygame.Surface, x: int = 0, y: int = 0) -> pygame.Surface:
    result = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    result.blit(source, (x, y))
    return result


def white_flash(source: pygame.Surface) -> pygame.Surface:
    result = source.copy()
    result.fill((96, 96, 96, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return result


def save_strip(frames: list[pygame.Surface], relative_path: str) -> None:
    frame_width, frame_height = frames[0].get_size()
    strip = pygame.Surface((frame_width * len(frames), frame_height), pygame.SRCALPHA)
    for index, frame in enumerate(frames):
        strip.blit(frame, (index * frame_width, 0))
    save(strip, relative_path)


def load(relative_path: str) -> pygame.Surface:
    return pygame.image.load(ASSETS / relative_path)


def build_characters() -> None:
    master = pygame.image.load(ASSETS / "characters/character_turnarounds_v1.png")
    directions = ("down", "left", "right", "up")
    rows = (
        ("player", (32, 48)),
        ("zombie_normal", (32, 48)),
        ("zombie_fast", (32, 40)),
        ("zombie_heavy", (48, 56)),
    )
    cell_width = master.get_width() // 4
    cell_height = master.get_height() // 4
    for row_index, (character, size) in enumerate(rows):
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
            save(sprite, f"characters/{character}/{character}_idle_{direction}.png")

    actions = pygame.image.load(ASSETS / "characters/character_actions_master_v1.png")
    action_specs = (
        (0, "player", (32, 48), "walk", "shoot"),
        (1, "zombie_normal", (32, 48), "walk", "charge"),
        (2, "zombie_fast", (32, 40), "run", "leap"),
        (3, "zombie_heavy", (48, 56), "charge_prepare", "charge"),
    )
    for row, character, size, first_action, second_action in action_specs:
        for column, direction in enumerate(directions):
            for action, offset in ((first_action, 0), (second_action, 4)):
                sprite = fit(
                    grid_crop(actions, 8, 4, column + offset, row),
                    size,
                    padding=1,
                    largest_only=True,
                )
                save(
                    sprite,
                    f"characters/{character}/{character}_{action}_{direction}.png",
                )

    hurt_death = pygame.image.load(
        ASSETS / "characters/character_hurt_death_master_v1.png"
    )
    for row, (character, size) in enumerate(rows):
        stun_action = "hurt" if character == "player" else "stun"
        for column, direction in enumerate(directions):
            sprite = fit(
                grid_crop(hurt_death, 8, 4, column, row),
                size,
                padding=1,
                largest_only=True,
            )
            save(
                sprite,
                f"characters/{character}/{character}_{stun_action}_{direction}.png",
            )
            if character != "player":
                save(
                    sprite,
                    f"characters/{character}/{character}_hurt_{direction}.png",
                )
        for frame in range(4):
            sprite = fit(
                grid_crop(hurt_death, 8, 4, frame + 4, row),
                size,
                padding=1,
                largest_only=True,
            )
            save(sprite, f"characters/{character}/{character}_death_{frame}.png")

    for direction in directions:
        fast_run = load(f"characters/zombie_fast/zombie_fast_run_{direction}.png")
        save(fast_run, f"characters/zombie_fast/zombie_fast_charge_{direction}.png")
        heavy_idle = load(f"characters/zombie_heavy/zombie_heavy_idle_{direction}.png")
        save(heavy_idle, f"characters/zombie_heavy/zombie_heavy_walk_{direction}.png")

    build_boss()
    build_character_sheets()


def build_character_sheets() -> None:
    directions = ("down", "left", "right", "up")
    recoil = {"down": (0, -1), "left": (1, 0), "right": (-1, 0), "up": (0, 1)}
    characters = {
        "player": ("walk", "shoot"),
        "zombie_normal": ("walk", "charge"),
        "zombie_fast": ("run", "leap"),
        "zombie_heavy": ("walk", "charge"),
    }
    for character, (move_action, attack_action) in characters.items():
        directory = f"characters/{character}"
        for direction in directions:
            idle = load(f"{directory}/{character}_idle_{direction}.png")
            move = load(f"{directory}/{character}_{move_action}_{direction}.png")
            attack = load(f"{directory}/{character}_{attack_action}_{direction}.png")
            save_strip(
                [idle, shifted(idle, y=-1)],
                f"{directory}/{character}_idle_{direction}_sheet.png",
            )
            save_strip(
                [idle, move, shifted(idle, y=-1), shifted(move, y=-1)],
                f"{directory}/{character}_{move_action}_{direction}_sheet.png",
            )
            save_strip(
                [move, attack, shifted(attack, *recoil[direction])],
                f"{directory}/{character}_{attack_action}_{direction}_sheet.png",
            )
            reaction = "hurt" if character == "player" else "stun"
            hurt = load(f"{directory}/{character}_{reaction}_{direction}.png")
            save_strip(
                [hurt, white_flash(hurt)],
                f"{directory}/{character}_{reaction}_{direction}_sheet.png",
            )
            if character != "player":
                save_strip(
                    [hurt, white_flash(hurt)],
                    f"{directory}/{character}_hurt_{direction}_sheet.png",
                )

        death = [
            load(f"{directory}/{character}_death_{frame}.png") for frame in range(4)
        ]
        save_strip(
            [death[0], death[1], death[2], death[2], death[3], death[3]],
            f"{directory}/{character}_death_sheet.png",
        )

    for direction in directions:
        fast_run = load(f"characters/zombie_fast/zombie_fast_run_{direction}_sheet.png")
        save(
            fast_run,
            f"characters/zombie_fast/zombie_fast_charge_{direction}_sheet.png",
        )
        heavy_idle = load(f"characters/zombie_heavy/zombie_heavy_idle_{direction}.png")
        heavy_prepare = load(
            f"characters/zombie_heavy/zombie_heavy_charge_prepare_{direction}.png"
        )
        save_strip(
            [heavy_idle, heavy_prepare],
            "characters/zombie_heavy/"
            f"zombie_heavy_charge_prepare_{direction}_sheet.png",
        )


def build_boss() -> None:
    directions = ("down", "left", "right", "up")
    size = (80, 88)
    master = pygame.image.load(ASSETS / "characters/boss/boss_character_master_v1.png")
    for row, (phase, action) in enumerate(
        ((1, "idle"), (1, "charge"), (2, "idle"), (2, "charge"))
    ):
        for column, direction in enumerate(directions):
            sprite = fit(
                grid_crop(master, 4, 4, column, row),
                size,
                padding=2,
                largest_only=True,
            )
            save(
                sprite,
                f"characters/boss/boss_phase{phase}_{action}_{direction}.png",
            )

    actions = pygame.image.load(ASSETS / "characters/boss/boss_actions_master_v1.png")
    for phase, offset in ((1, 0), (2, 4)):
        for column, direction in enumerate(directions):
            sprite = fit(
                grid_crop(actions, 8, 2, column + offset, 0),
                size,
                padding=2,
                largest_only=False,
            )
            save(
                sprite,
                f"characters/boss/boss_phase{phase}_stun_{direction}.png",
            )
    for frame in range(8):
        sprite = fit(
            grid_crop(actions, 8, 2, frame, 1),
            size,
            padding=2,
            largest_only=False,
        )
        save(sprite, f"characters/boss/boss_death_{frame}.png")

    for phase in (1, 2):
        for direction in directions:
            idle = load(f"characters/boss/boss_phase{phase}_idle_{direction}.png")
            charge = load(f"characters/boss/boss_phase{phase}_charge_{direction}.png")
            stun = load(f"characters/boss/boss_phase{phase}_stun_{direction}.png")
            save_strip(
                [idle, shifted(idle, y=-1)],
                f"characters/boss/boss_phase{phase}_idle_{direction}_sheet.png",
            )
            save_strip(
                [idle, charge, shifted(charge, *recoil_offset(direction))],
                f"characters/boss/boss_phase{phase}_charge_{direction}_sheet.png",
            )
            save_strip(
                [stun, white_flash(stun)],
                f"characters/boss/boss_phase{phase}_stun_{direction}_sheet.png",
            )
    save_strip(
        [load(f"characters/boss/boss_death_{frame}.png") for frame in range(8)],
        "characters/boss/boss_death_sheet.png",
    )


def recoil_offset(direction: str) -> tuple[int, int]:
    return {"down": (0, -1), "left": (1, 0), "right": (-1, 0), "up": (0, 1)}[direction]


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
        (
            (300, 270, 220, 195),
            (64, 64),
            "environment/shared/wall_inner_corner.png",
        ),
        (
            (545, 270, 220, 195),
            (64, 64),
            "environment/shared/wall_outer_corner.png",
        ),
        ((785, 270, 110, 195), (32, 48), "environment/shared/wall_end.png"),
        ((915, 270, 285, 200), (64, 48), "environment/shared/wall_broken.png"),
        ((60, 465, 195, 220), (64, 64), "environment/shared/door_frame.png"),
        ((275, 465, 205, 220), (64, 64), "environment/shared/door_closed.png"),
        ((500, 465, 225, 235), (64, 64), "environment/shared/door_opening.png"),
        ((735, 465, 205, 220), (64, 64), "environment/shared/door_open.png"),
        ((1010, 450, 125, 260), (32, 64), "environment/shared/pillar.png"),
        ((50, 680, 145, 165), (32, 40), "props/crate_intact.png"),
        ((215, 680, 145, 165), (32, 40), "props/crate_damage_01.png"),
        ((370, 690, 150, 150), (32, 40), "props/crate_damage_02.png"),
        ((520, 700, 180, 135), (32, 32), "props/crate_broken.png"),
        ((710, 700, 175, 135), (64, 48), "environment/shared/low_wall.png"),
        (
            (885, 700, 145, 135),
            (32, 48),
            "environment/shared/low_wall_end.png",
        ),
        (
            (1025, 690, 175, 150),
            (64, 48),
            "environment/shared/low_wall_broken.png",
        ),
        ((250, 850, 225, 175), (96, 64), "environment/shared/pit.png"),
        (
            (475, 850, 120, 175),
            (32, 64),
            "environment/shared/pit_vertical.png",
        ),
        (
            (550, 875, 180, 120),
            (96, 32),
            "environment/shared/pit_horizontal.png",
        ),
        ((790, 850, 195, 175), (96, 64), "environment/shared/water_large.png"),
        (
            (985, 850, 100, 175),
            (32, 64),
            "environment/shared/water_vertical.png",
        ),
        (
            (1095, 850, 130, 175),
            (64, 64),
            "environment/shared/water_corner.png",
        ),
        ((50, 850, 100, 160), (24, 36), "props/switch_off.png"),
        ((150, 850, 100, 160), (24, 36), "props/switch_on.png"),
        ((55, 1010, 125, 120), (16, 16), "props/coin.png"),
        ((225, 1010, 115, 120), (8, 8), "props/bullet.png"),
        ((350, 1015, 250, 105), (24, 10), "props/shadow_small.png"),
    )
    for source_rect, size, relative_path in specs:
        save(fit(crop(master, source_rect), size), relative_path)

    pillar = load("environment/shared/pillar.png")
    pillar_variant = pillar.copy()
    pillar_variant.fill((205, 220, 232, 255), special_flags=pygame.BLEND_RGBA_MULT)
    save(pillar_variant, "environment/shared/pillar_variant_02.png")

    shadow = load("props/shadow_small.png")
    save(pygame.transform.scale(shadow, (36, 14)), "props/shadow_large.png")

    coin = load("props/coin.png")
    coin_frames: list[pygame.Surface] = []
    for width in (16, 11, 5, 11):
        frame = pygame.Surface((16, 16), pygame.SRCALPHA)
        scaled = pygame.transform.scale(coin, (width, 16))
        frame.blit(scaled, ((16 - width) // 2, 0))
        coin_frames.append(frame)
    for index, frame in enumerate(coin_frames):
        save(frame, f"props/coin_{index}.png")
    save_strip(coin_frames, "props/coin_sheet.png")

    bullet = load("props/bullet.png")
    save(bullet, "props/bullet_0.png")
    save(white_flash(bullet), "props/bullet_1.png")
    save_strip([bullet, white_flash(bullet)], "props/bullet_sheet.png")

    decals = pygame.image.load(ASSETS / "environment/environment_decals_master_v1.png")
    for column in range(6):
        marking = drop_tiny_components(grid_crop(decals, 6, 3, column, 0))
        save(
            harden_alpha(fit(marking, (32, 32), padding=1)),
            f"environment/checkpoint/marking_{column + 1:02d}.png",
        )
    for column in range(4):
        crack = drop_tiny_components(grid_crop(decals, 6, 3, column, 1))
        stain = drop_tiny_components(grid_crop(decals, 6, 3, column, 2))
        crack_runtime = harden_alpha(fit(crack, (32, 32), padding=1))
        stain_runtime = harden_alpha(fit(stain, (32, 32), padding=1))
        if column == 2:
            stain_runtime.fill((72, 30, 88, 0), special_flags=pygame.BLEND_RGBA_ADD)
        save(
            crack_runtime,
            f"environment/laboratory/crack_{column + 1:02d}.png",
        )
        save(
            stain_runtime,
            f"environment/laboratory/stain_{column + 1:02d}.png",
        )

    for source, destination in (
        (
            "environment/shared/floor_01.png",
            "environment/checkpoint/floor_clean_01.png",
        ),
        (
            "environment/shared/floor_02.png",
            "environment/checkpoint/floor_clean_02.png",
        ),
        (
            "environment/shared/floor_03.png",
            "environment/laboratory/floor_damaged_01.png",
        ),
        (
            "environment/shared/floor_04.png",
            "environment/laboratory/floor_damaged_02.png",
        ),
    ):
        save(load(source), destination)


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

    icon_names = (
        "icon_attack",
        "icon_health",
        "icon_fire_speed",
        "icon_move_speed",
        "icon_heal",
        "icon_coin",
    )
    for name in icon_names:
        icon = load(f"ui/{name}.png")
        save(pygame.transform.scale(icon, (16, 16)), f"ui/{name}_16.png")
        save(pygame.transform.scale(icon, (32, 32)), f"ui/{name}_32.png")

    card_specs = (
        ((90, 750, 195, 240), "ui/shop_card_normal.png"),
        ((290, 750, 215, 240), "ui/shop_card_selected.png"),
        ((540, 750, 200, 240), "ui/shop_card_unavailable.png"),
        ((760, 750, 205, 240), "ui/shop_card_maxed.png"),
    )
    for source_rect, relative_path in card_specs:
        save(fit(crop(master, source_rect), (160, 208)), relative_path)

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


def build_effects() -> None:
    master = pygame.image.load(ASSETS / "effects/combat_effects_master_v1.png")
    directions = ("down", "left", "right", "up")
    for row, direction in enumerate(directions):
        for frame in range(4):
            sprite = fit(
                grid_crop(master, 4, 8, frame, row),
                (16, 16),
                largest_only=False,
            )
            save(sprite, f"effects/fx_muzzle_{direction}_{frame}.png")

    effect_specs = (
        (4, "fx_bullet_impact", (16, 16)),
        (5, "fx_charge_warning", (32, 32)),
        (6, "fx_wall_dust", (24, 24)),
        (7, "fx_coin_pop", (24, 24)),
    )
    for row, name, size in effect_specs:
        for frame in range(4):
            sprite = fit(
                grid_crop(master, 4, 8, frame, row),
                size,
                largest_only=False,
            )
            save(sprite, f"effects/{name}_{frame}.png")

    secondary = pygame.image.load(ASSETS / "effects/secondary_effects_master_v1.png")
    for frame in range(5):
        sprite = fit(
            grid_crop(secondary, 5, 2, frame, 0),
            (32, 32),
            largest_only=False,
        )
        save(sprite, f"effects/fx_crate_debris_{frame}.png")
    for frame in range(4):
        sprite = fit(
            grid_crop(secondary, 5, 2, frame, 1),
            (32, 48),
            largest_only=False,
        )
        save(sprite, f"effects/fx_player_hurt_{frame}.png")

    environment = pygame.image.load(
        ASSETS / "environment/environment_props_master_v1.png"
    )
    blood_rects = (
        (60, 1110, 170, 125),
        (245, 1110, 155, 125),
        (405, 1110, 120, 125),
        (525, 1110, 130, 125),
        (650, 1110, 130, 125),
    )
    blood = [fit(crop(environment, rect), (32, 32)) for rect in blood_rects]
    blood.extend(
        (
            pygame.transform.flip(blood[0], True, False),
            pygame.transform.flip(blood[1], False, True),
            pygame.transform.rotate(blood[2], 180),
        )
    )
    for index, sprite in enumerate(blood, start=1):
        save(sprite, f"effects/blood_{index:02d}.png")


def main() -> None:
    pygame.init()
    build_characters()
    build_environment()
    build_ui()
    build_effects()
    print("运行时美术资源已生成")


if __name__ == "__main__":
    main()

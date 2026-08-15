from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from importlib.metadata import version as package_version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = ROOT / "build"
STAGE_ROOT = BUILD_ROOT / "pygbag-app"
WEB_ROOT = BUILD_ROOT / "web"
RUNTIME_EXTENSIONS = {".ogg", ".png", ".ttf"}
PYGBAG_VERSION = "0.9.2"
ENVIRONMENT_SHARED = {
    "door_closed.png",
    "door_open.png",
    "door_opening.png",
    "low_wall.png",
    "low_wall_broken.png",
    "low_wall_end.png",
    "pillar.png",
    "pillar_variant_02.png",
    "pit.png",
    "pit_vertical.png",
    "wall.png",
    "wall_broken.png",
    "wall_end.png",
    "water_large.png",
    "water_vertical.png",
}
PROPS = {
    "bullet.png",
    "bullet_sheet.png",
    "coin.png",
    "coin_sheet.png",
    "crate_broken.png",
    "crate_damage_01.png",
    "crate_damage_02.png",
    "crate_intact.png",
    "shadow_large.png",
    "shadow_small.png",
    "switch_off.png",
    "switch_on.png",
}
UI = {
    "heart_empty.png",
    "heart_full.png",
    "icon_attack.png",
    "icon_coin.png",
    "icon_fire_speed.png",
    "icon_health.png",
    "icon_move_speed.png",
    "panel.png",
    "shop_card_maxed.png",
    "shop_card_normal.png",
    "shop_card_selected.png",
    "shop_card_unavailable.png",
    "title_background.png",
}
PLAYER_ACTIONS = {"hurt", "idle", "shoot", "walk"}
ZOMBIE_ACTIONS = {
    "fast": {"charge", "hurt", "idle", "leap", "run", "stun"},
    "heavy": {"charge", "charge_prepare", "hurt", "idle", "stun", "walk"},
    "normal": {"charge", "hurt", "idle", "stun", "walk"},
}
DIRECTIONS = {"down", "left", "right", "up"}


def _is_runtime_character(relative: Path) -> bool:
    if len(relative.parts) != 3:
        return False
    _, character, filename = relative.parts
    if character == "player":
        if filename in {"player_death_3.png", "player_death_sheet.png"}:
            return True
        return any(
            filename == f"player_{action}_{direction}.png"
            for action in PLAYER_ACTIONS
            for direction in DIRECTIONS
        )
    if character == "boss":
        return filename == "boss_death_7.png" or filename.endswith("_sheet.png")
    if not character.startswith("zombie_"):
        return False
    kind = character.removeprefix("zombie_")
    return any(
        filename == f"zombie_{kind}_{action}_{direction}_sheet.png"
        for action in ZOMBIE_ACTIONS.get(kind, set())
        for direction in DIRECTIONS
    )


def _is_runtime_asset(relative: Path) -> bool:
    if not relative.parts:
        return False
    category = relative.parts[0]
    if category == "characters":
        return _is_runtime_character(relative)
    if category == "effects":
        return relative.suffix.casefold() == ".png" and "master" not in relative.name
    if category == "environment" and len(relative.parts) == 3:
        theme = relative.parts[1]
        return theme in {"checkpoint", "laboratory"} or (
            theme == "shared" and relative.name in ENVIRONMENT_SHARED
        )
    if category == "fonts":
        return relative.suffix.casefold() == ".ttf"
    if category == "props":
        return relative.name in PROPS
    if category == "ui":
        return relative.name in UI
    if category == "audio":
        return relative.suffix.casefold() == ".ogg"
    return False


def runtime_asset_paths(asset_root: Path) -> list[Path]:
    result = []
    for path in asset_root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in RUNTIME_EXTENSIONS:
            continue
        relative = path.relative_to(asset_root)
        if _is_runtime_asset(relative):
            result.append(relative)
    return sorted(result)


def _reset_directory(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def prepare_web_app(root: Path = ROOT, stage: Path = STAGE_ROOT) -> list[Path]:
    stage.mkdir(parents=True, exist_ok=True)
    for child in (stage / "game", stage / "static"):
        _reset_directory(child)

    shutil.copy2(root / "web" / "main.py", stage / "main.py")
    for path in sorted((root / "src" / "game").glob("*.py")):
        shutil.copy2(path, stage / "game" / path.name)

    copied_assets = runtime_asset_paths(root / "assets")
    for relative in copied_assets:
        target = stage / "game" / "assets" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "assets" / relative, target)

    for path in sorted((root / "web" / "static").iterdir()):
        if path.is_file():
            shutil.copy2(path, stage / "static" / path.name)
    shutil.copy2(root / "assets" / "ui" / "icon_attack_32.png", stage / "favicon.png")
    return copied_assets


def inject_web_controls(index_path: Path, controls_path: Path) -> None:
    html = index_path.read_text(encoding="utf-8")
    controls = controls_path.read_text(encoding="utf-8").strip()
    head = '  <link rel="stylesheet" href="web_controls.css">\n</head>'
    body = f"{controls}\n  <script src=\"web_controls.js\"></script>\n</body>"
    if "</head>" not in html or "</body>" not in html:
        raise RuntimeError("pygbag 模板缺少 head 或 body 结束标签")
    html = html.replace("</head>", head, 1)
    html = html.replace("</body>", body, 1)
    index_path.write_text(html, encoding="utf-8")


def verify_web_build(web_root: Path = WEB_ROOT) -> None:
    required_files = {
        "favicon.png",
        "index.html",
        "web_controls.css",
        "web_controls.js",
    }
    names = {path.name for path in web_root.iterdir() if path.is_file()}
    missing = required_files - names
    if missing:
        raise RuntimeError(f"网页构建缺少文件: {', '.join(sorted(missing))}")

    archives = sorted(web_root.glob("*.apk"))
    if len(archives) != 1:
        raise RuntimeError("网页构建必须且只能包含一个 pygbag 应用包")
    with zipfile.ZipFile(archives[0]) as archive:
        archived = set(archive.namelist())
    required_archive_files = {
        "assets/main.py",
        "assets/game/game.py",
        "assets/game/web.py",
        "assets/game/assets/fonts/fusion_pixel_12px_zh_hans.ttf",
        "assets/game/assets/ui/title_background.png",
        "assets/game/assets/characters/boss/boss_phase1_idle_down_sheet.png",
    }
    missing_archive = required_archive_files - archived
    if missing_archive:
        raise RuntimeError(
            f"网页应用包缺少运行时文件: {', '.join(sorted(missing_archive))}"
        )
    forbidden = [
        name
        for name in archived
        if "/concepts/" in name
        or "master" in Path(name).name.casefold()
        or "turnarounds" in Path(name).name.casefold()
    ]
    if forbidden:
        raise RuntimeError(f"网页应用包包含母版资源: {forbidden[0]}")

    html = (web_root / "index.html").read_text(encoding="utf-8")
    for marker in (
        "https://pygame-web.github.io/archives/0.9/",
        'href="web_controls.css"',
        'id="game-touch-controls"',
        'src="web_controls.js"',
    ):
        if marker not in html:
            raise RuntimeError(f"网页入口缺少触屏层标记: {marker}")


def build_web(root: Path = ROOT) -> Path:
    installed_version = package_version("pygbag")
    if installed_version != PYGBAG_VERSION:
        raise RuntimeError(
            f"网页构建需要 pygbag {PYGBAG_VERSION}，当前为 {installed_version}"
        )
    prepare_web_app(root, STAGE_ROOT)
    command = [
        sys.executable,
        "-m",
        "pygbag",
        "--build",
        "--width",
        "1280",
        "--height",
        "720",
        "--PYBUILD",
        "3.12",
        "--ume_block",
        "0",
        "--title",
        "像素士兵 VS 僵尸",
        "--package",
        "io.github.archettu6755.a-repo",
        "--icon",
        str(STAGE_ROOT / "favicon.png"),
        str(STAGE_ROOT),
    ]
    subprocess.run(command, cwd=root, check=True)

    generated = STAGE_ROOT / "build" / "web"
    if not generated.is_dir():
        raise RuntimeError("pygbag 未生成 build/web")
    _reset_directory(WEB_ROOT)
    shutil.copytree(generated, WEB_ROOT, dirs_exist_ok=True)
    inject_web_controls(WEB_ROOT / "index.html", root / "web" / "controls.html")
    verify_web_build(WEB_ROOT)
    return WEB_ROOT


if __name__ == "__main__":
    output = build_web()
    print(f"网页版本已生成: {output}")

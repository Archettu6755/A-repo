import os
import sys

import pygame

CANDIDATE_PATHS = (
    "/mnt/c/Windows/Fonts/msyh.ttc",
    "/mnt/c/Windows/Fonts/msyhbd.ttc",
    "/mnt/c/Windows/Fonts/simhei.ttf",
    "/mnt/c/Windows/Fonts/Deng.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
)

WINDOWS_FONT_FILES = (
    "msyh.ttc",
    "msyhbd.ttc",
    "simhei.ttf",
    "Deng.ttf",
    "simsun.ttc",
)

CANDIDATE_NAMES = [
    "microsoftyahei",
    "msyh",
    "simhei",
    "notosanscjksc",
    "wqymicrohei",
    "dengxian",
    "simsun",
]


def candidate_paths():
    windows_dir = os.environ.get("WINDIR")
    if windows_dir:
        for filename in WINDOWS_FONT_FILES:
            yield os.path.join(windows_dir, "Fonts", filename)
    yield from CANDIDATE_PATHS


def find_cjk_font_path() -> str | None:
    for path in candidate_paths():
        if os.path.isfile(path):
            return path
    for name in CANDIDATE_NAMES:
        try:
            match = pygame.font.match_font(name)
        except (OSError, TypeError, pygame.error):
            return None
        if match:
            return match
    return None


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    path = find_cjk_font_path()
    if path:
        try:
            return pygame.font.Font(path, size)
        except (FileNotFoundError, pygame.error):
            pass
    try:
        return pygame.font.SysFont(None, size, bold=bold)
    except (OSError, TypeError, pygame.error):
        return pygame.font.Font(None, size)


def warn_if_no_cjk_font() -> None:
    if find_cjk_font_path() is None:
        print("警告：未找到中文字体，界面中文可能无法正常显示", file=sys.stderr)

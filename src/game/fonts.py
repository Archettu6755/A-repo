import os
import sys

import pygame

CANDIDATE_PATHS = [
    "/mnt/c/Windows/Fonts/msyh.ttc",
    "/mnt/c/Windows/Fonts/msyhbd.ttc",
    "/mnt/c/Windows/Fonts/simhei.ttf",
    "/mnt/c/Windows/Fonts/Deng.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]

CANDIDATE_NAMES = [
    "microsoftyahei",
    "msyh",
    "simhei",
    "notosanscjksc",
    "wqymicrohei",
    "dengxian",
    "simsun",
]


def find_cjk_font_path() -> str | None:
    for path in CANDIDATE_PATHS:
        if os.path.isfile(path):
            return path
    for name in CANDIDATE_NAMES:
        match = pygame.font.match_font(name)
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
    except pygame.error:
        return pygame.font.Font(None, size)


def warn_if_no_cjk_font() -> None:
    if find_cjk_font_path() is None:
        print("警告：未找到中文字体，界面中文可能无法正常显示", file=sys.stderr)

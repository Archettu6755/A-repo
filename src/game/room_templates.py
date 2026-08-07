from dataclasses import dataclass

from .config import ROOM_GRID_HEIGHT, ROOM_GRID_WIDTH

CellRect = tuple[int, int, int, int, str]
Cell = tuple[int, int]


@dataclass(frozen=True)
class RoomTemplate:
    template_id: str
    name: str
    difficulty: int
    tags: tuple[str, ...]
    solids: tuple[CellRect, ...]


ROOM_TEMPLATES = (
    RoomTemplate(
        "O01",
        "四角柱",
        1,
        ("open",),
        (
            (6, 4, 1, 1, "pillar"),
            (25, 4, 1, 1, "pillar"),
            (6, 13, 1, 1, "pillar"),
            (25, 13, 1, 1, "pillar"),
        ),
    ),
    RoomTemplate(
        "O02",
        "两侧矮墙",
        1,
        ("open", "cover"),
        ((6, 6, 1, 4, "wall"), (25, 8, 1, 4, "wall")),
    ),
    RoomTemplate(
        "O03",
        "中央双掩体",
        1,
        ("open",),
        ((13, 5, 2, 1, "wall"), (18, 12, 2, 1, "wall")),
    ),
    RoomTemplate(
        "S01",
        "镜像柱阵",
        2,
        ("symmetric", "cover"),
        (
            (9, 5, 1, 1, "pillar"),
            (22, 5, 1, 1, "pillar"),
            (9, 12, 1, 1, "pillar"),
            (22, 12, 1, 1, "pillar"),
        ),
    ),
    RoomTemplate(
        "S02",
        "上下矮墙",
        2,
        ("symmetric",),
        ((7, 5, 5, 1, "wall"), (20, 12, 5, 1, "wall")),
    ),
    RoomTemplate(
        "S03",
        "断开十字",
        2,
        ("symmetric", "split"),
        (
            (10, 8, 4, 1, "wall"),
            (19, 8, 4, 1, "wall"),
            (16, 3, 1, 3, "wall"),
            (16, 12, 1, 3, "wall"),
        ),
    ),
    RoomTemplate(
        "C01",
        "交错掩体",
        2,
        ("cover",),
        ((8, 5, 1, 3, "wall"), (15, 12, 1, 3, "wall"), (23, 5, 1, 3, "wall")),
    ),
    RoomTemplate(
        "C02",
        "冲锋中断线",
        3,
        ("cover", "heavy"),
        (
            (8, 7, 5, 1, "wall"),
            (20, 10, 5, 1, "wall"),
            (6, 12, 1, 1, "pillar"),
            (26, 5, 1, 1, "pillar"),
        ),
    ),
    RoomTemplate(
        "D01",
        "横向分割",
        3,
        ("split",),
        ((5, 8, 8, 1, "wall"), (20, 8, 7, 1, "wall")),
    ),
    RoomTemplate(
        "D02",
        "纵向分割",
        3,
        ("split",),
        ((16, 2, 1, 5, "wall"), (16, 11, 1, 5, "wall")),
    ),
    RoomTemplate(
        "P01",
        "双裂隙",
        3,
        ("pit",),
        ((7, 4, 3, 2, "block"), (22, 12, 3, 2, "block")),
    ),
    RoomTemplate(
        "P02",
        "侧向水坑",
        3,
        ("pit", "open"),
        ((6, 6, 3, 5, "block"), (24, 4, 2, 3, "block")),
    ),
)

PLAYER_SPAWN_CELL: Cell = (16, 9)
BOSS_EXIT_SWITCH_CELL: Cell = (26, 4)
SWITCH_CELLS: tuple[Cell, ...] = ((5, 4), (26, 4), (5, 13), (26, 13))
CRATE_CELLS: tuple[Cell, ...] = (
    (4, 4),
    (10, 4),
    (21, 4),
    (27, 4),
    (4, 13),
    (10, 13),
    (21, 13),
    (27, 13),
    (12, 7),
    (20, 10),
)
ENEMY_CELLS: tuple[Cell, ...] = tuple(
    (x, y) for y in (3, 6, 12, 15) for x in (3, 7, 11, 21, 25, 29)
)


def transform_cell(cell: Cell, transform: str) -> Cell:
    x, y = cell
    if transform in ("hflip", "rot180"):
        x = ROOM_GRID_WIDTH - 1 - x
    if transform in ("vflip", "rot180"):
        y = ROOM_GRID_HEIGHT - 1 - y
    return x, y


def transform_rect(rect: CellRect, transform: str) -> CellRect:
    x, y, width, height, kind = rect
    if transform in ("hflip", "rot180"):
        x = ROOM_GRID_WIDTH - x - width
    if transform in ("vflip", "rot180"):
        y = ROOM_GRID_HEIGHT - y - height
    return x, y, width, height, kind

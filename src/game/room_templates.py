from dataclasses import dataclass

from .config import ROOM_GRID_HEIGHT, ROOM_GRID_WIDTH

CellRect = tuple[int, int, int, int, str]
Cell = tuple[int, int]

DEFAULT_PLAYER_SPAWN_CELLS: tuple[Cell, ...] = ((16, 9),)
DEFAULT_SWITCH_CELLS: tuple[Cell, ...] = ((5, 4), (26, 4), (5, 13), (26, 13))
DEFAULT_CRATE_CELLS: tuple[Cell, ...] = (
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
DEFAULT_ENEMY_CELLS: tuple[Cell, ...] = tuple(
    (x, y) for y in (3, 6, 12, 15) for x in (3, 7, 11, 21, 25, 29)
)
DEFAULT_DECAL_CELLS: tuple[Cell, ...] = (
    (4, 3),
    (4, 8),
    (4, 14),
    (8, 3),
    (12, 14),
    (14, 3),
    (18, 14),
    (19, 3),
    (23, 14),
    (27, 3),
    (27, 8),
    (27, 14),
)


@dataclass(frozen=True)
class RoomTemplate:
    template_id: str
    name: str
    difficulty: int
    tags: tuple[str, ...]
    solids: tuple[CellRect, ...]
    allowed_door_masks: tuple[int, ...] = tuple(range(16))
    player_spawn_cells: tuple[Cell, ...] = DEFAULT_PLAYER_SPAWN_CELLS
    enemy_spawn_cells: tuple[Cell, ...] = DEFAULT_ENEMY_CELLS
    switch_cells: tuple[Cell, ...] = DEFAULT_SWITCH_CELLS
    crate_cells: tuple[Cell, ...] = DEFAULT_CRATE_CELLS
    pit_cells: tuple[Cell, ...] = ()
    decal_cells: tuple[Cell, ...] = DEFAULT_DECAL_CELLS


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
        "双侧裂隙",
        3,
        ("pit", "open"),
        ((6, 6, 2, 3, "block"), (24, 4, 2, 3, "block")),
    ),
)

PLAYER_SPAWN_CELL: Cell = DEFAULT_PLAYER_SPAWN_CELLS[0]
BOSS_SPAWN_CELL: Cell = (26, 9)
BOSS_OBSTACLES: tuple[CellRect, ...] = (
    (10, 5, 1, 1, "pillar"),
    (22, 5, 1, 1, "pillar"),
    (10, 12, 1, 1, "pillar"),
    (22, 12, 1, 1, "pillar"),
)
BOSS_DECAL_CELLS: tuple[Cell, ...] = (
    (5, 4),
    (5, 13),
    (15, 4),
    (17, 13),
    (27, 4),
    (27, 13),
)
SWITCH_CELLS: tuple[Cell, ...] = DEFAULT_SWITCH_CELLS
CRATE_CELLS: tuple[Cell, ...] = DEFAULT_CRATE_CELLS
ENEMY_CELLS: tuple[Cell, ...] = DEFAULT_ENEMY_CELLS

SECONDARY_SHORT_WALL_PATTERN: tuple[CellRect, ...] = (
    (0, 0, 2, 1, "wall"),
    (4, 3, 2, 1, "wall"),
)
SECONDARY_LIGHT_COVER_PATTERN: tuple[CellRect, ...] = (
    (0, 1, 2, 1, "wall"),
    (4, 3, 2, 1, "wall"),
    (2, 0, 1, 1, "pillar"),
    (3, 4, 1, 1, "pillar"),
)
SECONDARY_LONG_COVER_PATTERN: tuple[CellRect, ...] = (
    (0, 0, 3, 1, "wall"),
    (0, 4, 3, 1, "wall"),
    (5, 1, 1, 1, "pillar"),
    (5, 3, 1, 1, "pillar"),
)
SECONDARY_PIT_PATTERN: tuple[CellRect, ...] = (
    (0, 0, 2, 2, "block"),
    (5, 3, 2, 2, "block"),
)
SECONDARY_PATTERNS: tuple[tuple[CellRect, ...], ...] = (
    SECONDARY_SHORT_WALL_PATTERN,
    SECONDARY_LIGHT_COVER_PATTERN,
    SECONDARY_LONG_COVER_PATTERN,
    SECONDARY_PIT_PATTERN,
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

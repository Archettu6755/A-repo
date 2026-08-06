WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

TILE_SIZE = 32
ROOM_GRID_WIDTH = 32
ROOM_GRID_HEIGHT = 18
ROOM_WIDTH = ROOM_GRID_WIDTH * TILE_SIZE
ROOM_HEIGHT = ROOM_GRID_HEIGHT * TILE_SIZE
ROOM_TOP_OFFSET = 48
WALL_THICKNESS = TILE_SIZE
DOOR_WIDTH = 2 * TILE_SIZE

ROOM_COUNT_RANGE = {1: (2, 3), 2: (2, 4), 3: (2, 4)}
BOX_EXTRA_RANGE = {1: (0, 1), 2: (1, 2), 3: (2, 3)}

OBSTACLE_COLORS = {
    "pillar": (90, 100, 125),
    "wall": (110, 120, 145),
    "block": (65, 80, 105),
}
OBSTACLE_BORDER = (35, 45, 65)

BOX_HP = 3
BOX_SIZE = 32
BOX_COLOR = (200, 130, 60)

SWITCH_SIZE = 22
SWITCH_COLOR = (255, 255, 255)
SWITCH_COLOR_ACTIVE = (120, 220, 120)

VISION_RADIUS = 224
ZOMBIE_CHARGE_DIST = 160
ZOMBIE_SPAWN_GAP = 8

PLAYER_SIZE = 28
PLAYER_SEPARATION_RADIUS = 12
PLAYER_COLOR = (70, 130, 255)
PLAYER_MAX_HP = 5
PLAYER_ATTACK = 1
PLAYER_FIRE_COOLDOWN = 0.3
PLAYER_SPEED = 3

BULLET_SPEED = 6
BULLET_RANGE = 300
BULLET_SIZE = 8
BULLET_COLOR = (80, 200, 255)
BULLET_COOLDOWN_BONUS = 0.08

INVINCIBLE_TIME = 0.5

ZOMBIE_COLORS = {
    "normal": (60, 180, 80),
    "fast": (120, 220, 90),
    "heavy": (40, 120, 60),
}

ZOMBIE_TYPES = {
    "normal": {
        "hp": 3,
        "damage": 1,
        "speed": 1.2,
        "size": 28,
        "separation_radius": 12,
        "warning": 0.35,
        "charge_mult": 3.0,
        "max_charge_dist": 400,
        "stun": 0.6,
        "color": "normal",
    },
    "fast": {
        "hp": 2,
        "damage": 1,
        "speed": 2.0,
        "size": 20,
        "separation_radius": 9,
        "warning": 0.20,
        "charge_mult": 3.0,
        "max_charge_dist": 192,
        "stun": 0.45,
        "color": "fast",
    },
    "heavy": {
        "hp": 4,
        "damage": 2,
        "speed": 0.9,
        "size": 38,
        "separation_radius": 17,
        "warning": 0.65,
        "charge_mult": 5.0,
        "max_charge_dist": 320,
        "stun": 0.9,
        "color": "heavy",
    },
}

COIN_SIZE = 10
COIN_COLOR = (255, 215, 0)
COIN_DROP_CHANCE = 0.5
COIN_VALUE = 1
COIN_LIFETIME = 20

LEVEL_COUNT = 3
LEVEL_CLEAR_DELAY = 2.5
ZOMBIE_COUNT_RANGE = {1: (10, 12), 2: (14, 16), 3: (18, 20)}
ZOMBIE_TYPE_WEIGHTS = {
    1: {"normal": 70, "fast": 20, "heavy": 10},
    2: {"normal": 55, "fast": 25, "heavy": 20},
    3: {"normal": 40, "fast": 35, "heavy": 25},
}

SHOP_ITEMS = [
    {
        "key": "attack",
        "name": "攻击力 +1",
        "desc": "子弹伤害提升",
        "price": 2,
        "raise": 2,
        "max_value": 5,
    },
    {
        "key": "max_hp",
        "name": "生命上限 +1",
        "desc": "最大生命值提升",
        "price": 5,
        "raise": 3,
        "max_value": 10,
    },
    {
        "key": "fire_speed",
        "name": "射速提升",
        "desc": "缩短子弹冷却",
        "price": 6,
        "raise": 6,
        "min_value": 0.15,
    },
    {
        "key": "move_speed",
        "name": "移速提升",
        "desc": "提升移动速度",
        "price": 5,
        "raise": 5,
        "max_value": 5,
    },
    {"key": "heal", "name": "回血", "desc": "恢复 3 点生命", "price": 2, "raise": 1},
]

COLORS = {
    "background": (24, 24, 32),
    "wall": (90, 90, 100),
    "hud": (240, 240, 240),
    "title": (255, 80, 80),
    "info": (180, 180, 200),
    "highlight": (255, 200, 60),
    "disabled": (110, 110, 120),
    "error": (255, 80, 80),
    "ok": (120, 220, 120),
}

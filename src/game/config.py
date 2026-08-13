import os

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
LOW_PERFORMANCE_MODE = os.environ.get("GAME_LOW_PERFORMANCE") == "1"
FPS = 30 if LOW_PERFORMANCE_MODE else 60
MAX_VISUAL_EFFECTS = 80

TILE_SIZE = 32
ROOM_GRID_WIDTH = 32
ROOM_GRID_HEIGHT = 18
ROOM_WIDTH = ROOM_GRID_WIDTH * TILE_SIZE
ROOM_HEIGHT = ROOM_GRID_HEIGHT * TILE_SIZE
ROOM_TOP_OFFSET = 48
ROOM_SCREEN_LEFT = 128
ROOM_SCREEN_TOP = 120
WALL_THICKNESS = TILE_SIZE
DOOR_WIDTH = 2 * TILE_SIZE

HEART_SIZE = 24
HEARTS_PER_ROW = 3
HEART_GAP = 4
HEART_ORIGIN = (8, 6)

ROOM_COUNT_RANGE = {1: (1, 1), 2: (3, 3), 3: (2, 2)}
OBSTACLE_CELL_RANGE = {1: (12, 20), 2: (18, 28), 3: (24, 36)}
SECONDARY_GROUP_COUNT_RANGE = {1: (1, 1), 2: (1, 2), 3: (2, 3)}
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
ZOMBIE_SPAWN_GAP = 8
ZOMBIE_WANDER_INTERVAL = (1.2, 2.5)
ZOMBIE_RECOVERY_TIME = (0.4, 0.8)

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
        "hp": 4,
        "damage": 1,
        "speed": 1.0,
        "size": 28,
        "separation_radius": 12,
        "warning": 0.50,
        "sensing_distance": 256,
        "charge_mult": 2.5,
        "max_charge_dist": 320,
        "stun": 0.6,
        "color": "normal",
    },
    "fast": {
        "hp": 2,
        "damage": 1,
        "speed": 1.6,
        "size": 20,
        "separation_radius": 9,
        "warning": 0.35,
        "sensing_distance": 224,
        "charge_mult": 2.5,
        "max_charge_dist": 256,
        "stun": 0.45,
        "color": "fast",
    },
    "heavy": {
        "hp": 6,
        "damage": 2,
        "speed": 0.8,
        "size": 38,
        "separation_radius": 17,
        "warning": 0.80,
        "sensing_distance": 256,
        "charge_mult": 4.0,
        "max_charge_dist": 352,
        "stun": 0.9,
        "color": "heavy",
    },
}

BOSS_SIZE = 56
BOSS_SEPARATION_RADIUS = 28
BOSS_CANVAS_SIZE = (80, 88)
BOSS_DEATH_TIME = 1.0
BOSS_CHARGE_SUBSTEP = 8.0
BOSS_PHASE_STATS = {
    1: {
        "hp": 80,
        "base_speed": 1.0,
        "warning": 0.80,
        "charge_speed": 6.0,
        "max_charge_dist": 640.0,
        "charges": 1,
        "stun": 1.10,
        "recovery": 1.00,
        "damage": 2,
    },
    2: {
        "hp": 50,
        "base_speed": 1.4,
        "warning": 0.40,
        "charge_speed": 7.5,
        "max_charge_dist": 480.0,
        "charges": 2,
        "stun": 0.60,
        "recovery": 0.50,
        "damage": 3,
    },
}

COIN_SIZE = 10
COIN_COLOR = (255, 215, 0)
COIN_DROP_CHANCE = 0.5
COIN_VALUE = 1
COIN_LIFETIME = 20

LEVEL_COUNT = 3
LEVEL_CLEAR_DELAY = 2.5
ZOMBIE_COUNT_PER_ROOM_RANGE = {1: (6, 8), 2: (8, 10), 3: (11, 13)}
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

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

ROOM_MIN_WIDTH = 768
ROOM_MAX_WIDTH = 1024
ROOM_MIN_HEIGHT = 432
ROOM_MAX_HEIGHT = 576
WALL_THICKNESS = 20

PLAYER_SIZE = 28
PLAYER_COLOR = (70, 130, 255)
PLAYER_MAX_HP = 5
PLAYER_ATTACK = 1
PLAYER_FIRE_COOLDOWN = 0.3
PLAYER_SPEED = 3
PLAYER_SPAWN_OFFSET = 40

BULLET_SPEED = 6
BULLET_RANGE = 300
BULLET_SIZE = 8
BULLET_COLOR = (80, 200, 255)
BULLET_COOLDOWN_BONUS = 0.08

INVINCIBLE_TIME = 0.5

ZOMBIE_CHARGE_DIST = 200
ZOMBIE_CHARGE_SPEED_MULT = 2.5
ZOMBIE_STUN_TIME = 0.5
ZOMBIE_MAX_CHARGE_DIST = 400
ZOMBIE_COLORS = {
    "normal": (60, 180, 80),
    "fast": (120, 220, 90),
    "heavy": (40, 120, 60),
}

ZOMBIE_TYPES = {
    "normal": {"hp": 2, "damage": 1, "speed": 1.0, "size": 28, "color": "normal"},
    "fast": {"hp": 1, "damage": 1, "speed": 1.8, "size": 20, "color": "fast"},
    "heavy": {"hp": 3, "damage": 2, "speed": 0.7, "size": 38, "color": "heavy"},
}

COIN_SIZE = 10
COIN_COLOR = (255, 215, 0)
COIN_DROP_CHANCE = 0.5
COIN_VALUE = 1
COIN_LIFETIME = 20

LEVEL_COUNT = 2
LEVEL_CLEAR_DELAY = 2.5
ZOMBIE_COUNT_RANGE = {1: (5, 10), 2: (8, 15)}
HEAVY_CHANCE = {1: 0.2, 2: 0.35}

SHOP_ITEMS = [
    {"key": "attack", "name": "攻击力 +1", "desc": "子弹伤害提升", "price": 5},
    {"key": "max_hp", "name": "生命上限 +1", "desc": "最大生命值提升", "price": 10},
    {"key": "fire_speed", "name": "射速提升", "desc": "缩短子弹冷却", "price": 8},
    {"key": "move_speed", "name": "移速提升", "desc": "提升移动速度", "price": 8},
    {"key": "heal", "name": "回血", "desc": "恢复 3 点生命", "price": 3},
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

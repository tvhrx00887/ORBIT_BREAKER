# ==========================================
# ORBIT BREAKER - SETTINGS
# ==========================================

WIDTH = 1000
HEIGHT = 720
FPS = 60
TILE = 40                      # level grid: 25 columns x 18 rows

GAME_TITLE = "ORBIT BREAKER"

# Colours
BACKGROUND = (9, 13, 26)
WHITE = (240, 245, 255)
CYAN = (50, 220, 235)
DARK_CYAN = (20, 90, 110)
PLATFORM = (43, 55, 76)
PLATFORM_DARK = (30, 40, 58)
PURPLE = (160, 110, 255)
YELLOW = (255, 215, 85)
RED = (255, 75, 95)
GREEN = (85, 230, 155)
GREY = (135, 150, 175)
ORANGE = (255, 150, 80)
PINK = (235, 95, 215)

# Player
PLAYER_W = 26
PLAYER_H = 34
PLAYER_SPEED = 5
GRAVITY = 0.6
JUMP_STRENGTH = -13.5
MAX_FALL = 15
JUMP_CUT = 0.45                # releasing jump early multiplies upward speed by this
COYOTE_FRAMES = 6              # grace frames to jump after leaving a ledge
JUMP_BUFFER_FRAMES = 6         # grace frames to press jump before landing

# Dash
DASH_SPEED = 13
DASH_DURATION = 9
DASH_COOLDOWN = 50

# World objects
PAD_STRENGTH = -19
SWITCH_COOLDOWN = 50
CRUMBLE_DELAY = 28
CRUMBLE_RESPAWN = 200
ENEMY_SPEED = 1.3

# Gameplay
STARTING_LIVES = 3
MAX_LIVES = 5
ORB_VALUE = 10
ENEMY_VALUE = 25
EXTRA_LIFE_EVERY = 100         # score needed for each bonus life
INVULN_FRAMES = 90             # blink time after respawning
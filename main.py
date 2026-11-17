# =====================================================
# ORBIT BREAKER
# A complete space platformer
#
# Run with:   python main.py
# Files:      main.py (engine), settings.py (tuning), levels.py (maps)
# =====================================================

import array
import json
import math
import os
import random
import sys

import pygame

import levels as LV
import settings as S

TILE = S.TILE
COLS = S.WIDTH // TILE
ROWS = S.HEIGHT // TILE
PW, PH = S.PLAYER_W, S.PLAYER_H
NUM_LEVELS = len(LV.LEVELS)

SAVE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "orbit_breaker_save.json"
)

JUMP_KEYS = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
DASH_KEYS = (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_x)


# =====================================================
# SMALL HELPERS
# =====================================================

def hit(x, y, w, h, r):
    """Float-friendly overlap test between a box and a pygame.Rect."""
    return x < r.right and x + w > r.left and y < r.bottom and y + h > r.top


_glow_cache = {}


def glow(radius, colour, strength=60):
    key = (radius, colour, strength)
    if key not in _glow_cache:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -2):
            a = int(strength * (1 - r / radius) ** 2)
            pygame.draw.circle(surf, (*colour, a), (radius, radius), r)
        _glow_cache[key] = surf
    return _glow_cache[key]


def draw_text(surf, s, font, colour, x, y, anchor="topleft", shadow=True):
    img = font.render(s, True, colour)
    rect = img.get_rect(**{anchor: (x, y)})
    if shadow:
        surf.blit(font.render(s, True, (0, 0, 0)), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def draw_text_alpha(surf, s, font, colour, cx, cy, alpha):
    img = font.render(s, True, colour)
    img.set_alpha(int(255 * max(0, min(1, alpha))))
    surf.blit(img, img.get_rect(center=(cx, cy)))


def format_time(frames):
    seconds = frames // S.FPS
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def star_points(cx, cy, r):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    return pts


def draw_stars(surf, cx, cy, count, r=14, gap=36):
    for i in range(3):
        x = cx + (i - 1) * gap
        pts = star_points(x, cy, r)
        if i < count:
            pygame.draw.polygon(surf, S.YELLOW, pts)
            pygame.draw.polygon(surf, S.WHITE, pts, 1)
        else:
            pygame.draw.polygon(surf, (50, 60, 80), pts)
            pygame.draw.polygon(surf, (90, 100, 125), pts, 1)


def draw_heart(surf, x, y, colour, size=16):
    r = size // 4
    pygame.draw.circle(surf, colour, (x + r, y + r), r)
    pygame.draw.circle(surf, colour, (x + 3 * r, y + r), r)
    pygame.draw.polygon(
        surf, colour, [(x, y + r + 1), (x + 4 * r, y + r + 1), (x + 2 * r, y + 4 * r)]
    )


# =====================================================
# SAVE DATA
# =====================================================

def load_save():
    data = {"unlocked": 1, "stars": [0] * NUM_LEVELS, "best_score": 0}
    try:
        with open(SAVE_PATH, "r") as f:
            loaded = json.load(f)
        data["unlocked"] = max(1, min(NUM_LEVELS, int(loaded.get("unlocked", 1))))
        stars = loaded.get("stars", [])
        for i in range(min(NUM_LEVELS, len(stars))):
            data["stars"][i] = max(0, min(3, int(stars[i])))
        data["best_score"] = int(loaded.get("best_score", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return data


def write_save(data):
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


# =====================================================
# SOUND (all generated in code, no asset files needed)
# =====================================================

def make_sound(f0, f1, dur, vol=0.2, kind="sine"):
    rate, fmt, channels = pygame.mixer.get_init()
    if fmt != -16:
        raise pygame.error("unsupported mixer format")
    n = int(rate * dur)
    buf = array.array("h")
    phase = 0.0
    for i in range(n):
        k = i / n
        phase += 2 * math.pi * (f0 + (f1 - f0) * k) / rate
        if kind == "square":
            v = 1.0 if math.sin(phase) >= 0 else -1.0
        elif kind == "noise":
            v = random.uniform(-1, 1)
        else:
            v = math.sin(phase)
        env = min(1.0, i / 200) * (1 - k) ** 0.7
        sample = int(32767 * vol * env * v)
        buf.append(sample)
        if channels == 2:
            buf.append(sample)
    return pygame.mixer.Sound(buffer=buf.tobytes())


class Sound:
    def __init__(self):
        self.enabled = True
        self.fx = {}
        try:
            self.fx = {
                "jump": make_sound(300, 620, 0.12),
                "collect": make_sound(800, 1400, 0.12),
                "death": make_sound(320, 60, 0.4, 0.14, "square"),
                "checkpoint": make_sound(500, 900, 0.25),
                "portal": make_sound(600, 1500, 0.4),
                "dash": make_sound(0, 0, 0.12, 0.10, "noise"),
                "stomp": make_sound(420, 150, 0.12, 0.15, "square"),
                "flip": make_sound(250, 800, 0.22),
                "pad": make_sound(250, 900, 0.2, 0.14, "square"),
                "crumble": make_sound(0, 0, 0.2, 0.10, "noise"),
                "select": make_sound(700, 700, 0.05, 0.12),
                "win": make_sound(520, 1050, 0.5),
            }
        except (pygame.error, TypeError):
            self.fx = {}

    def play(self, name):
        if self.enabled and name in self.fx:
            self.fx[name].play()


# =====================================================
# ENTITIES
# =====================================================

class Body:
    """Player physics. Pure logic (no drawing) so it can be unit-tested."""

    def __init__(self, x, y, g=1):
        self.x = float(x)
        self.y = float(y)
        self.vy = 0.0
        self.g = g                  # +1 = gravity down, -1 = gravity up
        self.on_ground = False
        self.coyote = 0
        self.support = None         # crumble/mover currently stood on
        self.pad_cd = 0
        self.sw_cd = 0

    def clone(self):
        b = Body(self.x, self.y, self.g)
        b.vy, b.on_ground, b.coyote = self.vy, self.on_ground, self.coyote
        b.support, b.pad_cd, b.sw_cd = self.support, self.pad_cd, self.sw_cd
        return b

    def move_x(self, level, dx):
        if dx == 0:
            return False
        self.x += dx
        blocked = False
        if self.x < 0:
            self.x, blocked = 0.0, True
        if self.x + PW > S.WIDTH:
            self.x, blocked = float(S.WIDTH - PW), True
        for rect, _obj in level.solids_near(self.x, self.y, PW, PH):
            if hit(self.x, self.y, PW, PH, rect):
                self.x = rect.left - PW if dx > 0 else rect.right
                blocked = True
        return blocked

    def move_y(self, level, dy):
        self.y += dy
        landed = False
        self.support = None
        for rect, obj in level.solids_near(self.x, self.y, PW, PH):
            if hit(self.x, self.y, PW, PH, rect):
                if dy > 0:
                    self.y = rect.top - PH
                elif dy < 0:
                    self.y = rect.bottom
                else:
                    continue
                if (dy > 0) == (self.g > 0):
                    landed = True
                    self.support = obj
                self.vy = 0.0
        return landed

    def step(self, level, move, want_jump):
        """Advance one frame. Returns True if a jump started this frame."""
        g = self.g
        jumped = False
        if want_jump and self.coyote > 0:
            self.vy = S.JUMP_STRENGTH * g
            self.coyote = 0
            self.on_ground = False
            jumped = True
        self.move_x(level, move * S.PLAYER_SPEED)
        self.vy += S.GRAVITY * g
        if self.vy * g > S.MAX_FALL:
            self.vy = S.MAX_FALL * g
        landed = self.move_y(level, self.vy)
        self.on_ground = landed
        self.coyote = S.COYOTE_FRAMES if landed else max(0, self.coyote - 1)
        return jumped

    def triggers(self, level):
        """Spring pads and gravity rings. Returns list of event names."""
        events = []
        if self.pad_cd > 0:
            self.pad_cd -= 1
        if self.sw_cd > 0:
            self.sw_cd -= 1
        box = pygame.Rect(int(self.x), int(self.y), PW, PH)
        if self.pad_cd == 0:
            for pad in level.pads:
                if box.colliderect(pad):
                    self.vy = S.PAD_STRENGTH * self.g
                    self.on_ground = False
                    self.coyote = 0
                    self.pad_cd = 8
                    events.append("pad")
                    break
        if self.sw_cd == 0:
            for ring in level.switches:
                if box.colliderect(ring):
                    self.g = -self.g
                    self.vy = 0.0
                    self.on_ground = False
                    self.coyote = 0
                    self.sw_cd = S.SWITCH_COOLDOWN
                    events.append("flip")
                    break
        return events


class Crumble:
    def __init__(self, c, r):
        self.rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
        self.state = 0              # 0 solid, 1 shaking, 2 gone
        self.timer = 0

    @property
    def solid(self):
        return self.state < 2

    def trigger(self):
        if self.state == 0:
            self.state = 1
            self.timer = S.CRUMBLE_DELAY

    def update(self, body):
        """Returns True on the frame it breaks apart."""
        if self.state == 1:
            self.timer -= 1
            if self.timer <= 0:
                self.state = 2
                self.timer = S.CRUMBLE_RESPAWN
                return True
        elif self.state == 2:
            self.timer -= 1
            if self.timer <= 0 and not hit(body.x, body.y, PW, PH, self.rect):
                self.state = 0
        return False


class Mover:
    HEIGHT = 16

    def __init__(self, d):
        self.x0 = d["c"] * TILE
        self.y0 = d["r"] * TILE
        self.w = d["w"] * TILE
        self.dx = d["dx"] * TILE
        self.dy = d["dy"] * TILE
        self.length = math.hypot(self.dx, self.dy)
        self.speed = d.get("speed", 1.5)
        self.s = 0.0
        self.dir = 1
        self.pause = 0
        self.rect = pygame.Rect(self.x0, self.y0, self.w, self.HEIGHT)

    def update(self):
        if self.length > 0:
            if self.pause > 0:
                self.pause -= 1
            else:
                self.s += self.dir * self.speed
                if self.s >= self.length:
                    self.s, self.dir, self.pause = self.length, -1, 30
                elif self.s <= 0:
                    self.s, self.dir, self.pause = 0.0, 1, 30
        k = self.s / self.length if self.length else 0
        self.rect.x = round(self.x0 + self.dx * k)
        self.rect.y = round(self.y0 + self.dy * k)


class Walker:
    SIZE = 28

    def __init__(self, c, r):
        self.x = c * TILE + (TILE - self.SIZE) / 2
        self.y = (r + 1) * TILE - self.SIZE
        self.dir = 1
        self.alive = True
        self.anim = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.SIZE, self.SIZE)

    def update(self, level, t):
        nx = self.x + self.dir * S.ENEMY_SPEED
        edge_x = nx + (self.SIZE if self.dir > 0 else 0)
        col = int(edge_x // TILE)
        row_body = int((self.y + self.SIZE / 2) // TILE)
        row_floor = int((self.y + self.SIZE + 2) // TILE)
        if level.blocks_walker(col, row_body) or not level.is_solid(col, row_floor):
            self.dir = -self.dir
        else:
            self.x = nx
        self.anim += 1


class Flyer:
    SIZE = 26

    def __init__(self, c, r, horizontal):
        self.cx = c * TILE + TILE / 2
        self.cy = r * TILE + TILE / 2
        self.horizontal = horizontal
        self.amp = 100 if horizontal else 60
        self.phase = (c * 7 + r * 3) % 6
        self.x, self.y = self.cx, self.cy
        self.alive = True

    @property
    def rect(self):
        h = self.SIZE // 2
        return pygame.Rect(int(self.x - h), int(self.y - h), self.SIZE, self.SIZE)

    def update(self, level, t):
        off = math.sin(t * 0.03 + self.phase) * self.amp
        if self.horizontal:
            self.x, self.y = self.cx + off, self.cy
        else:
            self.x, self.y = self.cx, self.cy + off


# =====================================================
# LEVEL
# =====================================================

class Level:
    def __init__(self, data):
        self.name = data["name"]
        self.hint = data.get("hint", "")
        rows = list(data["map"])
        if len(rows) > ROWS:
            raise ValueError(f"{self.name}: too many rows")
        rows = [""] * (ROWS - len(rows)) + rows

        self.solid = set()
        self.spike_cells = []
        self.hazards = []
        self.hazard_cells = set()
        self.orbs = []
        self.pads = []
        self.switches = []
        self.checkpoints = []
        self.crumbles = []
        self.enemies = []
        self.movers = [Mover(m) for m in data.get("movers", [])]
        self.spawn = (TILE, ROWS * TILE - 2 * TILE)
        self.exit_rect = pygame.Rect(0, 0, 44, 64)

        for r, row in enumerate(rows):
            if len(row) > COLS:
                raise ValueError(f"{self.name}: row {r} is longer than {COLS}")
            for c, ch in enumerate(row.ljust(COLS)):
                x, y = c * TILE, r * TILE
                if ch == "#":
                    self.solid.add((c, r))
                elif ch == "^":
                    self.spike_cells.append((c, r, ch))
                    self.hazards.append(pygame.Rect(x + 6, y + TILE - 20, TILE - 12, 20))
                    self.hazard_cells.add((c, r))
                elif ch == "v":
                    self.spike_cells.append((c, r, ch))
                    self.hazards.append(pygame.Rect(x + 6, y, TILE - 12, 20))
                    self.hazard_cells.add((c, r))
                elif ch == "o":
                    self.orbs.append(
                        {"x": x + TILE // 2, "y": y + TILE // 2, "got": False,
                         "phase": random.random() * 6}
                    )
                elif ch == "C":
                    self.checkpoints.append({"rect": pygame.Rect(x + 8, y, 24, TILE),
                                             "active": False})
                elif ch == "P":
                    self.spawn = (x + (TILE - PW) / 2, y + TILE - PH)
                elif ch == "E":
                    self.exit_rect.midbottom = (x + TILE // 2, y + TILE)
                elif ch == "c":
                    self.crumbles.append(Crumble(c, r))
                elif ch == "J":
                    self.pads.append(pygame.Rect(x + 4, y + TILE - 14, TILE - 8, 14))
                elif ch == "g":
                    self.switches.append(pygame.Rect(x + 4, y + 4, TILE - 8, TILE - 8))
                elif ch == "w":
                    self.enemies.append(Walker(c, r))
                elif ch == "f":
                    self.enemies.append(Flyer(c, r, False))
                elif ch == "F":
                    self.enemies.append(Flyer(c, r, True))

    def is_solid(self, c, r):
        if c < 0 or c >= COLS or r < 0:
            return True
        return (c, r) in self.solid

    def blocks_walker(self, c, r):
        return self.is_solid(c, r) or (c, r) in self.hazard_cells

    def solids_near(self, x, y, w, h):
        out = []
        c0, c1 = int((x - 1) // TILE), int((x + w + 1) // TILE)
        r0, r1 = int((y - 1) // TILE), int((y + h + 1) // TILE)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (c, r) in self.solid:
                    out.append((pygame.Rect(c * TILE, r * TILE, TILE, TILE), None))
        for cr in self.crumbles:
            if cr.solid:
                out.append((cr.rect, cr))
        for m in self.movers:
            out.append((m.rect, m))
        return out

    def orbs_left(self):
        return sum(1 for o in self.orbs if not o["got"])

    def render_static(self):
        """Pre-draw blocks and spikes once per level."""
        surf = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        for (c, r) in self.solid:
            x, y = c * TILE, r * TILE
            pygame.draw.rect(surf, S.PLATFORM, (x, y, TILE, TILE))
            pygame.draw.rect(surf, S.PLATFORM_DARK, (x + 4, y + 4, TILE - 8, TILE - 8), 1)
            for rx, ry in ((x + 6, y + 6), (x + TILE - 7, y + 6),
                           (x + 6, y + TILE - 7), (x + TILE - 7, y + TILE - 7)):
                surf.set_at((rx, ry), (90, 105, 135))
        for (c, r) in self.solid:
            x, y = c * TILE, r * TILE
            if (c, r - 1) not in self.solid:
                pygame.draw.line(surf, S.CYAN, (x, y + 1), (x + TILE - 1, y + 1), 3)
            if (c, r + 1) not in self.solid and r + 1 < ROWS:
                pygame.draw.line(surf, S.PURPLE, (x, y + TILE - 2), (x + TILE - 1, y + TILE - 2), 2)
            if (c - 1, r) not in self.solid and c > 0:
                pygame.draw.line(surf, (70, 90, 120), (x, y), (x, y + TILE - 1), 2)
            if (c + 1, r) not in self.solid and c < COLS - 1:
                pygame.draw.line(surf, (70, 90, 120), (x + TILE - 1, y), (x + TILE - 1, y + TILE - 1), 2)
        for (c, r, ch) in self.spike_cells:
            x, y = c * TILE, r * TILE
            for k in range(2):
                bx = x + 3 + k * 17
                if ch == "^":
                    pts = [(bx, y + TILE), (bx + 8, y + TILE - 22), (bx + 17, y + TILE)]
                else:
                    pts = [(bx, y), (bx + 8, y + 22), (bx + 17, y)]
                pygame.draw.polygon(surf, S.RED, pts)
                pygame.draw.polygon(surf, S.WHITE, pts, 1)
        return surf


# =====================================================
# ICON DRAWING (used in the world and the help screen)
# =====================================================

def draw_orb(surf, cx, cy, t, phase=0.0):
    cy = int(cy + math.sin(t * 0.08 + phase) * 3)
    cx = int(cx)
    surf.blit(glow(24, S.YELLOW), (cx - 24, cy - 24))
    pygame.draw.circle(surf, S.YELLOW, (cx, cy), 9)
    pygame.draw.circle(surf, S.WHITE, (cx - 2, cy - 2), 3)


def draw_spike_icon(surf, x, y):
    for k in range(2):
        bx = x + 3 + k * 17
        pts = [(bx, y + TILE), (bx + 8, y + TILE - 22), (bx + 17, y + TILE)]
        pygame.draw.polygon(surf, S.RED, pts)
        pygame.draw.polygon(surf, S.WHITE, pts, 1)


def draw_checkpoint(surf, rect, active, t):
    colour = S.GREEN if active else S.PURPLE
    pole_x = rect.centerx - 6
    pygame.draw.line(surf, S.WHITE, (pole_x, rect.top + 4), (pole_x, rect.bottom), 3)
    wave = int(math.sin(t * 0.15) * 2)
    pts = [(pole_x + 2, rect.top + 5), (pole_x + 20 + wave, rect.top + 12),
           (pole_x + 2, rect.top + 19)]
    pygame.draw.polygon(surf, colour, pts)
    if active:
        surf.blit(glow(26, S.GREEN, 50), (rect.centerx - 26, rect.centery - 26))


def draw_portal(surf, rect, is_open, t):
    cx, cy = rect.center
    col = S.CYAN if is_open else S.GREY
    dark = S.DARK_CYAN if is_open else (38, 46, 62)
    if is_open:
        surf.blit(glow(70, S.CYAN, 70), (cx - 70, cy - 70))
    pygame.draw.ellipse(surf, dark, rect)
    pygame.draw.ellipse(surf, col, rect, 4)
    for i in range(3):
        k = (t * 0.03 * (1 if is_open else 0.3) + i / 3) % 1
        w, h = int(rect.w * (1 - k)), int(rect.h * (1 - k))
        if w > 6 and h > 6:
            r = pygame.Rect(0, 0, w, h)
            r.center = (cx, cy)
            pygame.draw.ellipse(surf, col, r, 1)


def draw_pad(surf, rect, t):
    pygame.draw.rect(surf, (60, 70, 95), (rect.x, rect.bottom - 4, rect.w, 4))
    pts = []
    for i in range(7):
        px = rect.x + 5 + (rect.w - 10) * (i % 2)
        py = rect.bottom - 4 - i * 1.4
        pts.append((px, py))
    pygame.draw.lines(surf, S.GREY, False, pts, 2)
    pygame.draw.rect(surf, S.GREEN, (rect.x, rect.y, rect.w, 5), border_radius=2)


def draw_switch(surf, rect, t):
    cx, cy = rect.center
    surf.blit(glow(30, S.PURPLE, 70), (cx - 30, cy - 30))
    pygame.draw.circle(surf, S.PURPLE, (cx, cy), 14, 3)
    for i in range(2):
        a = t * 0.06 + i * math.pi
        pygame.draw.circle(surf, S.WHITE, (cx + math.cos(a) * 14, cy + math.sin(a) * 14), 3)
    pygame.draw.polygon(surf, S.WHITE, [(cx, cy - 7), (cx - 4, cy - 2), (cx + 4, cy - 2)])
    pygame.draw.polygon(surf, S.WHITE, [(cx, cy + 7), (cx - 4, cy + 2), (cx + 4, cy + 2)])


def draw_walker(surf, e, t):
    r = e.rect
    pygame.draw.rect(surf, S.ORANGE, (r.x, r.y, r.w, r.h - 5), border_radius=7)
    pygame.draw.rect(surf, (170, 80, 40), (r.x, r.y, r.w, r.h - 5), 2, border_radius=7)
    eye_x = r.centerx + e.dir * 5
    pygame.draw.circle(surf, S.WHITE, (eye_x, r.y + 10), 6)
    pygame.draw.circle(surf, (30, 20, 20), (eye_x + e.dir * 2, r.y + 10), 3)
    lift = (e.anim // 8) % 2
    pygame.draw.rect(surf, (170, 80, 40), (r.x + 3, r.bottom - 5, 8, 5 - lift * 2))
    pygame.draw.rect(surf, (170, 80, 40), (r.right - 11, r.bottom - 5, 8, 3 + lift * 2))


def draw_flyer(surf, e, t):
    cx, cy = int(e.x), int(e.y)
    surf.blit(glow(26, S.PINK, 60), (cx - 26, cy - 26))
    for i in range(4):
        a = t * 0.12 + i * math.pi / 2
        pygame.draw.line(surf, S.PINK, (cx, cy),
                         (cx + math.cos(a) * 16, cy + math.sin(a) * 16), 3)
    pygame.draw.circle(surf, (120, 40, 110), (cx, cy), 10)
    pygame.draw.circle(surf, S.PINK, (cx, cy), 10, 2)
    pygame.draw.circle(surf, S.WHITE, (cx, cy), 4)
    pygame.draw.circle(surf, (30, 10, 30), (cx, cy), 2)


# =====================================================
# GAME
# =====================================================

class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption(S.GAME_TITLE)
        self.canvas = pygame.Surface((S.WIDTH, S.HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.Font(None, 30)
        self.small = pygame.font.Font(None, 23)
        self.mid = pygame.font.Font(None, 40)
        self.big = pygame.font.Font(None, 64)
        self.title_font = pygame.font.Font(None, 110)

        self.sound = Sound()
        self.save = load_save()
        self.bg = self.build_background()
        rnd = random.Random(42)
        self.stars = [[rnd.randint(0, S.WIDTH), rnd.randint(0, S.HEIGHT),
                       rnd.choice([1, 1, 2, 2, 3]), rnd.random() * 6] for _ in range(130)]

        self.t = 0
        self.state = "MENU"
        self.menu_idx = 0
        self.select_idx = 0
        self.particles = []
        self.shake = 0.0

        # run state
        self.level_index = 0
        self.level = None
        self.static = None
        self.body = Body(0, 0)
        self.score = 0
        self.lives = S.STARTING_LIVES
        self.next_life_at = S.EXTRA_LIFE_EVERY
        self.level_start_score = 0
        self.level_deaths = 0
        self.level_frames = 0
        self.last_stars = 0
        self.new_best = False
        self.facing = 1
        self.moving = False
        self.dash_frames = 0
        self.dash_cd = 0
        self.iframes = 0
        self.jump_buffer = 0
        self.cp = None            # (x, y, g)
        self.banner = 0
        self.message = ("", 0)

    # ---------------------------------------------------------- setup
    def build_background(self):
        bg = pygame.Surface((S.WIDTH, S.HEIGHT))
        top, bottom = (6, 9, 22), (20, 14, 44)
        for y in range(S.HEIGHT):
            k = y / S.HEIGHT
            col = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
            pygame.draw.line(bg, col, (0, y), (S.WIDTH, y))
        rnd = random.Random(7)
        for colour in [(80, 60, 200), (40, 120, 200), (150, 60, 170), (60, 90, 220), (120, 50, 160)]:
            radius = rnd.randint(150, 260)
            bg.blit(glow(radius, colour, 45),
                    (rnd.randint(-50, S.WIDTH - 100), rnd.randint(-50, S.HEIGHT - 100)))
        return bg

    def start_run(self, index):
        self.score = 0
        self.lives = S.STARTING_LIVES
        self.load_level(index)

    def load_level(self, index):
        self.level_index = index
        self.level = Level(LV.LEVELS[index])
        self.static = self.level.render_static()
        sx, sy = self.level.spawn
        self.body = Body(sx, sy, 1)
        self.cp = (sx, sy, 1)
        self.level_start_score = self.score
        self.next_life_at = (self.score // S.EXTRA_LIFE_EVERY + 1) * S.EXTRA_LIFE_EVERY
        self.level_deaths = 0
        self.level_frames = 0
        self.dash_frames = self.dash_cd = 0
        self.iframes = 0
        self.jump_buffer = 0
        self.facing = 1
        self.particles = []
        self.banner = 170
        self.message = ("", 0)
        self.state = "PLAYING"

    def restart_level(self):
        self.score = self.level_start_score
        self.load_level(self.level_index)

    def add_score(self, amount):
        self.score += amount
        while self.score >= self.next_life_at:
            if self.lives < S.MAX_LIVES:
                self.lives += 1
                self.message = ("EXTRA LIFE!", 120)
                self.sound.play("checkpoint")
            self.next_life_at += S.EXTRA_LIFE_EVERY

    def finish_run(self):
        if self.score > self.save["best_score"]:
            self.save["best_score"] = self.score
            self.new_best = True
            write_save(self.save)
        else:
            self.new_best = False

    # ---------------------------------------------------------- effects
    def burst(self, x, y, colour, n=12, speed=3.0, life=30, grav=0.1, size=3):
        for _ in range(n):
            ang = random.random() * math.tau
            sp = random.random() * speed
            self.particles.append([x, y, math.cos(ang) * sp, math.sin(ang) * sp,
                                   life, life, colour, size, grav])

    def update_particles(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += p[8]
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        self.shake *= 0.85
        if self.shake < 0.3:
            self.shake = 0
        if self.message[1] > 0:
            self.message = (self.message[0], self.message[1] - 1)

    # ---------------------------------------------------------- input
    def on_keydown(self, key):
        if key == pygame.K_n:
            self.sound.enabled = not self.sound.enabled
            return
        handler = getattr(self, "keys_" + self.state.lower())
        handler(key)

    def on_keyup(self, key):
        if self.state == "PLAYING" and key in JUMP_KEYS:
            b = self.body
            if b.vy * b.g < 0:
                b.vy *= S.JUMP_CUT

    def keys_menu(self, key):
        n = 5
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_idx = (self.menu_idx - 1) % n
            self.sound.play("select")
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_idx = (self.menu_idx + 1) % n
            self.sound.play("select")
        elif key == pygame.K_h:
            self.state = "HELP"
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.sound.play("select")
            if self.menu_idx == 0:
                self.start_run(0)
            elif self.menu_idx == 1:
                self.select_idx = min(self.save["unlocked"] - 1, NUM_LEVELS - 1)
                self.state = "SELECT"
            elif self.menu_idx == 2:
                self.state = "HELP"
            elif self.menu_idx == 3:
                self.sound.enabled = not self.sound.enabled
            elif self.menu_idx == 4:
                self.quit()

    def keys_help(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
            self.state = "MENU"

    def keys_select(self, key):
        i = self.select_idx
        if key in (pygame.K_LEFT, pygame.K_a):
            i = (i - 1) % NUM_LEVELS
        elif key in (pygame.K_RIGHT, pygame.K_d):
            i = (i + 1) % NUM_LEVELS
        elif key in (pygame.K_UP, pygame.K_w):
            i = (i - 4) % NUM_LEVELS
        elif key in (pygame.K_DOWN, pygame.K_s):
            i = (i + 4) % NUM_LEVELS
        elif key == pygame.K_ESCAPE:
            self.state = "MENU"
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if i < self.save["unlocked"]:
                self.sound.play("select")
                self.start_run(i)
            return
        if i != self.select_idx:
            self.select_idx = i
            self.sound.play("select")

    def keys_playing(self, key):
        if key == pygame.K_ESCAPE:
            self.state = "PAUSED"
        elif key in JUMP_KEYS:
            self.jump_buffer = S.JUMP_BUFFER_FRAMES
        elif key in DASH_KEYS:
            if self.dash_cd <= 0 and self.dash_frames <= 0:
                self.dash_frames = S.DASH_DURATION
                self.dash_cd = S.DASH_COOLDOWN
                self.sound.play("dash")
        elif key == pygame.K_r:
            self.restart_level()

    def keys_paused(self, key):
        if key == pygame.K_ESCAPE:
            self.state = "PLAYING"
        elif key == pygame.K_r:
            self.restart_level()
        elif key == pygame.K_m:
            self.state = "MENU"

    def keys_level_complete(self, key):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.load_level(self.level_index + 1)
        elif key == pygame.K_m:
            self.state = "MENU"

    def keys_game_over(self, key):
        if key == pygame.K_r:
            self.lives = S.STARTING_LIVES
            self.restart_level()
        elif key == pygame.K_m:
            self.state = "MENU"

    def keys_victory(self, key):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.start_run(0)
        elif key == pygame.K_m:
            self.state = "MENU"

    # ---------------------------------------------------------- gameplay
    def update_play(self, keys):
        L = self.level
        b = self.body
        self.level_frames += 1
        if self.banner > 0:
            self.banner -= 1
        if self.iframes > 0:
            self.iframes -= 1
        if self.dash_cd > 0:
            self.dash_cd -= 1

        move = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - \
               (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        self.moving = move != 0
        if move:
            self.facing = move

        # moving platforms (carry or push the player)
        for m in L.movers:
            ox, oy = m.rect.x, m.rect.y
            m.update()
            ddx, ddy = m.rect.x - ox, m.rect.y - oy
            if ddx or ddy:
                if b.support is m and b.on_ground:
                    b.move_x(L, ddx)
                    b.y += ddy
                elif hit(b.x, b.y, PW, PH, m.rect):
                    if ddx:
                        b.x = m.rect.right if ddx > 0 else m.rect.left - PW
                    elif ddy < 0:
                        b.y = m.rect.top - PH
                    else:
                        b.y = m.rect.bottom

        for cr in L.crumbles:
            if cr.update(b):
                self.sound.play("crumble")
                self.burst(cr.rect.centerx, cr.rect.centery, (150, 120, 110), 14, 2.5, 35, 0.25, 4)
        for e in L.enemies:
            if e.alive:
                e.update(L, self.t)

        # movement
        if self.dash_frames > 0:
            self.dash_frames -= 1
            b.move_x(L, self.facing * S.DASH_SPEED)
            b.vy = 0.0
            self.burst(b.x + PW / 2, b.y + PH / 2, S.CYAN, 2, 0.5, 14, 0, 6)
        else:
            if b.step(L, move, self.jump_buffer > 0):
                self.jump_buffer = 0
                self.sound.play("jump")
                self.burst(b.x + PW / 2, b.y + (PH if b.g > 0 else 0), S.WHITE, 5, 1.5, 16, 0.05, 2)
        if self.jump_buffer > 0:
            self.jump_buffer -= 1

        if b.on_ground and isinstance(b.support, Crumble):
            b.support.trigger()

        for event in b.triggers(L):
            self.sound.play(event)
            colour = S.GREEN if event == "pad" else S.PURPLE
            self.burst(b.x + PW / 2, b.y + PH / 2, colour, 18, 4, 30, 0.02, 3)
            if event == "flip":
                self.shake = max(self.shake, 4)

        self.interact()

    def interact(self):
        L = self.level
        b = self.body
        box = pygame.Rect(int(b.x) + 4, int(b.y) + 3, PW - 8, PH - 6)

        if b.y > S.HEIGHT + 30 or (b.g < 0 and b.y + PH < -30):
            self.kill(force=True)
            return

        if self.iframes <= 0:
            for h in L.hazards:
                if box.colliderect(h):
                    self.kill()
                    return

        for e in L.enemies:
            if not e.alive or not box.colliderect(e.rect):
                continue
            er = e.rect
            falling = b.vy * b.g > 1
            if b.g > 0:
                from_above = (b.y + PH) - er.top < 22
            else:
                from_above = er.bottom - b.y < 22
            if self.dash_frames > 0:
                self.defeat(e, bounce=False)
            elif falling and from_above:
                self.defeat(e, bounce=True)
            elif self.iframes <= 0:
                self.kill()
                return

        for orb in L.orbs:
            if not orb["got"] and box.colliderect(pygame.Rect(orb["x"] - 11, orb["y"] - 11, 22, 22)):
                orb["got"] = True
                self.add_score(S.ORB_VALUE)
                self.sound.play("collect")
                self.burst(orb["x"], orb["y"], S.YELLOW, 14, 3, 26, 0.03, 3)

        for cp in L.checkpoints:
            if not cp["active"] and box.colliderect(cp["rect"]):
                for other in L.checkpoints:
                    other["active"] = False
                cp["active"] = True
                x = cp["rect"].centerx - PW / 2
                y = cp["rect"].bottom - PH if b.g > 0 else cp["rect"].top
                self.cp = (x, y, b.g)
                self.sound.play("checkpoint")
                self.burst(cp["rect"].centerx, cp["rect"].centery, S.GREEN, 20, 3, 30, 0.02, 3)
                self.message = ("CHECKPOINT", 90)

        if box.colliderect(L.exit_rect):
            if L.orbs_left() == 0:
                self.complete_level()
            elif self.message[0] != "COLLECT ALL ENERGY ORBS" or self.message[1] < 30:
                self.message = ("COLLECT ALL ENERGY ORBS", 120)

    def defeat(self, enemy, bounce):
        enemy.alive = False
        self.add_score(S.ENEMY_VALUE)
        self.sound.play("stomp")
        self.shake = max(self.shake, 5)
        self.burst(enemy.rect.centerx, enemy.rect.centery, S.ORANGE, 18, 4, 30, 0.12, 3)
        if bounce:
            b = self.body
            b.vy = S.JUMP_STRENGTH * 0.7 * b.g
            b.on_ground = False
            b.coyote = 0

    def kill(self, force=False):
        if self.iframes > 0 and not force:
            return
        b = self.body
        self.lives -= 1
        self.level_deaths += 1
        self.sound.play("death")
        self.shake = 14
        self.burst(b.x + PW / 2, b.y + PH / 2, S.CYAN, 26, 5, 40, 0.15, 3)
        self.burst(b.x + PW / 2, b.y + PH / 2, S.RED, 12, 4, 30, 0.15, 3)
        if self.lives <= 0:
            self.state = "GAME_OVER"
            self.finish_run()
        else:
            x, y, g = self.cp
            self.body = Body(x, y, g)
            self.dash_frames = self.dash_cd = 0
            self.jump_buffer = 0
            self.iframes = S.INVULN_FRAMES

    def complete_level(self):
        d = self.level_deaths
        self.last_stars = 3 if d == 0 else (2 if d <= 2 else 1)
        i = self.level_index
        self.save["stars"][i] = max(self.save["stars"][i], self.last_stars)
        self.save["unlocked"] = max(self.save["unlocked"], min(NUM_LEVELS, i + 2))
        write_save(self.save)
        self.sound.play("portal")
        self.burst(*self.level.exit_rect.center, S.CYAN, 40, 6, 50, 0.05, 3)
        if i >= NUM_LEVELS - 1:
            self.finish_run()
            self.state = "VICTORY"
            self.sound.play("win")
        else:
            self.state = "LEVEL_COMPLETE"

    # ---------------------------------------------------------- drawing
    def draw_background(self, surf):
        surf.blit(self.bg, (0, 0))
        for s in self.stars:
            x, y, size, ph = s
            x = (x - self.t * 0.12 * size) % S.WIDTH
            br = max(60, min(235, 140 + int(80 * math.sin(self.t / 40 + ph))))
            pygame.draw.circle(surf, (br, br, min(255, br + 20)), (int(x), y), size)

    def draw_world(self, surf):
        L = self.level
        t = self.t
        self.draw_background(surf)
        surf.blit(self.static, (0, 0))

        for cr in L.crumbles:
            if cr.state == 2:
                continue
            r = cr.rect.copy()
            if cr.state == 1:
                r.x += random.randint(-2, 2)
                r.y += random.randint(-1, 1)
            pygame.draw.rect(surf, (92, 70, 64), r)
            pygame.draw.rect(surf, (60, 46, 46), r.inflate(-8, -8), 1)
            pygame.draw.line(surf, S.ORANGE, (r.x, r.y + 1), (r.right - 1, r.y + 1), 3)
            pygame.draw.lines(surf, (50, 36, 36), False,
                              [(r.x + 8, r.y + 8), (r.x + 18, r.y + 20), (r.x + 14, r.y + 32)], 2)

        for m in L.movers:
            r = m.rect
            surf.blit(glow(40, S.CYAN, 35), (r.centerx - 40, r.centery - 40))
            pygame.draw.rect(surf, (62, 80, 118), r, border_radius=4)
            pygame.draw.line(surf, (130, 245, 255), (r.x + 2, r.y + 1), (r.right - 3, r.y + 1), 3)
            for k in range(r.x + 10, r.right - 6, 20):
                pygame.draw.circle(surf, S.CYAN, (k, r.y + 9), 2)

        for pad in L.pads:
            draw_pad(surf, pad, t)
        for ring in L.switches:
            draw_switch(surf, ring, t)
        for cp in L.checkpoints:
            draw_checkpoint(surf, cp["rect"], cp["active"], t)
        for orb in L.orbs:
            if not orb["got"]:
                draw_orb(surf, orb["x"], orb["y"], t, orb["phase"])
        draw_portal(surf, L.exit_rect, L.orbs_left() == 0, t)

        for e in L.enemies:
            if e.alive:
                (draw_walker if isinstance(e, Walker) else draw_flyer)(surf, e, t)

        for p in self.particles:
            f = p[4] / p[5]
            col = tuple(int(c * f) for c in p[6])
            pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), max(1, int(p[7] * f)))

        if self.state != "GAME_OVER":
            self.draw_player(surf)

    def draw_player(self, surf):
        b = self.body
        if self.iframes > 0 and (self.t // 4) % 2 == 0:
            return
        ps = pygame.Surface((PW + 10, PH + 10), pygame.SRCALPHA)
        ox, oy = 5, 5
        body = pygame.Rect(ox, oy, PW, PH - 5)
        pygame.draw.rect(ps, S.CYAN, body, border_radius=8)
        pygame.draw.rect(ps, (20, 140, 160), body, 2, border_radius=8)
        vx = ox + PW - 17 if self.facing > 0 else ox + 4
        pygame.draw.rect(ps, S.WHITE, (vx, oy + 7, 13, 10), border_radius=4)
        px = vx + (7 if self.facing > 0 else 2)
        pygame.draw.rect(ps, (30, 60, 90), (px, oy + 10, 4, 4), border_radius=2)
        bx = ox - 4 if self.facing > 0 else ox + PW - 2
        pygame.draw.rect(ps, (20, 140, 160), (bx, oy + 12, 6, 14), border_radius=3)
        running = self.moving and b.on_ground
        lift = (self.t // 5) % 2 if running else 0
        pygame.draw.rect(ps, S.WHITE, (ox + 4, oy + PH - 5, 7, 5 - (2 if lift else 0)))
        pygame.draw.rect(ps, S.WHITE, (ox + PW - 11, oy + PH - 5, 7, 3 + (2 if lift else 0)))
        if b.g < 0:
            ps = pygame.transform.flip(ps, False, True)
        surf.blit(ps, (int(b.x) - 5, int(b.y) - 5))

    def draw_hud(self, surf):
        bar = pygame.Surface((S.WIDTH, 46), pygame.SRCALPHA)
        bar.fill((4, 7, 16, 175))
        surf.blit(bar, (0, 0))
        draw_text(surf, f"ENERGY {self.score}", self.font, S.YELLOW, 16, 14)
        for i in range(S.MAX_LIVES):
            colour = S.RED if i < self.lives else (60, 40, 55)
            draw_heart(surf, 190 + i * 22, 14, colour)
        ready = self.dash_cd <= 0
        draw_text(surf, "DASH", self.small, S.GREEN if ready else S.GREY, 330, 16)
        pygame.draw.rect(surf, (45, 55, 75), (380, 17, 80, 12), border_radius=4)
        fill = 80 if ready else int(80 * (1 - self.dash_cd / S.DASH_COOLDOWN))
        pygame.draw.rect(surf, S.GREEN if ready else S.GREY, (380, 17, fill, 12), border_radius=4)
        draw_text(surf, f"LEVEL {self.level_index + 1}/{NUM_LEVELS}", self.font, S.CYAN,
                  S.WIDTH // 2 + 40, 23, anchor="midleft")
        total = len(self.level.orbs)
        got = total - self.level.orbs_left()
        colour = S.GREEN if got == total else S.WHITE
        draw_text(surf, f"ORBS {got}/{total}", self.font, colour, 720, 14)
        draw_text(surf, format_time(self.level_frames), self.font, S.GREY, S.WIDTH - 16, 23,
                  anchor="midright")

        msg, timer = self.message
        if timer > 0:
            draw_text_alpha(surf, msg, self.mid, S.YELLOW, S.WIDTH // 2, S.HEIGHT - 50,
                            min(1, timer / 25))

        if self.banner > 0:
            a = min(1.0, self.banner / 30, (170 - self.banner) / 20)
            draw_text_alpha(surf, f"LEVEL {self.level_index + 1}", self.mid, S.CYAN,
                            S.WIDTH // 2, 120, a)
            draw_text_alpha(surf, self.level.name, self.big, S.WHITE, S.WIDTH // 2, 170, a)
            draw_text_alpha(surf, self.level.hint, self.font, S.GREY, S.WIDTH // 2, 218, a)

    def dim(self, surf, alpha=170):
        overlay = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surf.blit(overlay, (0, 0))

    def draw_menu(self, surf):
        self.draw_background(surf)
        cx = S.WIDTH // 2
        surf.blit(glow(260, S.CYAN, 40), (cx - 260, 150 - 260 + 60))
        draw_text(surf, "ORBIT", self.title_font, S.WHITE, cx, 110, "center")
        draw_text(surf, "BREAKER", self.title_font, S.CYAN, cx, 200, "center")
        draw_text(surf, "A JOURNEY THROUGH THE UNKNOWN", self.font, S.GREY, cx, 270, "center")
        items = ["START NEW GAME", "LEVEL SELECT", "HOW TO PLAY",
                 f"SOUND: {'ON' if self.sound.enabled else 'OFF'}", "QUIT"]
        for i, label in enumerate(items):
            y = 360 + i * 48
            sel = i == self.menu_idx
            colour = S.CYAN if sel else S.WHITE
            draw_text(surf, label, self.mid, colour, cx, y, "center")
            if sel:
                bob = int(math.sin(self.t * 0.15) * 4)
                pygame.draw.polygon(surf, S.CYAN, [(cx - 170 + bob, y - 10), (cx - 170 + bob, y + 10), (cx - 154 + bob, y)])
                pygame.draw.polygon(surf, S.CYAN, [(cx + 170 - bob, y - 10), (cx + 170 - bob, y + 10), (cx + 154 - bob, y)])
        total_stars = sum(self.save["stars"])
        draw_text(surf, f"BEST ENERGY: {self.save['best_score']}     STARS: {total_stars}/{NUM_LEVELS * 3}",
                  self.small, S.YELLOW, cx, 640, "center")
        draw_text(surf, "UP/DOWN + ENTER      N = SOUND", self.small, S.GREY, cx, 672, "center")

    def draw_help(self, surf):
        self.draw_background(surf)
        draw_text(surf, "HOW TO PLAY", self.big, S.CYAN, S.WIDTH // 2, 70, "center")
        controls = [("A / D  or  ARROWS", "Move"),
                    ("SPACE / W / UP", "Jump (hold = higher)"),
                    ("SHIFT / X", "Dash (smashes drones)"),
                    ("R", "Restart level"),
                    ("ESC", "Pause"),
                    ("N", "Sound on / off")]
        draw_text(surf, "CONTROLS", self.font, S.YELLOW, 60, 130)
        for i, (k, v) in enumerate(controls):
            y = 175 + i * 46
            draw_text(surf, k, self.font, S.WHITE, 60, y)
            draw_text(surf, v, self.small, S.GREY, 60, y + 22)

        draw_text(surf, "THINGS YOU'LL MEET", self.font, S.YELLOW, 470, 130)
        t = self.t
        rows = [("orb", "Collect ALL orbs to open the exit"),
                ("spike", "Spikes cost a life"),
                ("checkpoint", "Checkpoint: respawn here"),
                ("pad", "Spring pad: big bounce"),
                ("switch", "Gravity ring: flips gravity"),
                ("crumble", "Crumbling platform"),
                ("walker", "Drones: stomp or dash them"),
                ("portal", "Exit portal")]
        for i, (icon, label) in enumerate(rows):
            y = 185 + i * 50
            cx, cy = 505, y + 6
            if icon == "orb":
                draw_orb(surf, cx, cy, t)
            elif icon == "spike":
                draw_spike_icon(surf, cx - 20, cy - 20)
            elif icon == "checkpoint":
                draw_checkpoint(surf, pygame.Rect(cx - 12, cy - 20, 24, 40), False, t)
            elif icon == "pad":
                draw_pad(surf, pygame.Rect(cx - 16, cy + 4, 32, 14), t)
            elif icon == "switch":
                draw_switch(surf, pygame.Rect(cx - 16, cy - 16, 32, 32), t)
            elif icon == "crumble":
                r = pygame.Rect(cx - 16, cy - 14, 32, 28)
                pygame.draw.rect(surf, (92, 70, 64), r)
                pygame.draw.line(surf, S.ORANGE, (r.x, r.y + 1), (r.right - 1, r.y + 1), 3)
            elif icon == "walker":
                w = Walker(0, 0)
                w.x, w.y = cx - 14, cy - 14
                w.anim = t
                draw_walker(surf, w, t)
            elif icon == "portal":
                draw_portal(surf, pygame.Rect(cx - 16, cy - 22, 32, 44), True, t)
            draw_text(surf, label, self.small, S.WHITE, 560, y, "midleft" if False else "topleft")
        draw_text(surf, "Stars: 3 = no deaths, 2 = up to two, 1 = more. A bonus life every 100 energy.",
                  self.small, S.GREY, S.WIDTH // 2, 625, "center")
        draw_text(surf, "PRESS ESC TO RETURN", self.font, S.CYAN, S.WIDTH // 2, 670, "center")

    def draw_select(self, surf):
        self.draw_background(surf)
        draw_text(surf, "LEVEL SELECT", self.big, S.CYAN, S.WIDTH // 2, 80, "center")
        cw, ch, gap = 210, 170, 20
        x0 = (S.WIDTH - (4 * cw + 3 * gap)) // 2
        for i in range(NUM_LEVELS):
            col, row = i % 4, i // 4
            r = pygame.Rect(x0 + col * (cw + gap), 150 + row * (ch + gap), cw, ch)
            unlocked = i < self.save["unlocked"]
            sel = i == self.select_idx
            pygame.draw.rect(surf, (24, 32, 54) if unlocked else (16, 20, 32), r, border_radius=12)
            pygame.draw.rect(surf, S.CYAN if sel else (60, 75, 105), r, 4 if sel else 2, border_radius=12)
            if unlocked:
                draw_text(surf, str(i + 1), self.title_font, S.WHITE, r.centerx, r.y + 55, "center")
                draw_text(surf, LV.LEVELS[i]["name"], self.small, S.GREY, r.centerx, r.y + 105, "center", False)
                draw_stars(surf, r.centerx, r.y + 140, self.save["stars"][i], 10, 28)
            else:
                draw_text(surf, "LOCKED", self.font, (90, 100, 125), r.centerx, r.centery, "center", False)
        draw_text(surf, "ARROWS - CHOOSE     ENTER - PLAY     ESC - BACK", self.small, S.GREY,
                  S.WIDTH // 2, 620, "center")

    def draw_level_complete(self, surf):
        self.dim(surf, 150)
        cx = S.WIDTH // 2
        panel = pygame.Rect(0, 0, 560, 380)
        panel.center = (cx, S.HEIGHT // 2)
        pygame.draw.rect(surf, (14, 20, 38), panel, border_radius=16)
        pygame.draw.rect(surf, S.CYAN, panel, 3, border_radius=16)
        draw_text(surf, "LEVEL COMPLETE", self.big, S.GREEN, cx, panel.y + 55, "center")
        draw_text(surf, self.level.name, self.font, S.GREY, cx, panel.y + 100, "center")
        draw_stars(surf, cx, panel.y + 160, self.last_stars, 22, 62)
        draw_text(surf, f"TIME  {format_time(self.level_frames)}      DEATHS  {self.level_deaths}",
                  self.font, S.WHITE, cx, panel.y + 225, "center")
        draw_text(surf, f"ENERGY  {self.score}", self.mid, S.YELLOW, cx, panel.y + 270, "center")
        draw_text(surf, "ENTER - NEXT LEVEL", self.font, S.CYAN, cx, panel.y + 325, "center")
        draw_text(surf, "M - MENU", self.small, S.GREY, cx, panel.y + 355, "center")

    def draw_pause(self, surf):
        self.dim(surf, 190)
        cx = S.WIDTH // 2
        draw_text(surf, "PAUSED", self.title_font, S.WHITE, cx, 270, "center")
        draw_text(surf, "ESC - RESUME", self.font, S.CYAN, cx, 370, "center")
        draw_text(surf, "R - RESTART LEVEL", self.font, S.WHITE, cx, 410, "center")
        draw_text(surf, "M - MAIN MENU", self.font, S.GREY, cx, 450, "center")

    def draw_game_over(self, surf):
        self.draw_background(surf)
        cx = S.WIDTH // 2
        draw_text(surf, "MISSION FAILED", self.title_font, S.RED, cx, 240, "center")
        draw_text(surf, f"FINAL ENERGY: {self.score}", self.big, S.WHITE, cx, 345, "center")
        if self.new_best:
            draw_text(surf, "NEW BEST!", self.mid, S.YELLOW, cx, 400, "center")
        draw_text(surf, "R - TRY THIS LEVEL AGAIN", self.font, S.CYAN, cx, 470, "center")
        draw_text(surf, "M - MAIN MENU", self.font, S.WHITE, cx, 515, "center")

    def draw_victory(self, surf):
        self.draw_background(surf)
        cx = S.WIDTH // 2
        surf.blit(glow(300, S.GREEN, 40), (cx - 300, 250 - 300))
        draw_text(surf, "MISSION COMPLETE", self.title_font, S.GREEN, cx, 180, "center")
        draw_text(surf, "YOU ESCAPED THE FINAL FRONTIER", self.mid, S.WHITE, cx, 265, "center")
        draw_text(surf, f"FINAL ENERGY: {self.score}", self.big, S.YELLOW, cx, 345, "center")
        if self.new_best:
            draw_text(surf, "NEW BEST!", self.mid, S.CYAN, cx, 395, "center")
        total = sum(self.save["stars"])
        draw_text(surf, f"STARS COLLECTED: {total}/{NUM_LEVELS * 3}", self.font, S.WHITE, cx, 445, "center")
        draw_text(surf, "ENTER - PLAY AGAIN", self.font, S.CYAN, cx, 520, "center")
        draw_text(surf, "M - MAIN MENU", self.font, S.WHITE, cx, 560, "center")

    def draw(self):
        st = self.state
        surf = self.canvas
        if st == "MENU":
            self.draw_menu(surf)
        elif st == "HELP":
            self.draw_help(surf)
        elif st == "SELECT":
            self.draw_select(surf)
        elif st == "GAME_OVER":
            self.draw_game_over(surf)
        elif st == "VICTORY":
            self.draw_victory(surf)
        else:
            self.draw_world(surf)
            self.draw_hud(surf)
            if st == "PAUSED":
                self.draw_pause(surf)
            elif st == "LEVEL_COMPLETE":
                self.draw_level_complete(surf)

        ox = oy = 0
        if self.shake:
            ox = random.randint(-int(self.shake), int(self.shake))
            oy = random.randint(-int(self.shake), int(self.shake))
        self.screen.fill((0, 0, 0))
        self.screen.blit(surf, (ox, oy))
        pygame.display.flip()

    # ---------------------------------------------------------- main loop
    def quit(self):
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            self.clock.tick(S.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.KEYDOWN:
                    self.on_keydown(event.key)
                elif event.type == pygame.KEYUP:
                    self.on_keyup(event.key)
            self.t += 1
            if self.state == "PLAYING":
                self.update_play(pygame.key.get_pressed())
            self.update_particles()
            self.draw()


if __name__ == "__main__":
    Game().run()
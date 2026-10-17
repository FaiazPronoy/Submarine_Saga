# Submarine Saga
# Copyright (c) 2024-2026 Faiaz Abrar Zaman Pronoy and Sinthia Khandoker.
# All rights reserved. See LICENSE. CSE423 Computer Graphics, BRAC University.

__author__ = "Faiaz Abrar Zaman Pronoy, Sinthia Khandoker"
__copyright__ = ("Copyright (c) 2024-2026 Faiaz Abrar Zaman Pronoy and Sinthia Khandoker. "
                 "All rights reserved.")
CREDIT_LINE = "(c) 2024-2026  Faiaz Abrar Zaman Pronoy  &  Sinthia Khandoker  -  All rights reserved"

# OpenGL Imports
import OpenGL
# PyOpenGL asks the driver for an error after every single call by default.
# The game makes a few thousand calls a frame and has none to report, so the
# check is switched off, and it is worth several frames a second.
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Standard Library Imports
import hashlib
import json
import math
import os
import struct
import tempfile
import time
import random
import wave

from math import pi, sin, cos

# Window Dimensions
W_Width, W_Height = 1366, 768

# The world is drawn in these coordinates and stretched to whatever size the
# window happens to be, so the game does not break if the window is resized.
WORLD_L, WORLD_R = -683, 683
WORLD_B, WORLD_T = -384, 384

SURFACE_Y = 230          # where the sky stops and the water starts
SEABED_Y = -300          # top of the sand
FONT = GLUT_BITMAP_HELVETICA_18
FONT_SMALL = GLUT_BITMAP_HELVETICA_12
FONT_BIG = GLUT_BITMAP_TIMES_ROMAN_24

# Game States
STATE_MENU, STATE_PLAY, STATE_ROUND_OVER, STATE_MATCH_OVER, STATE_SINKING = 0, 1, 2, 3, 4
STATE_INTRO = 5
state = STATE_INTRO               # the game opens on the intro, then the title screen
game_over = False
paused = False
restart_game = False
background_update_needed = False
night = False

round_no = 1
ROUNDS_TO_WIN = 2
score = {1: 0, 2: 0}
round_winner = None
match_winner = None
round_over_at = 0.0
announcement = ""
announce_until = 0.0

# Who is playing. On the title screen the first row is one player against
# the computer and the second is two players on one keyboard.
vs_cpu = True
cpu_level = 1                  # EASY, NORMAL or HARD: an index into CPU_LEVELS and
                               # LEVEL_RULES, chosen for both one and two players
menu_choice = 0                # which title screen row is highlighted
MENU_ROWS = 3                  # vs CPU, two players, how to play
show_help = False
help_paused = False            # the help screen paused the game, so closing it resumes
sound_on = True

# Round pacing. A round opens with a short READY so both players can find
# their submarine before anything can hit them, and after SUDDEN_DEATH_AT
# seconds the sea gets busier so no round drags on for ever.
READY_TIME = 1.6
SUDDEN_DEATH_AT = 60.0
round_clock = 0.0              # seconds since GO; negative during READY

# Hit feedback: a hit freezes the action for a blink, and the final hit of a
# round plays out in slow motion.
HITSTOP = 0.07
SLOWMO_TIME = 1.1
SLOWMO_SCALE = 0.35
hitstop = 0.0
slowmo = 0.0
popups = []                    # floating text: [text, x, y, colour, life, max life]

# Timing
start_time1 = time.time()
start_time2 = time.time() + 3
tor_time1 = time.time() - 2          # when each player last fired a light torpedo
tor_time2 = time.time() - 2
heavy_time = {1: time.time() - 9, 2: time.time() - 9}    # ...and a heavy one
decoy_time = {1: time.time() - 20, 2: time.time() - 20}
last_frame = time.time()
last_spawn_time = time.time()
last_spawn_time_shark = time.time()
last_mine_time = time.time()
spawn_interval = 6.0
fps_shown = 0.0
_fps_frames, _fps_clock = 0, time.time()

# Speeds  (now per second, not per key press, so movement is frame rate independent)
speed_rain = 260
SUB_ACCEL = 1900.0        # how hard a submarine pushes
SUB_MAX = 430.0           # top speed
SUB_DRAG = 1.4            # water resistance on an axis you are pushing along
SUB_BRAKE = 4.2           # ...and on one you have let go of, so it settles
TURN_BOOST = 1.7          # extra thrust when pushing against your own motion
DASH_SPEED = 900.0
DASH_TIME = 0.2
DASH_COOLDOWN = 2.0
speed_rad = 0.015
fall_speed = 210

# Aiming. The tube has its own angle, separate from which way the submarine
# is moving: the keys swing it towards the direction they point, at AIM_TURN
# radians a second, and letting go leaves it where it is. So an angle can be
# set, and then held while you stop, dodge or back away.
AIM_TURN = 4.5
# a shot within this angle of the other submarine is nudged onto it, so a
# diagonal shot does not need the keys to land on the exact degree
AIM_ASSIST = math.radians(9)

# Two kinds of torpedo. The light one is quick to reload and runs straight;
# the heavy one takes three times as long, hits three times as hard, turns
# gently towards its target, and its blast still hurts on a near miss.
WEAPONS = {
    # slow enough to see one coming and get out of the way: a light torpedo
    # takes about three seconds to cross the map
    'light': {'speed': 430.0, 'reload': 0.6, 'damage': 1, 'scale': 1.0,
              'turn': 0.0, 'blast': 0},
    'heavy': {'speed': 300.0, 'reload': 3.0, 'damage': 3, 'scale': 1.45,
              'turn': 0.8, 'blast': 80},
}
# What each level plays with. EASY is the plain game, one kind of torpedo;
# NORMAL adds the heavy torpedo, running straight; HARD makes it home and
# blast, and gives both sides the decoy to answer it with.
LEVEL_RULES = [
    {'heavy': False, 'homing': False, 'blast': False, 'decoy': False},   # EASY
    {'heavy': True, 'homing': False, 'blast': False, 'decoy': False},    # NORMAL
    {'heavy': True, 'homing': True, 'blast': True, 'decoy': True},       # HARD
]


LEVEL_NOTES = [
    "Easy:  light torpedoes only, and a calm computer.",
    "Normal:  light torpedoes, and the heavy torpedo (3 damage) on a slow reload.",
    "Hard:  the heavy torpedo homes and blasts, both sides get decoys, and a sharp computer.",
]


def rule(name):
    return LEVEL_RULES[cpu_level][name]


RAPID_FACTOR = 0.5        # rapid fire halves both reloads
LAST_STAND_RELOAD = 0.65

# A decoy is a noise maker left in the water. A heavy torpedo homes on noise,
# so it goes for the decoy instead of the submarine that dropped it.
DECOY_TIME = 4.0
DECOY_COOLDOWN = 9.0

MAX_LIFE = 10
LAST_STAND_AT = 2         # at this much life or less you swim and reload faster
MINE_DAMAGE = 2
BOMB_DAMAGE = 2
SHARK_DAMAGE = 1
HEALTH_PICKUP = 3

# Collision sizes, all measured off the art, so a near miss on screen is a
# near miss in the maths. They live together here rather than at the call
# sites, because they only make sense next to each other.
HULL_R = 25              # the round nose and tail caps, as drawn
TORPEDO_R = 7            # half the width of a light torpedo body
TORPEDO_NOSE = 26        # centre to the tip of the nose
TORPEDO_TAIL = 24        # centre to the end of the fins
                         # (a heavy torpedo is all three times its scale)
BOMB_R = 9
MINE_R = 18
# the shark is drawn 90 long, so it is three circles along its body rather
# than one at the centre that leaves the snout outside its own hit box.
# (offset ahead of the centre, radius)
SHARK_CIRCLES = ((28, 16), (0, 17), (-26, 13))
PICKUP_GRAB = 14         # added to the pickup's own radius
PICKUP_LINGER = 6.0      # a pickup that reaches the bottom waits this long
SHIELD_TIME = 9.0
RAPID_TIME = 6.0
BOOST_TIME = 7.0
IFRAMES = 0.35           # no second hit until the flash has faded
BANNER_GRACE = 0.7       # a result screen ignores input for this long

# Player, Submarines, and Entities
player = None
submarines = []
bubbles = []
torpedo1 = []
torpedo2 = []
rains = []
sharks = []
unique_circles = []
particles = []
fishes = []
mines = []
shake = 0.0
shake_x = 0.0
shake_y = 0.0

# Boat and Bombs
boatx = 80
boaty = 233
bombs = [[-65 + i * 40, boaty + 20] for i in range(4)]
bombN = [True, True, True, True]
theta = random.randrange(-30, 31)
bomb_vx = [theta * 2.4 - 90, theta * 2.4 - 30, theta * 2.4 + 30, theta * 2.4 + 90]
bomb_delay = 0.8

# ------------------------------------------------------------------ palette --
# Two palettes, one for day and one for night. Everything that changes with the
# time of day reads from PAL so there is one place to edit.
DAY = {
    'sky_top': (0.29, 0.60, 0.86), 'sky_bottom': (0.68, 0.85, 0.95),
    'water_top': (0.10, 0.55, 0.80), 'water_bottom': (0.01, 0.10, 0.26),
    'sand': (0.72, 0.62, 0.42), 'sand_dark': (0.50, 0.42, 0.28),
    'cloud': (1.0, 1.0, 1.0), 'ray': (0.65, 0.90, 1.0),
    'weed': (0.13, 0.45, 0.28), 'orb': (1.0, 0.93, 0.6),
    'rain': (0.62, 0.78, 0.92), 'text': (1.0, 1.0, 1.0),
}
NIGHT = {
    'sky_top': (0.03, 0.05, 0.14), 'sky_bottom': (0.10, 0.14, 0.30),
    'water_top': (0.04, 0.15, 0.30), 'water_bottom': (0.01, 0.03, 0.10),
    'sand': (0.30, 0.27, 0.21), 'sand_dark': (0.19, 0.17, 0.13),
    'cloud': (0.42, 0.45, 0.55), 'ray': (0.45, 0.62, 0.80),
    'weed': (0.07, 0.24, 0.16), 'orb': (0.90, 0.92, 1.0),
    'rain': (0.45, 0.55, 0.75), 'text': (0.92, 0.95, 1.0),
}
PAL = dict(DAY)

# each player gets their own hull colour so they can tell themselves apart
TEAM = {
    1: {'hull': (0.11, 0.42, 0.36), 'hull_dark': (0.06, 0.26, 0.23),
        'trim': (0.94, 0.76, 0.25), 'name': 'MARKAVA'},
    2: {'hull': (0.48, 0.16, 0.18), 'hull_dark': (0.30, 0.09, 0.11),
        'trim': (0.98, 0.62, 0.28), 'name': 'DESTROYER'},
}

# Submarine 11
list1 = [[-530, 180], [-630, 180], [-630, 130], [-530, 130]]
list2 = [[-660, 165], [-680, 165], [-680, 145], [-660, 145], [-655, 155]]
list3 = [[-550, 200], [-580, 200], [-610, 180], [-550, 180]]
list4 = [[-560, 215], [-570, 215], [-570, 200], [-560, 200]]
list5 = [[-540, 165], [-560, 165], [-560, 145], [-540, 145]]
list6 = [[-570, 130], [-610, 130], [-610, 115], [-570, 115], [-555, 122.5]]
circle1 = [-580, 155]
circle2 = [-615, 155]

# Submarine 22
list11 = [[530, 180], [630, 180], [630, 130], [530, 130]]
list22 = [[660, 165], [680, 165], [680, 145], [660, 145], [655, 155]]
list33 = [[550, 200], [580, 200], [610, 180], [550, 180]]
list44 = [[560, 215], [570, 215], [570, 200], [560, 200]]
list55 = [[540, 165], [560, 165], [560, 145], [540, 145]]
list66 = [[570, 130], [610, 130], [610, 115], [570, 115], [555, 122.5]]
circle11 = [580, 155]
circle22 = [615, 155]

background_list = None
wreck_list = None


# The part of the window the world is drawn into. The world keeps its own
# shape at any window size, with black bars on whichever sides are left over,
# so a circle stays a circle when the window is maximised. PIXEL_SCALE is
# window pixels per world unit, which every point size is multiplied by.
VIEW_X, VIEW_Y, VIEW_W, VIEW_H = 0, 0, W_Width, W_Height
PIXEL_SCALE = 1.0


def fit_viewport(width, height):
    """Viewport mapping: the largest rectangle of the world's aspect ratio that
    fits the window, centred in it."""
    global VIEW_X, VIEW_Y, VIEW_W, VIEW_H, PIXEL_SCALE
    world_w, world_h = WORLD_R - WORLD_L, WORLD_T - WORLD_B
    PIXEL_SCALE = min(width / world_w, height / world_h)
    VIEW_W = max(1, int(round(world_w * PIXEL_SCALE)))
    VIEW_H = max(1, int(round(world_h * PIXEL_SCALE)))
    VIEW_X = (width - VIEW_W) // 2
    VIEW_Y = (height - VIEW_H) // 2


def convert_coordinate(x, y):
    """Window pixels to world units, with the screen shake taken into account.

    GLUT counts y down from the top of the window and OpenGL up from the
    bottom, and the world only fills the viewport, not the whole window.
    """
    top = W_Height - (VIEW_Y + VIEW_H)
    return (((x - VIEW_X) / VIEW_W) * (WORLD_R - WORLD_L) + WORLD_L + shake_x,
            WORLD_T - ((y - top) / VIEW_H) * (WORLD_T - WORLD_B) + shake_y)


def point_px(size):
    """A point size in world units, as window pixels.

    Fills are rows of points `size` units apart, so at any window size the
    points have to grow with the world or the gaps between them show as a
    grid. Rounded up, so neighbours always meet.
    """
    return max(1.0, math.ceil(size * PIXEL_SCALE - 1e-6))


# ====================================================================== #
#  Point batching
#
#  Everything on screen is drawn with glBegin(GL_POINTS) and glVertex2f,
#  through the midpoint algorithms below. The original opened and closed a
#  glBegin/glEnd block for every single point, which held the game at about
#  12 frames a second. Points are now collected into runs of the same colour
#  and size, and each run is one glBegin/glEnd. The drawing order is kept
#  exactly, so what ends up on screen is identical.
# ====================================================================== #

_cur_color = (1.0, 1.0, 1.0)
_runs = []
_compiling = False          # True while a display list is being recorded


def set_color(c):
    global _cur_color
    _cur_color = (c[0], c[1], c[2])


def draw_points_batch(points, size):
    """Adds to the run in progress when the colour and size match.

    A chunk is either a plain list of (x, y), or a Placed shape: a shape
    rasterised once and the offset it is to be drawn at.
    """
    if points is None or len(points) == 0:
        return
    if _runs and _runs[-1][0] == _cur_color and _runs[-1][1] == size:
        _runs[-1][2].append(points)
    else:
        _runs.append([_cur_color, size, [points]])


def emit_points(points):
    """The one place a vertex is sent: glBegin(GL_POINTS), glVertex2f, glEnd."""
    glBegin(GL_POINTS)
    for x, y in points:
        glVertex2f(x, y)
    glEnd()


def flush_points():
    """
    Sends every collected run to OpenGL, in the order it was drawn.

    Loose points go out as glVertex2f calls between glBegin(GL_POINTS) and
    glEnd. A Placed shape goes out as its display list - the same glBegin,
    glVertex2f and glEnd, recorded the first time the shape was drawn -
    with glTranslatef moving it into place. That is what keeps the frame
    rate: a Python call per vertex costs about a microsecond, and a frame
    has tens of thousands of points, most of them in shapes that were drawn
    the frame before as well.
    """
    for color, size, chunks in _runs:
        glColor3f(color[0], color[1], color[2])
        glPointSize(point_px(size))
        loose = []
        for chunk in chunks:
            if isinstance(chunk, Placed):
                list_id = 0 if _compiling else shape_list(chunk.shape)
                if list_id:
                    if loose:
                        emit_points(loose)
                        loose = []
                    glTranslatef(chunk.tx, chunk.ty, 0.0)
                    glCallList(list_id)
                    glLoadIdentity()
                else:
                    # recording a display list: a list cannot be built inside
                    # another, so the shape's points are written out in place
                    loose.extend((x + chunk.tx, y + chunk.ty) for x, y in chunk.shape.points)
            else:
                loose.extend(chunk)
        if loose:
            emit_points(loose)
    _runs.clear()


# ---------------------------------------------------------- translation --
# A shape is rasterised once, relative to its own origin, and kept. Drawing it
# somewhere else is then a translation by (tx, ty), which is far cheaper than
# running the scanline or the midpoint algorithm again every frame.

class Shape:
    """A point set relative to its own origin, and the display list that
    draws it once it has been drawn."""
    __slots__ = ('points', 'list_id')

    def __init__(self, points):
        self.points = points
        self.list_id = None

    def __len__(self):
        return len(self.points)

    def __iter__(self):
        return iter(self.points)


class Placed:
    """A shape and where to draw it."""
    __slots__ = ('shape', 'tx', 'ty')

    def __init__(self, shape, tx, ty):
        self.shape, self.tx, self.ty = shape, tx, ty

    def __len__(self):
        return len(self.shape.points)

    def __iter__(self):
        return ((x + self.tx, y + self.ty) for x, y in self.shape.points)


def translate(rel, tx, ty):
    return Placed(rel, tx, ty)


def shape_list(shape):
    """The shape's display list, recorded with glVertex2f the first time."""
    if shape.list_id is None:
        list_id = glGenLists(1)
        if not list_id:
            return 0
        glNewList(list_id, GL_COMPILE)
        emit_points(shape.points)
        glEndList()
        shape.list_id = list_id
    return shape.list_id


_shape_cache = {}


def cached_shape(key, build):
    """build() is only called the first time a key is seen."""
    shape = _shape_cache.get(key)
    if shape is None:
        if len(_shape_cache) > 6000:
            # a hull turning as it sinks makes a new key every frame
            for old in _shape_cache.values():
                if old.list_id:
                    glDeleteLists(old.list_id, 1)
                    old.list_id = None
            _shape_cache.clear()
        shape = Shape([(float(x), float(y)) for x, y in build()])
        _shape_cache[key] = shape
    return shape


##---------------------Midpoint Line Algorithm---------------------------#
def MidPointLine(x1, y1, x2, y2):
    points = []
    dx = x2 - x1
    dy = y2 - y1
    d = 2 * dy - dx
    incE = 2 * dy
    incNE = 2 * dy - 2 * dx
    x = int(x1)
    y = int(y1)
    for i in range(x, int(x2) + 1):
        points.append([i, y])
        if d > 0:
            d += incNE
            y += 1
        else:
            d += incE
    return points


def findZone(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    if dx > 0 and dy >= 0:
        return 0 if abs(dx) > abs(dy) else 1
    elif dx <= 0 and dy >= 0:
        return 3 if abs(dx) > abs(dy) else 2
    elif dx < 0 and dy < 0:
        return 4 if abs(dx) > abs(dy) else 5
    elif dx >= 0 and dy < 0:
        return 7 if abs(dx) > abs(dy) else 6
    return 0


def convertToZone0(zone, x1, y1, x2, y2):
    if zone == 1:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
    elif zone == 2:
        x1, y1 = y1, -x1
        x2, y2 = y2, -x2
    elif zone == 3:
        x1, y1 = -x1, y1
        x2, y2 = -x2, y2
    elif zone == 4:
        x1, y1 = -x1, -y1
        x2, y2 = -x2, -y2
    elif zone == 5:
        x1, y1 = -y1, -x1
        x2, y2 = -y2, -x2
    elif zone == 6:
        x1, y1 = -y1, x1
        x2, y2 = -y2, x2
    elif zone == 7:
        x1, y1 = x1, -y1
        x2, y2 = x2, -y2
    return x1, y1, x2, y2


def convertToZoneM(zone, points):
    """Takes the zone 0 points back to the zone the line really lives in."""
    if zone == 0:
        out = [(x, y) for x, y in points]
    elif zone == 1:
        out = [(y, x) for x, y in points]
    elif zone == 2:
        out = [(-y, x) for x, y in points]
    elif zone == 3:
        out = [(-x, y) for x, y in points]
    elif zone == 4:
        out = [(-x, -y) for x, y in points]
    elif zone == 5:
        out = [(-y, -x) for x, y in points]
    elif zone == 6:
        out = [(y, -x) for x, y in points]
    else:
        out = [(x, -y) for x, y in points]
    return out


#=========================================================================#

#---------------Midpoint Circle Algorithm---------------------------#

def MidPointCircle(rad):
    zone0 = []
    d_init = 1 - rad
    x_temp = 0
    # <= not <, so the octant emits its 45 degree pixel. With < the point
    # where x meets y is never plotted and every hollow circle ends up with
    # eight notches on its diagonals.
    while x_temp <= rad:
        if d_init >= 0:
            d_init = d_init + 2 * x_temp - 2 * rad + 5
            zone0.append((x_temp, rad))
            x_temp += 1
            rad -= 1
        else:
            d_init = d_init + 2 * x_temp + 3
            zone0.append((x_temp, rad))
            x_temp += 1
    return zone0


# The same radius comes up again and again every frame, so the result of the
# algorithm above is kept rather than recomputed.
_circle_cache = {}


def circle_points(rad):
    rad = int(rad)
    if rad < 1:
        rad = 1
    pts = _circle_cache.get(rad)
    if pts is None:
        pts = MidPointCircle(rad)
        _circle_cache[rad] = pts
    return pts


def zone_converter(x, y, arr):
    all_points = [[], [], [], [], [], [], [], []]
    for m in arr:
        all_points[0].append((m[1] + x, m[0] + y))
        all_points[1].append((m[0] + x, m[1] + y))
        all_points[2].append((-m[0] + x, m[1] + y))
        all_points[3].append((-m[1] + x, m[0] + y))
        all_points[4].append((-m[1] + x, -m[0] + y))
        all_points[5].append((-m[0] + x, -m[1] + y))
        all_points[6].append((m[0] + x, -m[1] + y))
        all_points[7].append((m[1] + x, -m[0] + y))
    return all_points


_disc_cache = {}


def disc_points(rad):
    """Every point inside a circle of this radius, relative to its centre."""
    rad = int(rad)
    if rad < 1:
        rad = 1
    pts = _disc_cache.get(rad)
    if pts is not None:
        return pts
    pts = []
    xi, yi = 0, rad
    p = 1 - rad
    seen = set()
    while xi <= yi:
        for dx in range(-xi, xi + 1):
            seen.add((dx, yi))
            seen.add((dx, -yi))
        for dx in range(-yi, yi + 1):
            seen.add((dx, xi))
            seen.add((dx, -xi))
        xi += 1
        if p < 0:
            p += 2 * xi + 1
        else:
            yi -= 1
            p += 2 * (xi - yi) + 1
    pts = list(seen)
    _disc_cache[rad] = pts
    return pts


def filled_circle_helper(x, y, rad, color):
    set_color(color)
    draw_points_batch(translate(cached_shape(('disc', int(rad)), lambda: disc_points(rad)),
                                int(x), int(y)), 2)


def line_points(x1, y1, x2, y2):
    """Midpoint line between two integer points, through the zone conversion."""
    zone = findZone(x1, y1, x2, y2)
    a, b, c, d = convertToZone0(zone, x1, y1, x2, y2)
    return convertToZoneM(zone, MidPointLine(a, b, c, d))


def draw_lines(color, x1, y1, x2, y2, s=2):
    # the line is rasterised from the origin to (dx, dy) and then translated,
    # so the same slope drawn anywhere on screen is only computed once
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    dx, dy = x2 - x1, y2 - y1
    rel = cached_shape(('line', dx, dy), lambda: line_points(0, 0, dx, dy))
    set_color(color)
    draw_points_batch(translate(rel, x1, y1), s)


def ring_points(rad):
    """The eight octants of the midpoint circle, as one point set."""
    return [p for group in zone_converter(0, 0, circle_points(rad)) for p in group]


def draw_filled_circle(x, y, rad, color):
    rad = int(rad)
    rel = cached_shape(('fdisc', rad),
                       lambda: list(set(disc_points(rad)) | set(ring_points(rad))))
    set_color(color)
    draw_points_batch(translate(rel, int(x), int(y)), 2)


def draw_hollow_circle(x, y, rad, color, s=2):
    rad = int(rad)
    set_color(color)
    draw_points_batch(translate(cached_shape(('ring', rad), lambda: ring_points(rad)),
                                int(x), int(y)), s)


def draw_arc(x, y, rad, color, octants, s=2):
    """Only some of the eight octants of a circle - half a circle is four."""
    rad = int(rad)
    key = ('arc', rad, tuple(octants))
    rel = cached_shape(key, lambda: [p for i, group in
                                     enumerate(zone_converter(0, 0, circle_points(rad)))
                                     if i in octants for p in group])
    set_color(color)
    draw_points_batch(translate(rel, int(x), int(y)), s)


def draw_outline(color, vertices, s=2):
    """Outline of a polygon, drawn edge by edge with the midpoint line."""
    for i in range(len(vertices)):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % len(vertices)]
        draw_lines(color, x1, y1, x2, y2, s)


def scanline_points(vertices, step):
    """
    The scanline fill itself: for every row, find where the edges cross it,
    sort the crossings and fill between each pair (the even-odd rule).
    """
    ys = [v[1] for v in vertices]
    y_lo, y_hi = int(min(ys)), int(max(ys))
    pts = []
    n = len(vertices)
    for y in range(y_lo, y_hi + 1, step):
        crossings = []
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            if y1 == y2:
                continue
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                crossings.append(x1 + t * (x2 - x1))
        crossings.sort()
        for i in range(0, len(crossings) - 1, 2):
            xa, xb = int(crossings[i]), int(crossings[i + 1])
            for x in range(xa, xb + 1, step):
                pts.append((x, y))
    return pts


def fill_polygon(color, vertices, step=2):
    """
    Solid fill for a polygon, by scanline.

    The original only ever drew the outline of the submarine and called it
    filled, which is why the hulls looked like wireframes. Each scanline still
    ends up as a run of GL_POINTS. The fill is worked out relative to the
    first vertex and translated into place, so a hull that is only moving is
    filled once rather than every frame.
    """
    if len(vertices) < 3:
        return
    ox, oy = int(vertices[0][0]), int(vertices[0][1])
    rel = tuple((int(round(v[0] - ox)), int(round(v[1] - oy))) for v in vertices)
    pts = cached_shape(('poly', rel, step), lambda: scanline_points(rel, step))
    set_color(color)
    draw_points_batch(translate(pts, ox, oy), step)


def fill_rectangle(color, x_min, y_min, x_max, y_max, step=3):
    w, h = int(x_max) - int(x_min), int(y_max) - int(y_min)
    rel = cached_shape(('rect', w, h, step),
                       lambda: [(x, y) for y in range(0, h + 1, step)
                                for x in range(0, w + 1, step)])
    set_color(color)
    draw_points_batch(translate(rel, int(x_min), int(y_min)), step)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def fill_gradient(x_min, y_min, x_max, y_max, top_color, bottom_color, step=8):
    """
    A vertical gradient, one band of points per step.

    Each band is one run of large points. A finer step looks no different on
    screen and costs several times as much to draw.
    """
    span = max(1.0, y_max - y_min)
    xs = list(range(int(x_min), int(x_max) + 1, step))
    for y in range(int(y_min), int(y_max) + 1, step):
        t = (y - y_min) / span
        set_color(mix(bottom_color, top_color, t))
        draw_points_batch([(x, y) for x in xs], step + 1)


class AABB:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


def has_collided(box1, box2):
    return (box1.x < box2.x + box2.width and
            box1.x + box1.width > box2.x and
            box1.y < box2.y + box2.height and
            box1.y + box1.height > box2.y)


# ---------------------------------------------------------- geometry --
# The collision tests below work on the same polygons and circles the hulls
# are drawn from, so the edge of what you can see is the edge of what can be
# hit - not a box drawn loosely round it.

def seg_dist(ax, ay, bx, by, px, py):
    """Shortest distance from a point to the segment (ax,ay)-(bx,by).

    Torpedoes are checked against the path they covered this frame, not the
    point they ended on. One moves 50 units in a frame at 20fps and the radii
    involved are half that, so a test on the end point alone steps clean over
    whatever it should have hit.
    """
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _cross(ox, oy, ax, ay, bx, by):
    return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)


def segments_cross(ax, ay, bx, by, cx, cy, dx, dy):
    """True when segment AB and segment CD share a point."""
    d1 = _cross(cx, cy, dx, dy, ax, ay)
    d2 = _cross(cx, cy, dx, dy, bx, by)
    d3 = _cross(ax, ay, bx, by, cx, cy)
    d4 = _cross(ax, ay, bx, by, dx, dy)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return True
    # touching or collinear: fall back to the distances, which cover it
    return (seg_dist(cx, cy, dx, dy, ax, ay) < 1e-9 or seg_dist(cx, cy, dx, dy, bx, by) < 1e-9
            or seg_dist(ax, ay, bx, by, cx, cy) < 1e-9 or seg_dist(ax, ay, bx, by, dx, dy) < 1e-9)


def seg_seg_dist(ax, ay, bx, by, cx, cy, dx, dy):
    if segments_cross(ax, ay, bx, by, cx, cy, dx, dy):
        return 0.0
    return min(seg_dist(cx, cy, dx, dy, ax, ay), seg_dist(cx, cy, dx, dy, bx, by),
               seg_dist(ax, ay, bx, by, cx, cy), seg_dist(ax, ay, bx, by, dx, dy))


def point_in_polygon(px, py, poly):
    """Ray casting: count how many edges a ray to the right of the point crosses."""
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > py) != (y2 > py):
            if px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def seg_polygon_dist(ax, ay, bx, by, poly):
    """Distance from a segment to a filled polygon; 0 when they overlap."""
    if point_in_polygon(ax, ay, poly) or point_in_polygon(bx, by, poly):
        return 0.0
    best = float('inf')
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        best = min(best, seg_seg_dist(ax, ay, bx, by, x1, y1, x2, y2))
        if best == 0.0:
            break
    return best


# ------------------------------------------------ Cohen-Sutherland clipping --
# Each end of a line gets a four bit region code saying which side of the
# clip rectangle it is off. Both codes 0: the line is inside. Codes sharing a
# bit: both ends are off the same side, so the whole line is outside.
# Otherwise one outside end is moved onto the edge it crosses, and the test
# repeats. The sight uses it to clip the line of fire to the water.

CS_INSIDE, CS_LEFT, CS_RIGHT, CS_BOTTOM, CS_TOP = 0, 1, 2, 4, 8


def region_code(x, y, xmin, ymin, xmax, ymax):
    code = CS_INSIDE
    if x < xmin:
        code |= CS_LEFT
    elif x > xmax:
        code |= CS_RIGHT
    if y < ymin:
        code |= CS_BOTTOM
    elif y > ymax:
        code |= CS_TOP
    return code


def cohen_sutherland(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """The part of the line inside the rectangle, or None if there is none."""
    c0 = region_code(x0, y0, xmin, ymin, xmax, ymax)
    c1 = region_code(x1, y1, xmin, ymin, xmax, ymax)
    while True:
        if not (c0 | c1):
            return x0, y0, x1, y1              # trivially accepted
        if c0 & c1:
            return None                        # trivially rejected
        out = c0 if c0 else c1
        if out & CS_TOP:
            x, y = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0), ymax
        elif out & CS_BOTTOM:
            x, y = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0), ymin
        elif out & CS_RIGHT:
            x, y = xmax, y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
        else:
            x, y = xmin, y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
        if out == c0:
            x0, y0 = x, y
            c0 = region_code(x0, y0, xmin, ymin, xmax, ymax)
        else:
            x1, y1 = x, y
            c1 = region_code(x1, y1, xmin, ymin, xmax, ymax)


def rect_poly(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def capsule_hits_shape(shape, ax, ay, bx, by, r):
    """
    Does a capsule - the segment AB grown by r on every side - touch a shape?

    A shape is (box, polygons, circles), where box is its bounding box and is
    only there to throw out the far away cases before the exact test runs.
    A moving round thing sweeps out exactly a capsule over one frame, which is
    why this one test serves every hazard in the game.
    """
    (x0, y0, x1, y1), polys, circles = shape
    if (max(ax, bx) + r < x0 or min(ax, bx) - r > x1 or
            max(ay, by) + r < y0 or min(ay, by) - r > y1):
        return False
    for cx, cy, cr in circles:
        if seg_dist(ax, ay, bx, by, cx, cy) <= r + cr:
            return True
    for poly in polys:
        if seg_polygon_dist(ax, ay, bx, by, poly) <= r:
            return True
    return False


# ====================================================================== #
#  Background: sky, water, seabed, and the things that live in them
# ====================================================================== #

def draw_clouds(color, center, radius):
    pts = []
    x, y = 0, radius
    p = 1 - radius
    while x <= y:
        for dx in range(-x, x + 1, 3):
            pts.append((center[0] + dx, center[1] + y))
            pts.append((center[0] + dx, center[1] - y))
        for dx in range(-y, y + 1, 3):
            pts.append((center[0] + dx, center[1] + x))
            pts.append((center[0] + dx, center[1] - x))
        x += 1
        if p < 0:
            p += 2 * x + 1
        else:
            y -= 1
            p += 2 * (x - y) + 1
    set_color(color)
    draw_points_batch(pts, 3)


STATIC_CLOUDS = [
    (-392, 350, 30), (-410, 337, 25), (-375, 338, 25),
    (239, 314, 35), (215, 305, 25), (260, 305, 25),
    (500, 340, 35), (475, 330, 25), (525, 330, 25),
    (-640, 300, 25), (-615, 293, 19),
]

# Seaweed roots, each with its own height and sway offset so they do not all
# lean the same way.
WEEDS = [(x, random.randint(45, 105), random.uniform(0, 6.28))
         for x in range(-660, 661, 47)]

ROCKS = [(random.randint(-640, 640), random.randint(10, 26)) for _ in range(11)]


def draw_seabed():
    fill_gradient(WORLD_L, WORLD_B, WORLD_R, SEABED_Y,
                  PAL['sand'], PAL['sand_dark'], step=7)
    for rx, rr in ROCKS:
        draw_filled_circle(rx, SEABED_Y - rr // 2, rr, PAL['sand_dark'])
    draw_sand_grain()


SAND_PATTERN = 0xC095436ED22E9A2E   # which grains are lighter (1) or darker (0)
GRAIN_Y = -377                     # the middle of one band of the sand gradient
GRAIN_X0, GRAIN_STEP = -660, 9


def grain_bits():
    return [(SAND_PATTERN >> (63 - k)) & 1 for k in range(64)]


def draw_sand_grain():
    """A row of fine grains along the bottom of the sand, each a shade
    lighter or darker than the sand around it."""
    span = SEABED_Y - WORLD_B
    base = mix(PAL['sand_dark'], PAL['sand'], (GRAIN_Y - WORLD_B) / span)
    d = 6.0 / 255.0
    for i, bit in enumerate(grain_bits()):
        shade = d if bit else -d
        set_color(tuple(max(0.0, min(1.0, c + shade)) for c in base))
        draw_points_batch([(GRAIN_X0 + i * GRAIN_STEP, GRAIN_Y)], 3)


def draw_seaweed(t):
    """Weeds bend with a slow sine, which is what makes the floor feel alive."""
    pts = []
    for base_x, height, phase in WEEDS:
        sway = sin(t * 1.1 + phase) * 14
        for k in range(0, height, 4):
            f = k / height
            pts.append((base_x + sway * f * f, SEABED_Y + k))
    set_color(PAL['weed'])
    draw_points_batch(pts, 5)


def draw_light_rays(t):
    """Shafts of light coming down from the surface. Cheap and very effective."""
    # only a shade lighter than the water behind them, and slanted, so they
    # read as light coming through the surface rather than painted bars.
    # Two passes: a wide faint one, then a narrow brighter one inside it, so
    # the edges fade instead of ending in a hard line. Every shaft is the same
    # shape, so it is built once and translated to where each one sways to.
    for wide in (True, False):
        def build():
            pts = []
            for k in range(0, 290, 6):
                f = k / 290.0
                w = (26 + 34 * f) if wide else (12 + 18 * f)
                pts.extend((k * 0.22 + dx, -k)
                           for dx in range(int(-w / 2), int(w / 2) + 1, 6))
            return pts
        rel = cached_shape(('ray', wide), build)
        set_color(mix(PAL['water_top'], PAL['ray'], 0.05 if wide else 0.11))
        for i in range(5):
            x0 = -520 + i * 260 + sin(t * 0.3 + i * 1.7) * 30
            draw_points_batch(translate(rel, x0, SURFACE_Y), 7)


def draw_sun_moon(t):
    x, y = 285, 318
    if night:
        draw_filled_circle(x, y, 26, PAL['orb'])
        draw_filled_circle(x - 11, y + 7, 22, PAL['sky_top'])
        set_color((1.0, 1.0, 0.92))
        draw_points_batch([(sx, sy) for sx, sy in
                           [(-330, 330), (-250, 300), (-180, 335), (-360, 268),
                            (200, 262), (330, 288), (-290, 245), (185, 332),
                            (245, 250), (355, 330), (-210, 262), (150, 296)]],
                          3 + 2 * (0.5 + 0.5 * sin(t * 2.3)))
    else:
        draw_filled_circle(x, y, 30, PAL['orb'])
        pts = []
        for i in range(12):
            a = t * 0.25 + i * (pi / 6)
            for k in range(38, 51, 3):
                pts.append((x + cos(a) * k, y + sin(a) * k))
        set_color((1.0, 0.88, 0.45))
        draw_points_batch(pts, 4)


def draw_surface(t):
    """A wavy waterline instead of a hard edge between sky and sea."""
    pts = [(x, SURFACE_Y + sin(x * 0.017 + t * 1.7) * 5 + sin(x * 0.005 - t * 0.9) * 3)
           for x in range(WORLD_L, WORLD_R + 1, 4)]
    set_color(mix(PAL['water_top'], (1, 1, 1), 0.55))
    draw_points_batch(pts, 5)


static_list = None


def flush_compiled():
    """flush_points() while a display list is being recorded."""
    global _compiling
    _compiling = True
    try:
        flush_points()
    finally:
        _compiling = False


def create_static_list():
    """
    The HUD panels and the button chrome never move, so they are baked once
    instead of being rebuilt out of points every frame.
    """
    global static_list
    if static_list is not None:
        glDeleteLists(static_list, 1)
    static_list = glGenLists(1)
    if not static_list:
        return
    glNewList(static_list, GL_COMPILE)
    draw_hud_panels()
    draw_button_chrome()
    flush_compiled()
    glEndList()


def create_wreck_list():
    """The wreck never moves either, but it needs its own slot in the draw
    order: behind the submarines, in front of the weeds."""
    global wreck_list
    if wreck_list is not None:
        glDeleteLists(wreck_list, 1)
    wreck_list = glGenLists(1)
    if not wreck_list:
        return
    glNewList(wreck_list, GL_COMPILE)
    draw_titanic()
    flush_compiled()
    glEndList()


def create_background_list():
    """The sky, the water and the seabed never move, so they are baked once."""
    global background_list
    if background_list is not None:
        glDeleteLists(background_list, 1)
    background_list = glGenLists(1)
    if not background_list:
        # glGenLists returns 0 when it cannot allocate; without this the
        # background would silently never be drawn again
        return
    glNewList(background_list, GL_COMPILE)
    fill_gradient(WORLD_L, SURFACE_Y, WORLD_R, WORLD_T,
                  PAL['sky_top'], PAL['sky_bottom'], step=9)
    fill_gradient(WORLD_L, SEABED_Y, WORLD_R, SURFACE_Y,
                  PAL['water_top'], PAL['water_bottom'], step=8)
    draw_seabed()
    for x, y, r in STATIC_CLOUDS:
        draw_clouds(PAL['cloud'], (x, y), r)
    flush_compiled()
    glEndList()


# ====================================================================== #
#  Particles: explosions, sparks, torpedo trails
# ====================================================================== #

class Particle:
    def __init__(self, x, y, vx, vy, life, color, size=3, gravity=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity


def burst(x, y, n=26, palette=None, speed=230, life=0.75, size=4):
    palette = palette or [(1.0, 0.85, 0.25), (1.0, 0.55, 0.12), (1.0, 0.95, 0.75)]
    for _ in range(n):
        a = random.uniform(0, 2 * pi)
        sp = random.uniform(speed * 0.25, speed)
        particles.append(Particle(
            x, y, cos(a) * sp, sin(a) * sp,
            random.uniform(life * 0.5, life),
            random.choice(palette), size, gravity=-40))


def update_particles(dt):
    for p in particles:
        p.x += p.vx * dt
        p.y += p.vy * dt
        p.vy += p.gravity * dt
        p.vx *= 0.97
        p.life -= dt
    particles[:] = [p for p in particles if p.life > 0]


def draw_particles():
    """Grouped by colour so a burst is a handful of runs, not one per spark."""
    groups = {}
    for p in particles:
        f = p.life / p.max_life
        c = mix(PAL['water_top'], p.color, f)
        key = (round(c[0], 1), round(c[1], 1), round(c[2], 1),
               max(1, int(p.size * f) + 1))
        groups.setdefault(key, []).append((p.x, p.y))
    for (r, g, b, size), pts in groups.items():
        set_color((r, g, b))
        draw_points_batch(pts, size)


# ====================================================================== #
#  Fish: background life, purely decorative
# ====================================================================== #

class Fish:
    def __init__(self):
        self.dir = random.choice([-1, 1])
        self.x = -720 if self.dir > 0 else 720
        self.y = random.uniform(SEABED_Y + 40, SURFACE_Y - 40)
        self.speed = random.uniform(40, 105)
        self.size = random.uniform(5, 11)
        self.phase = random.uniform(0, 6.28)
        self.color = random.choice([(0.95, 0.62, 0.18), (0.85, 0.85, 0.30),
                                    (0.40, 0.75, 0.85), (0.90, 0.45, 0.45)])

    def update(self, dt, t):
        self.x += self.speed * self.dir * dt
        self.y += sin(t * 2.2 + self.phase) * 22 * dt

    def draw(self):
        s = self.size
        d = self.dir
        body = [(self.x - s * d, self.y), (self.x, self.y + s * 0.55),
                (self.x + s * d, self.y), (self.x, self.y - s * 0.55)]
        fill_polygon(self.color, body, step=2)
        # the tail trails behind: d is the way it swims, so the tail is at -d
        # (it used to be at +d, and every fish swam tail first)
        tail = [(self.x - s * d, self.y), (self.x - s * 1.9 * d, self.y + s * 0.7),
                (self.x - s * 1.9 * d, self.y - s * 0.7)]
        fill_polygon(mix(self.color, (0, 0, 0), 0.25), tail, step=2)


def update_fishes(dt, t):
    while len(fishes) < 14:
        fishes.append(Fish())
    for f in fishes:
        f.update(dt, t)
    fishes[:] = [f for f in fishes if -760 < f.x < 760]


def draw_fishes():
    for f in fishes:
        f.draw()


# ====================================================================== #
#  Sound
#
#  GLUT has no audio, but Windows ships a sound player with Python. The
#  effects are synthesised into small WAV files the first time the game runs,
#  so there are still no assets to carry around. Anywhere else, or if any of
#  this fails, the game is simply silent.
# ====================================================================== #

SOUNDS = {}
SOUND_PRIORITY = {'sonar': 5, 'win': 5, 'lose': 5, 'boom': 4, 'hit': 3, 'go': 3, 'pickup': 2,
                  'shield': 2, 'dash': 1, 'fire': 1, 'bump': 1, 'splash': 0,
                  'click': 1, 'ready': 1}
_sound_playing = (0, 0.0)       # (priority, until)

try:
    import winsound
except ImportError:
    winsound = None


def _tone(samples, sr, dur, f0, f1=None, vol=0.5, wave_kind='sine', decay=4.0, start=0.0):
    """Mixes a tone into a sample list. f0 to f1 is a pitch sweep."""
    f1 = f0 if f1 is None else f1
    n = int(dur * sr)
    s0 = int(start * sr)
    phase = 0.0
    for i in range(n):
        t = i / sr
        f = f0 + (f1 - f0) * (i / n)
        phase += 2 * pi * f / sr
        if wave_kind == 'sine':
            v = sin(phase)
        elif wave_kind == 'square':
            v = 1.0 if sin(phase) > 0 else -1.0
        else:
            v = random.uniform(-1, 1)
        env = math.exp(-decay * t / dur) * min(1.0, i / (0.004 * sr) + 1e-9)
        j = s0 + i
        if j < len(samples):
            samples[j] += v * env * vol


def _synth(name):
    sr = 22050
    length = {'fire': 0.2, 'boom': 0.55, 'hit': 0.3, 'pickup': 0.32, 'shield': 0.3,
              'dash': 0.18, 'bump': 0.1, 'splash': 0.22, 'click': 0.05, 'go': 0.35,
              'ready': 0.12, 'win': 0.8, 'lose': 0.8, 'sonar': 1.3}[name]
    s = [0.0] * int(length * sr)
    if name == 'fire':
        _tone(s, sr, 0.18, 420, 110, 0.45, 'sine', 5)
        _tone(s, sr, 0.12, 0, None, 0.25, 'noise', 6)
    elif name == 'boom':
        _tone(s, sr, 0.55, 0, None, 0.7, 'noise', 5)
        _tone(s, sr, 0.5, 90, 40, 0.6, 'sine', 3)
    elif name == 'hit':
        _tone(s, sr, 0.28, 260, 90, 0.35, 'square', 4)
        _tone(s, sr, 0.2, 0, None, 0.35, 'noise', 6)
    elif name == 'pickup':
        for k, f in enumerate((660, 880, 1320)):
            _tone(s, sr, 0.12, f, None, 0.35, 'sine', 3, start=k * 0.08)
    elif name == 'shield':
        _tone(s, sr, 0.3, 900, 500, 0.35, 'sine', 3)
    elif name == 'dash':
        _tone(s, sr, 0.18, 200, 700, 0.3, 'sine', 3)
        _tone(s, sr, 0.15, 0, None, 0.15, 'noise', 5)
    elif name == 'bump':
        _tone(s, sr, 0.1, 110, 70, 0.5, 'sine', 4)
    elif name == 'splash':
        _tone(s, sr, 0.22, 0, None, 0.25, 'noise', 7)
    elif name == 'click':
        _tone(s, sr, 0.05, 1200, None, 0.25, 'sine', 5)
    elif name == 'ready':
        _tone(s, sr, 0.12, 520, None, 0.3, 'sine', 3)
    elif name == 'go':
        _tone(s, sr, 0.35, 1040, None, 0.35, 'sine', 3)
    elif name == 'sonar':
        # a ping, and two fainter echoes coming back
        for k, vol in enumerate((0.5, 0.2, 0.08)):
            _tone(s, sr, 0.5, 1250, 1180, vol, 'sine', 4, start=k * 0.38)
    elif name == 'win':
        for k, f in enumerate((523, 659, 784, 1047)):
            _tone(s, sr, 0.3, f, None, 0.3, 'sine', 2.5, start=k * 0.13)
    elif name == 'lose':
        for k, f in enumerate((392, 330, 262)):
            _tone(s, sr, 0.35, f, None, 0.3, 'sine', 2.5, start=k * 0.16)
    # only ever scaled down: two tones on top of each other can pass 1.0
    norm = max(1.0, max(abs(v) for v in s))
    return b''.join(struct.pack('<h', int(v / norm * 30000)) for v in s), sr


def init_sound():
    if winsound is None:
        return
    try:
        folder = os.path.join(tempfile.gettempdir(), 'submarine_saga_sfx_v1')
        os.makedirs(folder, exist_ok=True)
        for name in SOUND_PRIORITY:
            path = os.path.join(folder, name + '.wav')
            if not os.path.exists(path):
                data, sr = _synth(name)
                with wave.open(path, 'wb') as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(sr)
                    w.writeframes(data)
            SOUNDS[name] = path
    except Exception:
        SOUNDS.clear()


def play(name):
    """Windows plays one sound at a time, so a quiet one never cuts off a
    louder one that is still going."""
    global _sound_playing
    if not sound_on or name not in SOUNDS:
        return
    now = time.time()
    prio = SOUND_PRIORITY[name]
    if now < _sound_playing[1] and prio < _sound_playing[0]:
        return
    try:
        winsound.PlaySound(SOUNDS[name], winsound.SND_FILENAME | winsound.SND_ASYNC
                           | winsound.SND_NODEFAULT)
        _sound_playing = (prio, now + 0.25)
    except Exception:
        pass


# ====================================================================== #
#  Floating text
# ====================================================================== #

def popup(text, x, y, color, life=0.9):
    # Popups rise about fifty units while they last, so one starts low enough
    # to stay in the water. Several things often happen in one spot at once;
    # they stack downwards rather than print on top of each other.
    y = min(y, SURFACE_Y - 70)
    moved = True
    while moved:
        moved = False
        for p in popups:
            if abs(p[1] - x) < 110 and abs(p[2] - y) < 20:
                y = p[2] - 22
                moved = True
    popups.append([text, x, y, color, life, life])


def update_popups(dt):
    for p in popups:
        p[2] += 55 * dt
        p[4] -= dt
    popups[:] = [p for p in popups if p[4] > 0]


# ====================================================================== #
#  Torpedoes
# ====================================================================== #

class Torpedo:
    """
    A torpedo carries its own direction. The original stored only a vertical
    step and worked out the horizontal one from who fired it, which meant a
    torpedo could not be aimed and player two's shots climbed when they should
    have dived.
    """

    def __init__(self, x, y, vx, vy, owner, kind='light'):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.active = True
        self.owner = owner
        self.kind = kind
        self.spec = WEAPONS[kind]
        self.scale = self.spec['scale']
        self.radius = TORPEDO_R * self.scale
        self.px, self.py = x, y   # where it was last frame, for swept hits
        self.trail = 0.0
        self.armed = 0.0        # travelled distance
        self.scored = False     # did it end in the other submarine

    def center(self):
        return self.x, self.y

    def direction(self):
        h = math.hypot(self.vx, self.vy) or 1.0
        return self.vx / h, self.vy / h

    def swept(self):
        """
        The capsule this torpedo covered in the last frame: from where its
        tail was to where its nose is now, self.radius wide. A torpedo only
        ever moves along its own length, so this is exactly the water it
        passed through and nothing more - the nose touching something is a
        hit, and nothing can slip between two frames. (A heavy torpedo turns
        a little as it homes, but by a degree or so a frame, which the
        capsule's width covers.)
        """
        ux, uy = self.direction()
        return (self.px - ux * TORPEDO_TAIL * self.scale, self.py - uy * TORPEDO_TAIL * self.scale,
                self.x + ux * TORPEDO_NOSE * self.scale, self.y + uy * TORPEDO_NOSE * self.scale)


def draw_torpedo(torpedo_list):
    for tor in torpedo_list:
        if not tor.active:
            continue
        team = TEAM[tor.owner]
        cx, cy = tor.x, tor.y
        ux, uy = tor.direction()               # along the torpedo
        px, py = -uy, ux                       # across it
        k = tor.scale                          # a heavy torpedo is the same shape, scaled up

        def at(along, across):
            return (cx + (ux * along + px * across) * k, cy + (uy * along + py * across) * k)

        body = [at(TORPEDO_NOSE, 0), at(12, TORPEDO_R), at(-16, TORPEDO_R),
                at(-16, -TORPEDO_R), at(12, -TORPEDO_R)]
        heavy = tor.kind == 'heavy'
        fill_polygon((0.22, 0.12, 0.10) if heavy else (0.15, 0.16, 0.19), body, step=2)
        draw_outline((0.85, 0.45, 0.25) if heavy else (0.45, 0.48, 0.54), body)
        if heavy:
            # a warning band round the warhead, so it reads as the big one
            fill_polygon((0.95, 0.75, 0.2), [at(4, TORPEDO_R), at(8, TORPEDO_R),
                                             at(8, -TORPEDO_R), at(4, -TORPEDO_R)], step=2)
        fill_polygon(team['trim'], [at(-14, 6), at(-TORPEDO_TAIL, 14), at(-20, 0)], step=2)
        fill_polygon(team['trim'], [at(-14, -6), at(-TORPEDO_TAIL, -14), at(-20, 0)], step=2)
        draw_filled_circle(*at(20, 0), int(3 * k), (1.0, 0.35, 0.2) if heavy else (1.0, 0.92, 0.6))


def spawn_trail(tor, dt):
    tor.trail += dt
    if tor.trail > 0.03:
        tor.trail = 0.0
        ux, uy = tor.direction()
        particles.append(Particle(
            tor.x - ux * 22, tor.y - uy * 22 + random.uniform(-4, 4),
            -ux * 40, random.uniform(6, 24), 0.45,
            (0.85, 0.94, 1.0), 3))


def hits_sub(sub, x, y, radius):
    """
    Does a round thing of this radius at (x, y) touch the submarine?

    The test runs on the polygons and circles the hull is drawn from, so what
    looks like a clear miss on screen is a clear miss in the maths, and the
    nose and tail caps count as much as the middle does.
    """
    if not sub.control:
        return False
    return capsule_hits_shape(sub.shape(), x, y, x, y, radius)


def path_hits_sub(sub, ax, ay, bx, by, radius):
    """The same test for something that moved from A to B this frame."""
    if not sub.control:
        return False
    return capsule_hits_shape(sub.shape(), ax, ay, bx, by, radius)


def splash(x):
    """A torpedo breaking the surface."""
    burst(x, SURFACE_Y, 16, [(0.85, 0.95, 1.0), (0.6, 0.85, 1.0)], speed=170, life=0.6, size=3)
    for _ in range(8):
        particles.append(Particle(x + random.uniform(-10, 10), SURFACE_Y,
                                  random.uniform(-60, 60), random.uniform(120, 240),
                                  0.6, (0.9, 0.97, 1.0), 3, gravity=-520))


def sand_puff(x, y=SEABED_Y):
    burst(x, y + 4, 18, [(0.72, 0.62, 0.42), (0.55, 0.47, 0.32)], speed=160, life=0.6)


def end_torpedo(tor):
    tor.active = False
    if not tor.scored:
        stats[tor.owner]['combo'] = 0


def detonate(tor, x, y, spare=None):
    """
    A heavy torpedo's warhead: whatever it ends on, the shock wave still
    hurts any submarine near enough, the one that fired it included. A light
    torpedo has no blast worth the name.
    """
    blast = tor.spec['blast']
    if not blast or not rule('blast'):
        return
    burst(x, y, 40, [(1.0, 0.85, 0.3), (1.0, 0.45, 0.1), (0.9, 0.9, 0.9)],
          speed=320, life=0.8, size=6)
    for r in (blast * 0.5, blast * 0.8, blast):
        for k in range(18):
            a = k * pi / 9
            particles.append(Particle(x + cos(a) * r * 0.3, y + sin(a) * r * 0.3,
                                      cos(a) * r * 2.2, sin(a) * r * 2.2, 0.35,
                                      (0.9, 0.95, 1.0), 3))
    play('boom')
    for sub in submarines:
        if sub is not spare and hits_sub(sub, x, y, blast):
            if sub.flash <= 0 or sub.shield > 0:
                popup("SHOCKWAVE", sub.center()[0], sub.center()[1] + 90, (1.0, 0.7, 0.35), 0.8)
            damage(sub, 1)


# -------------------------------------------------------------- decoys --

class Decoy:
    """A noise maker. It rises slowly and fizzes until it runs down."""

    def __init__(self, x, y, owner):
        self.x, self.y = x, y
        self.owner = owner
        self.life = DECOY_TIME
        self.active = True


decoys = []


def drop_decoy(sub):
    if (not rule('decoy') or state != STATE_PLAY or paused or not sub.control or round_clock < 0
            or time.time() - decoy_time[sub.num] < DECOY_COOLDOWN):
        return False
    decoy_time[sub.num] = time.time()
    cx, cy = sub.center()
    decoys.append(Decoy(cx - sub.facing * 60, cy - 10, sub.num))
    popup("DECOY", cx, cy + 70, (0.6, 0.95, 1.0), 0.7)
    play('dash')
    return True


def update_decoys(dt):
    for d in decoys:
        d.life -= dt
        d.y = min(SURFACE_Y - 20, d.y + 18 * dt)
        if random.random() < 0.6:
            particles.append(Particle(d.x + random.uniform(-8, 8), d.y, random.uniform(-20, 20),
                                      random.uniform(30, 70), 0.5, (0.85, 0.95, 1.0), 3))
        if d.life <= 0:
            d.active = False
    decoys[:] = [d for d in decoys if d.active]


def draw_decoys():
    t = time.time()
    for d in decoys:
        col = mix(TEAM[d.owner]['trim'], (1, 1, 1), 0.4)
        draw_filled_circle(d.x, d.y, 6, col)
        for k in range(2):
            r = 12 + ((t * 40 + k * 18) % 36)
            draw_hollow_circle(d.x, d.y, int(r), mix(col, PAL['water_top'], r / 48), 2)


def homing_target(tor):
    """What a heavy torpedo steers for: a decoy of its target's, if one is
    close enough to hear, otherwise the target itself."""
    foe = sub22 if tor.owner == 1 else sub11
    best, best_d = None, 450.0
    for d in decoys:
        if d.owner == foe.num:
            dist = math.hypot(d.x - tor.x, d.y - tor.y)
            if dist < best_d:
                best, best_d = (d.x, d.y), dist
    if best is None and foe.control:
        best = foe.center()
    return best


def steer(tor, dt):
    """Turn a homing torpedo towards its target, at a limited rate, and only
    if the target is ahead of it: it can be dodged by getting out of its
    cone, or by crossing in front of it faster than it can turn."""
    turn = tor.spec['turn']
    if not turn or not rule('homing'):
        return
    target = homing_target(tor)
    if target is None:
        return
    speed = math.hypot(tor.vx, tor.vy)
    cur = math.atan2(tor.vy, tor.vx)
    want = math.atan2(target[1] - tor.y, target[0] - tor.x)
    diff = (want - cur + pi) % (2 * pi) - pi
    if abs(diff) > math.radians(75):
        return
    a = cur + max(-turn * dt, min(turn * dt, diff))
    tor.vx, tor.vy = cos(a) * speed, sin(a) * speed


def update_torpedoes(dt):
    """
    Torpedoes hit each other, the mines, the sharks and the depth charges as
    well as the other player. That is what turns the hazards into one system:
    the mine between you and a pickup is something you can clear, and a
    torpedo coming at you is something you can shoot down.

    Every test is on the swept capsule, so it happens the frame the nose
    touches, however fast the torpedo or however slow the frame.
    """
    global hitstop
    for lst, target in ((torpedo1, sub22), (torpedo2, sub11)):
        for tor in lst:
            if not tor.active:
                continue
            tor.px, tor.py = tor.x, tor.y
            steer(tor, dt)
            tor.x += tor.vx * dt
            tor.y += tor.vy * dt
            tor.armed += math.hypot(tor.vx, tor.vy) * dt
            spawn_trail(tor, dt)
            ax, ay, bx, by = tor.swept()
            r = tor.radius

            # the nose meets the waterline or the sand: it ends there, on the
            # boundary, not twenty units past it
            if by >= SURFACE_Y:
                splash(bx)
                play('splash')
                end_torpedo(tor)
                detonate(tor, bx, SURFACE_Y)
                continue
            if by <= SEABED_Y:
                sand_puff(bx)
                end_torpedo(tor)
                detonate(tor, bx, SEABED_Y)
                continue
            if not (WORLD_L - 40 < tor.x < WORLD_R + 40):
                end_torpedo(tor)
                continue

            # the wreck on the seabed stops a torpedo, so it is real cover
            if capsule_hits_shape(WRECK_SHAPE, ax, ay, bx, by, r):
                burst(bx, by, 16, [(0.7, 0.72, 0.75), (0.9, 0.85, 0.7)],
                      speed=150, life=0.5)
                end_torpedo(tor)
                detonate(tor, bx, by)
                continue

            for d in decoys:
                if d.owner != tor.owner and seg_dist(ax, ay, bx, by, d.x, d.y) <= 16 + r:
                    d.active = False
                    end_torpedo(tor)
                    popup("DECOYED", d.x, d.y + 40, (0.6, 0.95, 1.0), 0.8)
                    burst(d.x, d.y, 20, [(0.85, 0.95, 1.0)], speed=180, life=0.5)
                    detonate(tor, d.x, d.y)
                    break
            if not tor.active:
                continue

            for mine in mines:
                if mine.active and seg_dist(ax, ay, bx, by, mine.x, mine.y) <= MINE_R + r:
                    mine.active = False
                    end_torpedo(tor)
                    burst(mine.x, mine.y, 34, speed=280, life=0.8, size=5)
                    popup("MINE CLEARED", mine.x, mine.y + 30, (1.0, 0.85, 0.4), 0.8)
                    play('boom')
                    detonate(tor, mine.x, mine.y)
                    break
            if not tor.active:
                continue

            for shark in sharks:
                if shark.active and shark.warn <= 0 and any(
                        seg_dist(ax, ay, bx, by, sx, sy) <= sr + r
                        for sx, sy, sr in shark.circles()):
                    shark.active = False
                    end_torpedo(tor)
                    burst(shark.x, shark.y, 26, [(0.8, 0.25, 0.25), (0.9, 0.6, 0.5)],
                          speed=220, life=0.7)
                    popup("SHARK DOWN", shark.x, shark.y + 30, (1.0, 0.6, 0.5), 0.8)
                    play('hit')
                    detonate(tor, shark.x, shark.y)
                    break
            if not tor.active:
                continue

            for i, bomb in enumerate(bombs):
                if bombN[i] and seg_dist(ax, ay, bx, by, bomb[0], bomb[1]) <= BOMB_R + r:
                    bombN[i] = False
                    end_torpedo(tor)
                    burst(bomb[0], bomb[1], 30, speed=260, life=0.7, size=5)
                    play('boom')
                    detonate(tor, bomb[0], bomb[1])
                    break
            if not tor.active:
                continue

            if path_hits_sub(target, ax, ay, bx, by, r):
                tor.scored = True
                end_torpedo(tor)
                burst(bx, by, 30 if tor.kind == 'light' else 50)
                st = stats[tor.owner]
                st['hits'] += 1
                st['combo'] += 1
                st['best_combo'] = max(st['best_combo'], st['combo'])
                shielded = target.shield > 0
                damage(target, tor.spec['damage'])
                # the blast still reaches whoever fired it, if they were close
                detonate(tor, bx, by, spare=target)
                if not shielded:
                    hitstop = max(hitstop, HITSTOP * (2 if tor.kind == 'heavy' else 1))
                    if tor.kind == 'heavy':
                        popup("HEAVY HIT!", bx, by + 95, (1.0, 0.55, 0.25), 1.1)
                    if st['combo'] >= 2:
                        popup(f"COMBO x{st['combo']}", bx, by + 70, TEAM[tor.owner]['trim'], 1.1)

    # two torpedoes meeting cancel each other out
    for a in torpedo1:
        if not a.active:
            continue
        for b in torpedo2:
            if b.active and seg_dist(a.px - b.px, a.py - b.py,
                                     a.x - b.x, a.y - b.y, 0.0, 0.0) <= 26:
                end_torpedo(a)
                end_torpedo(b)
                mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
                burst(mx, my, 24, [(1.0, 0.9, 0.5), (0.9, 0.95, 1.0)], speed=210, life=0.6)
                popup("INTERCEPTED", mx, my + 30, (0.9, 0.95, 1.0), 0.8)
                play('boom')
                break

    torpedo1[:] = [t for t in torpedo1 if t.active]
    torpedo2[:] = [t for t in torpedo2 if t.active]


# ====================================================================== #
#  Bubbles
# ====================================================================== #

class Bubble:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rad = random.uniform(3, 8)
        self.flag = True
        self.drift = random.uniform(-9, 9)


def draw_bubble():
    for b in bubbles:
        if b.flag:
            draw_hollow_circle(b.x, b.y, int(b.rad), (0.80, 0.93, 1.0), 2)


def update_bubbles(current_time, dt):
    global start_time1, start_time2

    if current_time - start_time1 > 0.55 and sub11.control:
        x1 = (sub11.air_duct['ap1'][0] + sub11.air_duct['ap2'][0]) / 2
        bubbles.append(Bubble(x1, sub11.air_duct['ap1'][1] + 5))
        start_time1 = current_time

    if current_time - start_time2 > 0.55 and sub22.control:
        x1 = (sub22.air_duct['ap1'][0] + sub22.air_duct['ap2'][0]) / 2
        bubbles.append(Bubble(x1, sub22.air_duct['ap1'][1] + 5))
        start_time2 = current_time

    for b in bubbles:
        b.y += 46 * dt
        b.x += b.drift * dt
        b.rad += speed_rad * 60 * dt
        if b.y > SURFACE_Y:
            b.flag = False
    # a bubble that has reached the surface is done with
    bubbles[:] = [b for b in bubbles if b.flag]


# ====================================================================== #
#  Rain
# ====================================================================== #

class rain:
    def __init__(self, x, y):
        self.x1 = x
        self.y1 = y
        self.x2 = x
        self.y2 = y + 15

def draw_rain(rains):
    """All the drops in one run: they share a colour, so they can share a call."""
    pts = []
    for rain_group in rains:
        for drop in rain_group:
            for k in range(0, 16, 3):
                pts.append((drop.x1, drop.y1 + k))
    set_color(PAL['rain'])
    draw_points_batch(pts, 3)


def generate_rain(num_drops, y):
    return [rain(random.uniform(-680, 680), y) for _ in range(num_drops)]


def create_rain_groups():
    return [generate_rain(30, 300), generate_rain(24, 330),
            generate_rain(30, 355), generate_rain(24, 375)]


rains = create_rain_groups()
RAIN_RESET = [(300, 315), (330, 345), (355, 370), (375, 390)]


def update_rains(dt):
    for index, group in enumerate(rains):
        for k in group:
            k.y1 -= speed_rain * dt
            k.y2 -= speed_rain * dt
            if k.y1 < SURFACE_Y:
                # a small splash where the drop meets the water
                if random.random() < 0.25:
                    particles.append(Particle(
                        k.x1, SURFACE_Y, random.uniform(-30, 30),
                        random.uniform(20, 60), 0.3, (0.85, 0.95, 1.0), 2, gravity=-260))
                k.y1, k.y2 = RAIN_RESET[index]
                k.x1 = k.x2 = random.uniform(-680, 680)


def reset_rains():
    global rains
    rains = create_rain_groups()


# ====================================================================== #
#  Submarines
# ====================================================================== #

class submarine:
    def __init__(self, list1, list2, list3, list4, list5, list6, circle1, circle2, num):
        self.num = num
        self.main_body = {"mp1": list1[0], "mp2": list1[1], "mp3": list1[2], "mp4": list1[3]}
        self.propeller = {'pp1': list2[0], 'pp2': list2[1], 'pp3': list2[2], 'pp4': list2[3], 'pp5': list2[4]}
        self.top_body = {"tp1": list3[0], "tp2": list3[1], "tp3": list3[2], "tp4": list3[3]}
        self.air_duct = {"ap1": list4[0], "ap2": list4[1], "ap3": list4[2], "ap4": list4[3]}
        self.door = {"dp1": list5[0], "dp2": list5[1], "dp3": list5[2], "dp4": list5[3]}
        self.lower_body = {'lp1': list6[0], 'lp2': list6[1], 'lp3': list6[2], 'lp4': list6[3], 'lp5': list6[4]}
        self.circle1 = circle1
        self.circle2 = circle2
        self.control = True
        self.life = MAX_LIFE
        self.max_life = MAX_LIFE
        # movement is a velocity the keys push against, which is what makes
        # it glide instead of jumping a fixed distance per key event
        self.vx = 0.0
        self.vy = 0.0
        self.ix = 0.0           # what the controls are asking for this frame
        self.iy = 0.0
        # mp1 is always the nose. Player one starts facing right, player two
        # left, and either turns round by reflection when it swims backwards.
        self.facing = 1 if num == 1 else -1
        # the torpedo tube's angle, and the angle the controls are swinging
        # it towards (None when nothing is asking it to move)
        self.aim = 0.0 if num == 1 else pi
        self.aim_target = None
        self.aim_turn = AIM_TURN    # the computer's tube turns slower, by level
        self.shield = 0.0
        self.rapid = 0.0
        self.boost = 0.0
        self.flash = 0.0
        self.dash_t = 0.0       # how long the dash in progress has left
        self.dash_cd = 0.0      # until the next dash is ready
        self.speed_mul = 1.0    # the computer plays a little slower on easy
        self.prop_spin = 0.0
        self._shape = None

    @property
    def team(self):
        return TEAM[self.num]

    def parts(self):
        return (self.main_body, self.propeller, self.top_body,
                self.air_duct, self.door, self.lower_body)

    # ------------------------------------------------ transformations --
    # All three are done by hand on every stored point, which keeps the hit
    # shapes and the drawing in step: whatever the hull is drawn from is
    # what gets tested.

    def move_by(self, dx, dy):
        """Translation."""
        for part in self.parts():
            for key in part:
                part[key][0] += dx
                part[key][1] += dy
        self.circle1 = [self.circle1[0] + dx, self.circle1[1] + dy]
        self.circle2 = [self.circle2[0] + dx, self.circle2[1] + dy]
        self._shape = None

    def rotate_by(self, radians):
        """Rotation about the submarine's own centre.

        The sinking animation uses this. The hit shape is built from the same
        points, so it turns with the hull. The pivot is the average of the
        four hull corners, which is the one point a rotation leaves where it
        is.
        """
        px, py = self.center()
        c, s = cos(radians), sin(radians)
        for part in self.parts():
            for key in part:
                x, y = part[key][0] - px, part[key][1] - py
                part[key][0] = px + x * c - y * s
                part[key][1] = py + x * s + y * c
        for circle in (self.circle1, self.circle2):
            x, y = circle[0] - px, circle[1] - py
            circle[0], circle[1] = px + x * c - y * s, py + x * s + y * c
        self._shape = None

    def flip(self):
        """Reflection in the vertical line through the centre: x -> 2cx - x.

        This is how a submarine turns round. The nose stays mp1, so after
        the reflection it is on the other side, and the torpedoes, the sight
        and the propeller all follow without knowing anything happened.
        """
        cx = self.center()[0]
        for part in self.parts():
            for key in part:
                part[key][0] = 2 * cx - part[key][0]
        for circle in (self.circle1, self.circle2):
            circle[0] = 2 * cx - circle[0]
        self.facing = -self.facing
        self._shape = None

    # ------------------------------------------------------- measuring --

    def center(self):
        corners = list(self.main_body.values())
        return (sum(p[0] for p in corners) / 4.0, sum(p[1] for p in corners) / 4.0)

    def nose_tail(self):
        """Centres of the round caps: mp1-mp4 is the nose edge, mp2-mp3 the tail."""
        b = self.main_body
        return (((b['mp1'][0] + b['mp4'][0]) / 2, (b['mp1'][1] + b['mp4'][1]) / 2),
                ((b['mp2'][0] + b['mp3'][0]) / 2, (b['mp2'][1] + b['mp3'][1]) / 2))

    def shape(self):
        """
        What can be hit: the hull, the conning tower, the periscope and the
        keel as polygons, and the nose and tail as circles - the exact pieces
        the submarine is drawn from. The propeller is left out on purpose: it
        is a thin spinning blade and clipping it should not cost a life.
        """
        if self._shape is None:
            polys = [[tuple(p) for p in part.values()]
                     for part in (self.main_body, self.top_body, self.air_duct,
                                  self.lower_body)]
            (nx, ny), (tx, ty) = self.nose_tail()
            circles = [(nx, ny, HULL_R), (tx, ty, HULL_R)]
            xs = [p[0] for poly in polys for p in poly] + [nx - HULL_R, nx + HULL_R,
                                                           tx - HULL_R, tx + HULL_R]
            ys = [p[1] for poly in polys for p in poly] + [ny - HULL_R, ny + HULL_R,
                                                           ty - HULL_R, ty + HULL_R]
            self._shape = ((min(xs), min(ys), max(xs), max(ys)), polys, circles)
        return self._shape

    def extent(self):
        """Everything that is drawn, propeller and caps included, for the walls."""
        xs, ys = [], []
        for part in self.parts():
            for key in part:
                xs.append(part[key][0])
                ys.append(part[key][1])
        (nx, ny), (tx, ty) = self.nose_tail()
        xs += [nx - HULL_R, nx + HULL_R, tx - HULL_R, tx + HULL_R]
        ys += [ny - HULL_R, ny + HULL_R, ty - HULL_R, ty + HULL_R]
        return (min(xs), min(ys), max(xs), max(ys))

    def solid_boxes(self):
        """Two boxes that between them hug the hull closely: the long body
        with its caps and keel, and the tower with the periscope. Used for
        the wreck and for bumping into the other submarine."""
        (nx, ny), (tx, ty) = self.nose_tail()
        body = list(self.main_body.values()) + list(self.lower_body.values())
        bx = [p[0] for p in body] + [nx - HULL_R, nx + HULL_R, tx - HULL_R, tx + HULL_R]
        by = [p[1] for p in body] + [ny - HULL_R, ny + HULL_R]
        tower = list(self.top_body.values()) + list(self.air_duct.values())
        return [(min(bx), min(by), max(bx), max(by)),
                (min(p[0] for p in tower), min(p[1] for p in tower),
                 max(p[0] for p in tower), max(p[1] for p in tower))]

    def get_bounding_box(self):
        # has_collided() reads x, y as the bottom left corner, so this returns
        # the corner and the size rather than the centre.
        x0, y0, x1, y1 = self.shape()[0]
        return AABB(x0, y0, x1 - x0, y1 - y0)


sub11 = submarine(list1, list2, list3, list4, list5, list6, circle1, circle2, 1)
submarines.append(sub11)

sub22 = submarine(list11, list22, list33, list44, list55, list66, circle11, circle22, 2)
submarines.append(sub22)


def draw_submarine(submarines):
    for sub in submarines:
        team = sub.team
        hull = team['hull']
        # a white flash for a moment after taking a hit
        if sub.flash > 0:
            hull = mix(hull, (1.0, 1.0, 1.0), min(1.0, sub.flash * 4))
        dark = mix(hull, (0.0, 0.0, 0.0), 0.45)
        outline = mix(hull, (0, 0, 0), 0.55)

        mb = sub.main_body
        body = [mb["mp1"], mb["mp2"], mb["mp3"], mb["mp4"]]
        (nx, ny), (tx, ty) = sub.nose_tail()
        cx, cy = sub.center()
        # the hull's own axes, so the details stay put when it tilts
        ln = math.hypot(nx - tx, ny - ty) or 1.0
        ux, uy = (nx - tx) / ln, (ny - ty) / ln               # tail to nose
        topx = (mb['mp1'][0] + mb['mp2'][0]) / 2 - cx
        topy = (mb['mp1'][1] + mb['mp2'][1]) / 2 - cy
        tl = math.hypot(topx, topy) or 1.0
        upx, upy = topx / tl, topy / tl                       # towards the tower

        # nose and tail caps, then the hull, so the shape reads as one piece
        draw_filled_circle(nx, ny, HULL_R, hull)
        draw_filled_circle(tx, ty, HULL_R, hull)
        fill_polygon(hull, body, step=2)

        # a lighter band along the top of the hull for a bit of shading
        top_band = [mb['mp1'], mb['mp2'],
                    [mb['mp2'][0] - upx * 12, mb['mp2'][1] - upy * 12],
                    [mb['mp1'][0] - upx * 12, mb['mp1'][1] - upy * 12]]
        fill_polygon(mix(hull, (1, 1, 1), 0.22), top_band, step=2)

        conning = [sub.top_body["tp1"], sub.top_body["tp2"],
                   sub.top_body["tp3"], sub.top_body["tp4"]]
        fill_polygon(dark, conning, step=2)
        fill_polygon(dark, [sub.air_duct["ap1"], sub.air_duct["ap2"],
                            sub.air_duct["ap3"], sub.air_duct["ap4"]], step=2)
        fill_polygon(dark, [sub.lower_body["lp1"], sub.lower_body["lp2"],
                            sub.lower_body["lp3"], sub.lower_body["lp4"]], step=2)
        fill_polygon(dark, [sub.lower_body["lp4"], sub.lower_body["lp5"],
                            sub.lower_body["lp1"]], step=2)

        # propeller: a shaft from the tail cap, then blades spun by a sine.
        # The shaft starts at the tail, whichever way the hull is facing - it
        # used to start at the nose for player two and cut the hull in half.
        pp = sub.propeller
        cxp = (pp['pp1'][0] + pp['pp2'][0] + pp['pp3'][0] + pp['pp4'][0]) / 4
        cyp = (pp['pp1'][1] + pp['pp2'][1] + pp['pp3'][1] + pp['pp4'][1]) / 4
        fill_polygon(dark, [[tx - upx * 5, ty - upy * 5], [cxp - upx * 5, cyp - upy * 5],
                            [cxp + upx * 5, cyp + upy * 5], [tx + upx * 5, ty + upy * 5]], step=2)
        blade = abs(sin(sub.prop_spin)) * 17 + 4
        fill_polygon(mix(dark, (1, 1, 1), 0.18),
                     [[cxp - ux * 5 - upx * blade, cyp - uy * 5 - upy * blade],
                      [cxp + ux * 5 - upx * blade, cyp + uy * 5 - upy * blade],
                      [cxp + ux * 5 + upx * blade, cyp + uy * 5 + upy * blade],
                      [cxp - ux * 5 + upx * blade, cyp - uy * 5 + upy * blade]], step=2)
        draw_filled_circle(cxp, cyp, 5, team['trim'])

        # a darker outline round the hull, so it stands off the water: the top
        # and bottom edges and the outer half of each cap. Drawing whole
        # circles here put two arcs across the middle of the hull.
        draw_lines(outline, mb['mp1'][0], mb['mp1'][1], mb['mp2'][0], mb['mp2'][1], 3)
        draw_lines(outline, mb['mp4'][0], mb['mp4'][1], mb['mp3'][0], mb['mp3'][1], 3)
        right, left = (0, 1, 6, 7), (2, 3, 4, 5)
        draw_arc(nx, ny, HULL_R, outline, right if ux >= 0 else left, 3)
        draw_arc(tx, ty, HULL_R, outline, left if ux >= 0 else right, 3)
        draw_outline(outline, conning)

        # the hatch on the side of the hull
        fill_polygon(mix(dark, (1, 1, 1), 0.12),
                     [sub.door["dp1"], sub.door["dp2"],
                      sub.door["dp3"], sub.door["dp4"]], step=2)

        # portholes, lit at night
        glow = team['trim'] if not night else (1.0, 0.95, 0.6)
        draw_filled_circle(sub.circle1[0], sub.circle1[1], 10, glow)
        draw_filled_circle(sub.circle2[0], sub.circle2[1], 10, mix(glow, (0, 0, 0), 0.25))
        draw_hollow_circle(sub.circle1[0], sub.circle1[1], 12, dark, 2)
        draw_hollow_circle(sub.circle2[0], sub.circle2[1], 12, dark, 2)

        # the shield bubble, when one is running
        if sub.shield > 0:
            r = 92 + sin(time.time() * 6) * 4
            pulse = 0.5 + 0.5 * sin(time.time() * 8)
            # blinks in its last two seconds, so it is clear it is about to go
            if sub.shield > 2.0 or pulse > 0.3:
                draw_hollow_circle(cx, cy, int(r), mix((0.3, 0.8, 1.0), (1, 1, 1), pulse), 3)
                draw_hollow_circle(cx, cy, int(r) - 4, (0.25, 0.65, 0.95), 2)


def sub_label(sub):
    if vs_cpu:
        return "YOU" if sub.num == 1 else "CPU"
    return "P1" if sub.num == 1 else "P2"


def marker_spot(sub):
    """
    Where a submarine's label goes: over the periscope, or under the keel
    when the submarine is high enough that a label over it would land in
    the sky and the corner panels. Returns the tip of the arrow, which way
    it points, and the x to centre text on, kept clear of the screen edges.
    """
    x0, y0, x1, y1 = sub.extent()
    cx = (x0 + x1) / 2
    tx = max(WORLD_L + 110, min(WORLD_R - 110, cx))
    if y1 + 60 < SURFACE_Y:
        return cx, y1 + 6, -1, tx
    return cx, y0 - 6, 1, tx


WARN_AHEAD = 1.0          # seconds of warning before a torpedo would arrive


def incoming(sub):
    """The enemy torpedo that will reach this submarine soonest, if one is on
    course to within hitting distance in the next WARN_AHEAD seconds."""
    cx, cy = sub.center()
    best = None
    for tor in (torpedo2 if sub.num == 1 else torpedo1):
        v2 = tor.vx * tor.vx + tor.vy * tor.vy
        if not tor.active or v2 == 0:
            continue
        tt = ((cx - tor.x) * tor.vx + (cy - tor.y) * tor.vy) / v2
        if not 0 < tt < WARN_AHEAD:
            continue
        miss = math.hypot(tor.x + tor.vx * tt - cx, tor.y + tor.vy * tt - cy)
        if miss < 80 and (best is None or tt < best[0]):
            best = (tt, tor)
    return best[1] if best else None


def draw_threat_warnings():
    """
    A blinking red warning on the side of your submarine a torpedo is coming
    from, a second before it would arrive - time enough to move. Only on
    submarines a person is steering; the computer has its own eyes.
    """
    if sin(time.time() * 18) < -0.2:
        return
    for sub in submarines:
        if not sub.control or (vs_cpu and sub.num == 2):
            continue
        tor = incoming(sub)
        if tor is None:
            continue
        cx, cy = sub.center()
        ux, uy = tor.direction()
        # on the hull's edge, towards where the torpedo is coming from
        wx, wy = cx - ux * 100, cy - uy * 100
        red = (1.0, 0.25, 0.2)
        draw_lines(red, wx - 11, wy - 8, wx + 11, wy - 8, 3)
        draw_lines(red, wx + 11, wy - 8, wx, wy + 12, 3)
        draw_lines(red, wx, wy + 12, wx - 11, wy - 8, 3)
        draw_lines(red, wx, wy + 5, wx, wy - 1, 2)
        draw_filled_circle(wx, wy - 4, 1, red)


def draw_sub_markers():
    """A small arrow by each submarine, so nobody loses track of theirs."""
    for sub in submarines:
        if not sub.control:
            continue
        x, y, d, _ = marker_spot(sub)
        fill_polygon(sub.team['trim'], [(x - 8, y - 12 * d), (x + 8, y - 12 * d), (x, y)], step=2)


def draw_sub_markers_text():
    for sub in submarines:
        if not sub.control:
            continue
        x, y, d, tx = marker_spot(sub)
        # while the round is getting going, each player is shown their keys
        # right next to their own submarine
        lines = [sub_label(sub)]
        if round_clock < 2.5 and state == STATE_PLAY and control_hint(sub, short=True):
            lines.append(control_hint(sub, short=True))
        for i, text in enumerate(lines):
            ty = y + 16 + i * 16 if d < 0 else y - 26 - i * 16
            render_text(text, tx, ty, FONT_SMALL,
                        sub.team['trim'] if i == 0 else (1.0, 1.0, 1.0),
                        center=True, shadow=True)


def damage(sub, amount):
    """One entry point for losing life, so shields and effects live in one place."""
    global shake, state, slowmo
    # STATE_SINKING is the three seconds a loser takes to reach the seabed. The
    # round is already decided, so the winner cannot blunder into a mine during
    # the animation and turn their win into a draw.
    if not sub.control or state != STATE_PLAY:
        return
    # Without this, four hazards landing in the same frame took four lives at
    # once, with one flash to show for it.
    if sub.flash > IFRAMES * 0.45:
        return
    cx, cy = sub.center()
    if sub.shield > 0:
        burst(cx, cy, 18, [(0.4, 0.85, 1.0), (0.8, 0.95, 1.0)], speed=180, life=0.5)
        sub.shield = 0.0
        # the same i-frames a normal hit gets. Without them a minefield eats
        # the shield and a life in the same frame and the shield reads as
        # having done nothing.
        sub.flash = IFRAMES
        popup("BLOCKED", cx, cy + 70, (0.5, 0.85, 1.0))
        play('shield')
        return
    sub.life = max(0, sub.life - amount)
    sub.flash = IFRAMES
    shake = min(18.0, shake + 10.0)
    burst(cx, cy, 34)
    popup(f"-{amount}", cx, cy + 70, (1.0, 0.4, 0.35))
    play('hit')
    if sub.life == 0:
        sub.control = False
        state = STATE_SINKING
        slowmo = SLOWMO_TIME
        play('boom')
        announce(f"{sub.team['name']} IS GOING DOWN", 2.0)
        burst(cx, cy, 70, [(1.0, 0.9, 0.4), (1.0, 0.5, 0.1), (0.6, 0.6, 0.6)],
              speed=340, life=1.2, size=6)
    elif sub.life <= LAST_STAND_AT < sub.life + amount:
        announce(f"{sub.team['name']} LAST STAND", 1.8)


def heal(sub, amount):
    sub.life = min(sub.max_life, sub.life + amount)


def update_submarine_positions(dt):
    for sub in submarines:
        sub.flash = max(0.0, sub.flash - dt)
        sub.shield = max(0.0, sub.shield - dt)
        sub.rapid = max(0.0, sub.rapid - dt)
        sub.boost = max(0.0, sub.boost - dt)
        sub.dash_t = max(0.0, sub.dash_t - dt)
        sub.dash_cd = max(0.0, sub.dash_cd - dt)
        if sub.control:
            sub.prop_spin += dt * (14 + abs(sub.vx) * 0.04)
            # a damaged hull trails smoke from the tower, so how hurt the
            # other player is can be read without looking at the corner
            if (sub.life <= 4 and
                    random.random() < (0.5 if sub.life <= LAST_STAND_AT else 0.25)):
                ap = sub.air_duct['ap1']
                particles.append(Particle(ap[0] + random.uniform(-6, 6), ap[1],
                                          random.uniform(-12, 12), random.uniform(40, 80),
                                          0.9, (0.30, 0.30, 0.33), 5))
        else:
            auto_fall(sub, dt)


def top_speed(sub):
    top = SUB_MAX * sub.speed_mul * (1.25 if sub.boost > 0 else 1.0)
    if sub.life <= LAST_STAND_AT:
        top *= 1.22          # last stand, see reload_time() as well
    return top


def dash(sub):
    """A short burst of speed on a cooldown, for getting out of the way."""
    if (state != STATE_PLAY or paused or not sub.control or sub.dash_cd > 0
            or round_clock < 0):
        return False
    h = math.hypot(sub.ix, sub.iy)
    if h > 0.1:
        dx, dy = sub.ix / h, sub.iy / h
    else:
        dx, dy = float(sub.facing), 0.0
    sub.vx, sub.vy = dx * DASH_SPEED, dy * DASH_SPEED
    sub.dash_t = DASH_TIME
    sub.dash_cd = DASH_COOLDOWN
    cx, cy = sub.center()
    for _ in range(14):
        particles.append(Particle(cx - dx * 60 + random.uniform(-20, 20),
                                  cy - dy * 60 + random.uniform(-20, 20),
                                  -dx * random.uniform(60, 160), -dy * random.uniform(60, 160),
                                  0.5, (0.85, 0.95, 1.0), 4))
    play('dash')
    return True


def floor_under(x):
    """The wreck is a ledge in the middle of the seabed."""
    return WRECK[3] if WRECK[0] < x < WRECK[2] else SEABED_Y


def push_out_of(sub, box):
    """
    Separate a submarine from a solid box by the shortest way out.

    Whichever side it went in by least is the side it came in from, so a hull
    dropping onto the wreck lands on its deck and one swimming into its side
    is stopped by the side - it no longer jumps seventy units up the moment
    its centre crosses the edge.
    """
    hit = False
    for x0, y0, x1, y1 in sub.solid_boxes():
        if x1 <= box[0] or x0 >= box[2] or y1 <= box[1] or y0 >= box[3]:
            continue
        up, left, right = box[3] - y0, x1 - box[0], box[2] - x0
        m = min(up, left, right)
        if m == up:
            sub.move_by(0, up)
            sub.vy = max(0.0, sub.vy)
        elif m == left:
            sub.move_by(-left, 0)
            sub.vx = min(0.0, sub.vx)
        else:
            sub.move_by(right, 0)
            sub.vx = max(0.0, sub.vx)
        hit = True
    return hit


def keep_in_bounds(sub):
    """
    The walls, the surface and the seabed, measured on what is drawn.

    The whole submarine, propeller and caps included, stays inside the
    window; the periscope may reach the waterline but nothing goes above it;
    and the keel sits on the sand. Pushing into a wall stops the submarine
    dead rather than bouncing it, so holding the key against a wall is steady
    instead of a jitter.
    """
    min_x, min_y, max_x, max_y = sub.extent()
    if min_x < WORLD_L + 2:
        sub.move_by(WORLD_L + 2 - min_x, 0)
        sub.vx = max(0.0, sub.vx)
    if max_x > WORLD_R - 2:
        sub.move_by(WORLD_R - 2 - max_x, 0)
        sub.vx = min(0.0, sub.vx)
    if max_y > SURFACE_Y:
        sub.move_by(0, SURFACE_Y - max_y)
        sub.vy = min(0.0, sub.vy)
    if min_y < SEABED_Y + 2:
        sub.move_by(0, SEABED_Y + 2 - min_y)
        sub.vy = max(0.0, sub.vy)
    push_out_of(sub, WRECK_SOLID)


def bump_subs(a, b):
    """
    The two submarines are solid to each other. They used to pass straight
    through one another. Overlapping boxes are pushed apart along whichever
    axis they overlap least, and the speeds along that axis are swapped and
    damped, so a collision knocks both about the way it looks like it should.
    """
    if not (a.control and b.control):
        return
    hit = False
    for ba in a.solid_boxes():
        for bb in b.solid_boxes():
            ox = min(ba[2], bb[2]) - max(ba[0], bb[0])
            oy = min(ba[3], bb[3]) - max(ba[1], bb[1])
            if ox <= 0 or oy <= 0:
                continue
            if ox < oy:
                s = 1 if (ba[0] + ba[2]) < (bb[0] + bb[2]) else -1
                a.move_by(-s * ox / 2, 0)
                b.move_by(s * ox / 2, 0)
                if (a.vx - b.vx) * s > 0:
                    a.vx, b.vx = b.vx * 0.6, a.vx * 0.6
            else:
                s = 1 if (ba[1] + ba[3]) < (bb[1] + bb[3]) else -1
                a.move_by(0, -s * oy / 2)
                b.move_by(0, s * oy / 2)
                if (a.vy - b.vy) * s > 0:
                    a.vy, b.vy = b.vy * 0.6, a.vy * 0.6
            hit = True
            break
        if hit:
            break
    if hit:
        (ax, ay), (bx, by) = a.center(), b.center()
        if random.random() < 0.5:
            burst((ax + bx) / 2, (ay + by) / 2, 8, [(0.85, 0.95, 1.0)], speed=120, life=0.4, size=3)
        play('bump')


def apply_physics(dt):
    """
    Velocity, drag, turning round, and everything solid.

    Keys set an intent (ix, iy) and the movement happens here, once a frame,
    so it does not depend on the keyboard's repeat rate. Pushing against your
    own motion gets extra thrust and an axis you have let go of is braked
    harder than one you are holding, which is most of what makes the
    submarine feel like it answers the keys rather than drifts about.
    """
    for sub in submarines:
        if not sub.control:
            continue
        top = top_speed(sub)
        ix, iy = sub.ix, sub.iy
        mag = math.hypot(ix, iy)
        if mag > 1e-6 and sub.dash_t <= 0:
            amount = min(1.0, mag)
            dx, dy = ix / mag * amount, iy / mag * amount
            ax = SUB_ACCEL * (TURN_BOOST if dx * sub.vx < 0 else 1.0)
            ay = SUB_ACCEL * (TURN_BOOST if dy * sub.vy < 0 else 1.0)
            sub.vx += dx * ax * dt
            sub.vy += dy * ay * dt
        if sub.dash_t <= 0:
            # clamp the speed, not each axis on its own, or travelling
            # diagonally is 41 percent faster than travelling straight
            speed = math.hypot(sub.vx, sub.vy)
            if speed > top:
                sub.vx *= top / speed
                sub.vy *= top / speed
            sub.vx -= sub.vx * min(1.0, (SUB_DRAG if abs(ix) > 1e-6 else SUB_BRAKE) * dt)
            sub.vy -= sub.vy * min(1.0, (SUB_DRAG if abs(iy) > 1e-6 else SUB_BRAKE) * dt)

        sub.move_by(sub.vx * dt, sub.vy * dt)

        # swing the torpedo tube towards where the controls point, at a
        # steady rate; with nothing held it stays where it was left
        if sub.aim_target is not None:
            diff = (sub.aim_target - sub.aim + pi) % (2 * pi) - pi
            step = sub.aim_turn * dt
            sub.aim += max(-step, min(step, diff))
            sub.aim = (sub.aim + pi) % (2 * pi) - pi

        # the hull turns round to face the way the tube points, so the
        # torpedo always leaves from the nose
        if cos(sub.aim) * sub.facing < -0.15:
            sub.flip()

    bump_subs(sub11, sub22)
    for sub in submarines:
        if sub.control:
            keep_in_bounds(sub)


SINK_TILT_RATE = 0.22    # radians a second, while a hull is on its way down


def auto_fall(sub, dt):
    min_x, min_y, max_x, max_y = sub.extent()
    if min_y > floor_under(sub.center()[0]) + 4:
        sub.move_by(0, -150 * dt)
        # a hull going down goes down nose first, and the tilt is what makes
        # it read as sinking rather than as being lowered on a rope
        sub.rotate_by(-SINK_TILT_RATE * dt * sub.facing)
        if random.random() < 0.30:
            cx, cy = sub.center()
            particles.append(Particle(
                cx + random.uniform(-40, 40), cy, random.uniform(-20, 20),
                random.uniform(30, 70), 0.7, (0.35, 0.35, 0.38), 4))
    else:
        end_round(2 if sub.num == 1 else 1)


def reset_submarine_positions():
    sub11.main_body = {"mp1": [-530, 180], "mp2": [-630, 180], "mp3": [-630, 130], "mp4": [-530, 130]}
    sub11.propeller = {"pp1": [-660, 165], "pp2": [-680, 165], "pp3": [-680, 145], "pp4": [-660, 145], "pp5": [-655, 155]}
    sub11.top_body = {"tp1": [-550, 200], "tp2": [-580, 200], "tp3": [-610, 180], "tp4": [-550, 180]}
    sub11.air_duct = {"ap1": [-560, 215], "ap2": [-570, 215], "ap3": [-570, 200], "ap4": [-560, 200]}
    sub11.door = {"dp1": [-540, 165], "dp2": [-560, 165], "dp3": [-560, 145], "dp4": [-540, 145]}
    sub11.lower_body = {"lp1": [-570, 130], "lp2": [-610, 130], "lp3": [-610, 115], "lp4": [-570, 115], "lp5": [-555, 122.5]}
    sub11.circle1 = [-580, 155]
    sub11.circle2 = [-615, 155]

    sub22.main_body = {"mp1": [530, 180], "mp2": [630, 180], "mp3": [630, 130], "mp4": [530, 130]}
    sub22.propeller = {"pp1": [660, 165], "pp2": [680, 165], "pp3": [680, 145], "pp4": [660, 145], "pp5": [655, 155]}
    sub22.top_body = {"tp1": [550, 200], "tp2": [580, 200], "tp3": [610, 180], "tp4": [550, 180]}
    sub22.air_duct = {"ap1": [560, 215], "ap2": [570, 215], "ap3": [570, 200], "ap4": [560, 200]}
    sub22.door = {"dp1": [540, 165], "dp2": [560, 165], "dp3": [560, 145], "dp4": [540, 145]}
    sub22.lower_body = {"lp1": [570, 130], "lp2": [610, 130], "lp3": [610, 115], "lp4": [570, 115], "lp5": [555, 122.5]}
    sub22.circle1 = [580, 155]
    sub22.circle2 = [615, 155]

    for sub in submarines:
        sub.facing = 1 if sub.num == 1 else -1
        sub.aim = 0.0 if sub.num == 1 else pi
        sub.aim_target = None
        sub.aim_turn = AIM_TURN
        sub.vx = sub.vy = sub.ix = sub.iy = 0.0
        sub.shield = sub.rapid = sub.boost = sub.flash = 0.0
        sub.dash_t = sub.dash_cd = 0.0
        sub._shape = None
        # the starting spot sits the periscope clear of the surface
        keep_in_bounds(sub)


# ====================================================================== #
#  The boat on the surface, and the depth charges it drops
# ====================================================================== #

def boatMaker(t):
    bob = sin(t * 1.3) * 4
    boatx = 80
    boaty = 233 + bob
    boat_x1, boat_x2 = -boatx, boatx
    boat_y1, boat_y2 = boaty, boaty

    hull = [[boat_x1 - 90, boat_y1 + 70], [boat_x1 + 180, boat_y1 + 55],
            [boat_x1 + 180, boat_y1 + 30], [boat_x2, boat_y2],
            [boat_x1, boat_y1], [boat_x1 - 40, boat_y1 + 40]]
    fill_polygon((0.42, 0.28, 0.18), hull, step=3)
    draw_outline((0.62, 0.46, 0.30), hull)

    deck = [[boatx - 108, boaty + 40], [boatx - 70, boaty + 40],
            [boatx - 70, boaty + 65], [boatx - 108, boaty + 65]]
    fill_polygon((0.30, 0.38, 0.18), deck, step=3)

    sail = [[boatx - 20, boaty + 55], [boatx - 20, boaty + 140], [boatx + 40, boaty + 70]]
    fill_polygon((0.96, 0.90, 0.72), sail, step=3)
    draw_outline((0.85, 0.72, 0.35), sail)

    for i in range(4):
        cx = -boatx + 15 + i * 40
        color = (0.15, 0.15, 0.15) if bombN[i] else (0.45, 0.45, 0.45)
        draw_filled_circle(cx, boaty + 20, 10, color)

    draw_filled_circle(-boatx + 2, boaty + 83, 7, (0.2, 0.2, 0.2))


def sudden_death():
    return state in (STATE_PLAY, STATE_SINKING) and round_clock >= SUDDEN_DEATH_AT


def bomb_fall_speed():
    return fall_speed * (1.6 if sudden_death() else 1.0)


def draw_bombs():
    for idx, bomb in enumerate(bombs):
        if bombN[idx] and SEABED_Y < bomb[1] < SURFACE_Y + 30:
            draw_filled_circle(bomb[0], bomb[1], 7, (0.12, 0.12, 0.14))
            draw_hollow_circle(bomb[0], bomb[1], 11, (0.85, 0.25, 0.2), 2)
            draw_lines((0.5, 0.5, 0.5), bomb[0], bomb[1] + 11, bomb[0], bomb[1] + 20, 2)


def update_bombs(dt):
    global bomb_delay
    if bomb_delay > 0:
        # the pass is held back while the warning markers are on screen
        bomb_delay -= dt
        return

    fall = bomb_fall_speed()
    for i in range(len(bombs)):
        px, py = bombs[i][0], bombs[i][1]
        bombs[i][0] += bomb_vx[i] * dt
        bombs[i][1] -= fall * dt
        if bombN[i]:
            check_bomb_collisions(bombs[i], BOMB_R, i, px, py)

    if all(bomb[1] < SEABED_Y for bomb in bombs):
        reset_bombs()


def bomb_landing_x(i):
    """Where charge i will cross the seabed, so it can be marked in advance."""
    drop = bombs[i][1] - SEABED_Y
    if drop <= 0:
        return bombs[i][0]
    return bombs[i][0] + bomb_vx[i] * (drop / bomb_fall_speed())


def draw_bomb_warnings():
    """
    A bracket where each charge is heading.

    Without this the charges are the most frequent hazard in the game and
    arrive with no warning at all, so they read as bad luck rather than as
    something you could have moved out of.
    """
    pulse = 0.5 + 0.5 * sin(time.time() * 7)
    col = mix((0.95, 0.35, 0.25), (1.0, 0.85, 0.4), pulse)
    pts = []
    for i, bomb in enumerate(bombs):
        if not bombN[i] or bomb[1] < SEABED_Y + 60:
            continue
        x = max(WORLD_L + 30, min(WORLD_R - 30, bomb_landing_x(i)))
        y = floor_under(x) + 16
        # a small bracket on the sand where this charge is going to land
        for k in range(0, 15, 3):
            pts += [(x - 18, y + k), (x + 18, y + k),
                    (x - 18 + k, y), (x + 18 - k, y)]
    set_color(col)
    draw_points_batch(pts, 3)


def check_bomb_collisions(bomb, bomb_radius, index, px=None, py=None):
    """A charge is tested along the path it fell this frame, like a torpedo."""
    bx, by = bomb
    if px is None:
        px, py = bx, by
    if by <= SEABED_Y:
        bombN[index] = False
        sand_puff(bx)
        return
    if wreck_blocks(bx, by):
        bombN[index] = False
        burst(bx, by, 20, [(0.7, 0.72, 0.75)], speed=150, life=0.5)
        return
    for sub in submarines:
        if path_hits_sub(sub, px, py, bx, by, bomb_radius):
            bombN[index] = False
            burst(bx, by, 26)
            damage(sub, BOMB_DAMAGE)
            return


def reset_bombs():
    """
    Start a new pass of depth charges.

    The sideways speed is a plain horizontal one. Deriving it from the angle
    as 1/tan runs from nothing to billions across sixty degrees, and a hazard
    you are meant to read cannot have a speed like that.
    """
    global bombs, bombN, theta, bomb_vx, bomb_delay
    boaty = 233
    bombs = [[-65 + i * 40, boaty + 20] for i in range(4)]
    bombN = [True, True, True, True]
    theta = random.randrange(-30, 31)
    spread = theta * 2.4
    bomb_vx = [spread - 90, spread - 30, spread + 30, spread + 90]
    bomb_delay = 0.4 if sudden_death() else 0.8


# The wreck is solid: torpedoes stop against it and submarines stand on it.
# It is the only fixed feature on the map, so it is the only reason to care
# where you are. The three funnels above it are thin enough to shoot between,
# which is half the point of them, so only the hull counts.
WRECK = (-220, -252, 220, -230)
WRECK_HULL = [(-220, -230), (220, -230), (200, -252), (-200, -252)]
WRECK_SHAPE = (WRECK, [WRECK_HULL], [])
# for submarines it is a block down to the sand, so nothing can wedge itself
# into the gap under the slanted ends
WRECK_SOLID = (WRECK[0], SEABED_Y - 50, WRECK[2], WRECK[3])


def wreck_blocks(x, y):
    return point_in_polygon(x, y, WRECK_HULL)


def draw_titanic():
    color_body = (0.30, 0.31, 0.33)
    fill_polygon(color_body, WRECK_HULL, step=3)
    draw_outline((0.45, 0.46, 0.48), WRECK_HULL)
    for x in (-140, 0, 140):
        fill_polygon((0.14, 0.15, 0.16),
                     [[x - 9, -228], [x + 9, -228], [x + 7, -196], [x - 7, -196]], step=2)
    for x in range(-150, 151, 30):
        draw_filled_circle(x, -241, 4, (0.85, 0.72, 0.25) if night else (0.55, 0.25, 0.2))


# ====================================================================== #
#  Power ups
#
#  The original had one falling circle that added health. There are now four
#  kinds, each drawn with its own symbol so you can tell at a glance whether
#  it is worth swimming across the map for.
# ====================================================================== #

KIND_HEALTH, KIND_SHIELD, KIND_RAPID, KIND_BOOST = 'health', 'shield', 'rapid', 'boost'

PICKUP_STYLE = {
    KIND_HEALTH: ((0.90, 0.20, 0.25), 'plus'),
    KIND_SHIELD: ((0.25, 0.65, 0.95), 'ring'),
    KIND_RAPID: ((0.98, 0.72, 0.16), 'bolt'),
    KIND_BOOST: ((0.35, 0.85, 0.45), 'arrow'),
}


class UniqueCircle:
    def __init__(self, x, y, radius, kind=KIND_HEALTH):
        self.x = x
        self.y = y
        self.radius = radius
        self.active = True
        self.direction = 1
        self.max_radius = 26
        self.min_radius = 16
        self.kind = kind
        self.phase = random.uniform(0, 6.28)
        self.landed = None      # seconds left once it has reached the bottom


def spawn_unique_circle():
    kind = random.choices(
        [KIND_HEALTH, KIND_SHIELD, KIND_RAPID, KIND_BOOST],
        weights=[3, 3, 2, 2])[0]
    # a pickup lands a little closer to whoever is behind, so being four one
    # down is a fight rather than a formality
    if sub11.life < sub22.life:
        x = random.uniform(-460, 120)
    elif sub22.life < sub11.life:
        x = random.uniform(-120, 460)
    else:
        x = random.uniform(-420, 420)
    unique_circles.append(UniqueCircle(x, SURFACE_Y - 20, 20, kind))


def update_unique_circles(dt, t):
    """A pickup drifts down, then waits on the sand or the wreck for a few
    seconds rather than vanishing the moment it gets there."""
    for circle in unique_circles:
        if not circle.active:
            continue
        circle.radius += circle.direction * 22 * dt
        if circle.radius >= circle.max_radius or circle.radius <= circle.min_radius:
            circle.direction *= -1
        if circle.landed is None:
            circle.y -= 95 * dt
            circle.x += sin(t * 1.6 + circle.phase) * 26 * dt
            rest = floor_under(circle.x) + circle.max_radius + 2
            if circle.y <= rest:
                circle.y = rest
                circle.landed = PICKUP_LINGER
        else:
            circle.landed -= dt
            if circle.landed <= 0:
                circle.active = False
    unique_circles[:] = [c for c in unique_circles if c.active]


def draw_hollow_cross(x, y, size, color):
    draw_lines(color, x, y - size, x, y + size, 3)
    draw_lines(color, x - size, y, x + size, y, 3)


def draw_pickup_icon(x, y, r, kind):
    color, symbol = PICKUP_STYLE[kind]
    r = int(r)
    draw_filled_circle(x, y, r - 6, mix(color, (0, 0, 0), 0.55))
    draw_hollow_circle(x, y, r, color, 3)
    draw_hollow_circle(x, y, r - 3, mix(color, (1, 1, 1), 0.4), 2)
    s = r - 10
    if symbol == 'plus':
        draw_hollow_cross(x, y, s, color)
    elif symbol == 'ring':
        draw_hollow_circle(x, y, max(2, s), color, 3)
    elif symbol == 'bolt':
        draw_lines(color, x - s * 0.5, y + s, x + s * 0.2, y, 3)
        draw_lines(color, x + s * 0.2, y, x - s * 0.2, y, 3)
        draw_lines(color, x - s * 0.2, y, x + s * 0.5, y - s, 3)
    else:
        draw_lines(color, x - s, y - s * 0.4, x, y + s * 0.7, 3)
        draw_lines(color, x, y + s * 0.7, x + s, y - s * 0.4, 3)


def draw_unique_circles():
    blink = sin(time.time() * 14) > 0
    for c in unique_circles:
        if not c.active:
            continue
        # blinking out in its last two seconds on the bottom
        if c.landed is not None and c.landed < 2.0 and not blink:
            continue
        draw_pickup_icon(c.x, c.y, c.radius, c.kind)


PICKUP_NAMES = {KIND_HEALTH: "+HEALTH", KIND_SHIELD: "SHIELD", KIND_RAPID: "RAPID FIRE",
                KIND_BOOST: "SPEED"}


def apply_pickup(sub, kind):
    if kind == KIND_HEALTH:
        gained = min(HEALTH_PICKUP, sub.max_life - sub.life)
        heal(sub, HEALTH_PICKUP)
        if gained:
            announce(f"{sub.team['name']} +{gained} HEALTH")
        else:
            # nothing to heal, so it is worth a little cover instead
            sub.shield = max(sub.shield, 3.0)
            announce(f"{sub.team['name']} PATCHED UP")
    elif kind == KIND_SHIELD:
        sub.shield = SHIELD_TIME
        announce(f"{sub.team['name']} SHIELD UP")
    elif kind == KIND_RAPID:
        sub.rapid = RAPID_TIME
        announce(f"{sub.team['name']} RAPID FIRE")
    else:
        sub.boost = BOOST_TIME
        announce(f"{sub.team['name']} SPEED BOOST")


def check_collision_with_unique_circle(sub):
    if not sub.control:
        return
    for circle in unique_circles:
        if not circle.active:
            continue
        cx, cy, radius = circle.x, circle.y, circle.radius
        if hits_sub(sub, cx, cy, radius + PICKUP_GRAB):
            circle.active = False
            color = PICKUP_STYLE[circle.kind][0]
            burst(cx, cy, 22, [color, mix(color, (1, 1, 1), 0.5)], speed=170, life=0.6)
            popup(PICKUP_NAMES[circle.kind], cx, cy + 30, color)
            play('pickup')
            apply_pickup(sub, circle.kind)


# ====================================================================== #
#  Mines: drift slowly, and go off if anyone touches them
# ====================================================================== #

class Mine:
    def __init__(self):
        self.x = random.uniform(-380, 380)
        self.y = random.uniform(SEABED_Y + 60, SURFACE_Y - 90)
        self.drift = random.uniform(-26, 26)
        self.phase = random.uniform(0, 6.28)
        self.active = True
        self.armed = 1.4
        self.life = 26.0        # a mine clears itself, so the map never silts up

    def update(self, dt, t):
        self.x += self.drift * dt
        self.y += sin(t * 0.9 + self.phase) * 14 * dt
        self.armed = max(0.0, self.armed - dt)
        self.life -= dt
        if self.life <= 0:
            self.active = False
        # turn round at the edges of the middle of the map, the same way on
        # both sides, and never drift into the wreck
        if (self.x < -640 and self.drift < 0) or (self.x > 640 and self.drift > 0):
            self.drift *= -1
        self.y = max(WRECK[3] + MINE_R + 4, min(SURFACE_Y - 40, self.y))

    def draw(self, t):
        pulse = 0.5 + 0.5 * sin(t * 5 + self.phase)
        draw_mine_icon(self.x, self.y, self.armed <= 0, pulse, self.life)
        if self.armed > 0:
            # a tightening ring while it arms, so a fresh mine is obviously
            # not yet dangerous
            draw_hollow_circle(self.x, self.y, int(19 + 9 * self.armed),
                               (0.95, 0.75, 0.3), 2)


def draw_mine_icon(x, y, armed=True, pulse=0.5, life=99.0):
    body = (0.16, 0.17, 0.20) if armed else (0.35, 0.35, 0.38)
    draw_filled_circle(x, y, 13, body)
    for i in range(8):
        a = i * (pi / 4)
        draw_lines((0.45, 0.45, 0.5), x + cos(a) * 13, y + sin(a) * 13,
                   x + cos(a) * 21, y + sin(a) * 21, 3)
    if armed:
        draw_filled_circle(x, y, 5, mix((0.5, 0.1, 0.1), (1.0, 0.3, 0.2), pulse))
        if life < 5:
            # blinking out, so it is clear it is about to go
            draw_hollow_circle(x, y, 26, (0.6, 0.6, 0.65) if pulse > 0.5
                               else (0.3, 0.3, 0.35), 2)


def update_mines(dt, t):
    for m in mines:
        if not m.active:
            continue
        m.update(dt, t)
        if m.armed > 0:
            continue
        for sub in submarines:
            if hits_sub(sub, m.x, m.y, MINE_R):
                m.active = False
                burst(m.x, m.y, 40, speed=300, life=0.9, size=5)
                play('boom')
                damage(sub, MINE_DAMAGE)
                break
    mines[:] = [m for m in mines if m.active]


def draw_mines(t):
    for m in mines:
        m.draw(t)


# ====================================================================== #
#  Shark
# ====================================================================== #

class Shark:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.speed = random.uniform(110, 175)
        self.width = 60
        self.height = 34
        self.active = True
        self.phase = random.uniform(0, 6.28)
        self.warn = 1.3         # a fin shows at the surface before it appears

    def move(self, dt, t):
        self.x += self.speed * self.direction * dt
        self.y += sin(t * 2.0 + self.phase) * 28 * dt

    def circles(self):
        return [(self.x + off * self.direction, self.y, r) for off, r in SHARK_CIRCLES]

    def get_bounding_box(self):
        return AABB(self.x - self.width / 2, self.y - self.height / 2,
                    self.width, self.height)


def spawn_shark():
    direction = random.choice([-1, 1])
    x = -720 if direction == 1 else 720
    sharks.append(Shark(x, random.uniform(SEABED_Y + 60, SURFACE_Y - 60), direction))


def draw_shark_warnings():
    for shark in sharks:
        if shark.active and shark.warn > 0:
            x = shark.x + shark.direction * 120
            x = max(WORLD_L + 20, min(WORLD_R - 20, x))
            fill_polygon((0.32, 0.38, 0.46),
                         [(x - 14, SURFACE_Y - 4), (x, SURFACE_Y + 24),
                          (x + 14, SURFACE_Y - 4)], step=2)


def update_sharks(dt, t):
    for shark in sharks:
        if not shark.active:
            continue
        if shark.warn > 0:
            shark.warn -= dt
            continue
        shark.move(dt, t)
        if shark.x < -780 or shark.x > 780:
            shark.active = False
            continue
        for sub in submarines:
            if any(hits_sub(sub, sx, sy, sr) for sx, sy, sr in shark.circles()):
                shark.active = False
                burst(shark.x, shark.y, 22, [(0.8, 0.2, 0.2), (0.9, 0.5, 0.4)],
                      speed=200, life=0.6)
                damage(sub, SHARK_DAMAGE)
                break
    sharks[:] = [s for s in sharks if s.active]


def draw_shark(shark, t):
    if not shark.active or shark.warn > 0:
        return
    body_c = (0.32, 0.38, 0.46)
    belly_c = (0.72, 0.76, 0.80)
    d = shark.direction

    def ax(v):
        return v * -d

    body = [(shark.x + ax(-46), shark.y),
            (shark.x + ax(-22), shark.y - 16),
            (shark.x + ax(22), shark.y - 11),
            (shark.x + ax(44), shark.y),
            (shark.x + ax(22), shark.y + 12),
            (shark.x + ax(-22), shark.y + 17)]
    fill_polygon(body_c, body, step=2)
    fill_polygon(belly_c, [(shark.x + ax(-30), shark.y - 6),
                           (shark.x + ax(18), shark.y - 6),
                           (shark.x + ax(20), shark.y - 10),
                           (shark.x + ax(-24), shark.y - 14)], step=2)

    fin_wave = sin(t * 6 + shark.phase) * 4
    fill_polygon(body_c, [(shark.x + ax(6), shark.y + 12),
                          (shark.x + ax(16), shark.y + 30 + fin_wave),
                          (shark.x + ax(26), shark.y + 11)], step=2)
    tail_wave = sin(t * 7 + shark.phase) * 7
    fill_polygon(body_c, [(shark.x + ax(42), shark.y),
                          (shark.x + ax(60), shark.y + 18 + tail_wave),
                          (shark.x + ax(52), shark.y),
                          (shark.x + ax(60), shark.y - 18 + tail_wave)], step=2)
    fill_polygon(body_c, [(shark.x + ax(0), shark.y - 10),
                          (shark.x + ax(12), shark.y - 24),
                          (shark.x + ax(22), shark.y - 10)], step=2)

    draw_filled_circle(shark.x + ax(-32), shark.y + 6, 4, (1.0, 1.0, 1.0))
    draw_filled_circle(shark.x + ax(-32), shark.y + 6, 2, (0.0, 0.0, 0.0))
    for i in range(3):
        gx = shark.x + ax(-14 + i * 6)
        draw_lines((0.20, 0.26, 0.34), gx, shark.y + 5, gx, shark.y - 6, 2)
    # a row of teeth, so it reads as a shark and not a grey blob
    for i in range(5):
        tx = shark.x + ax(-42 + i * 5)
        draw_lines((1.0, 1.0, 1.0), tx, shark.y - 6, tx + ax(2), shark.y - 11, 2)


# ====================================================================== #
#  Match statistics and the saved record against the computer
# ====================================================================== #

def fresh_stats():
    return {n: {'shots': 0, 'hits': 0, 'combo': 0, 'best_combo': 0} for n in (1, 2)}


stats = fresh_stats()

def _game_folder():
    """Where the game lives. Built into an .exe, that is the folder the .exe
    is in - the script itself is unpacked somewhere temporary each run, and a
    record saved next to it would be lost."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(globals().get('__file__', 'x')))


SAVE_PATH = os.path.join(_game_folder(), 'submarine_saga_save.json')


def load_records():
    rec = {'wins': [0, 0, 0], 'losses': [0, 0, 0], 'streak': 0, 'best_streak': 0}
    try:
        with open(SAVE_PATH) as f:
            data = json.load(f)
        for key in rec:
            if key in data:
                rec[key] = data[key]
    except (OSError, ValueError):
        pass
    return rec


def save_records():
    try:
        with open(SAVE_PATH, 'w') as f:
            json.dump(records, f)
    except OSError:
        pass


records = load_records()


# ====================================================================== #
#  HUD
# ====================================================================== #

_glyph_w = {}


def screen_font(font):
    """Bitmap fonts do not scale, so in a large window the small ones are
    swapped for the next size up and the words keep roughly their size on
    screen next to everything else, which does scale."""
    if PIXEL_SCALE >= 1.25 and font is FONT_SMALL:
        return FONT
    return font


def text_width(text, font):
    """Width in world units, so text can be centred properly rather than guessed."""
    font = screen_font(font)
    px = 0
    for ch in text:
        key = (id(font), ch)
        w = _glyph_w.get(key)
        if w is None:
            try:
                w = glutBitmapWidth(font, ord(ch))
            except Exception:
                w = 8
            _glyph_w[key] = w
        px += w
    return px / PIXEL_SCALE


def render_text(text, x, y, font, color, center=False, shadow=False):
    if center:
        x -= text_width(text, font) / 2
    font = screen_font(font)
    if shadow:
        glColor3f(0.0, 0.0, 0.0)
        glRasterPos2f(x + 1.5, y - 1.5)
        bitmap_string(font, text)
    glColor3f(color[0], color[1], color[2])
    glRasterPos2f(x, y)
    bitmap_string(font, text)


_bitmap_string_ok = True


def bitmap_string(font, text):
    """A whole string in one call (freeglut's glutBitmapString) rather than a
    call per character, which was most of the title screen's frame time.
    Plain GLUT does not have it, so it falls back to one character at a time."""
    global _bitmap_string_ok
    if _bitmap_string_ok:
        try:
            glutBitmapString(font, text.encode('latin-1', 'replace'))
            return
        except Exception:
            _bitmap_string_ok = False
    for char in text:
        glutBitmapCharacter(font, ord(char))


def draw_bar(x, y, w, h, frac, color, back=(0.10, 0.12, 0.16)):
    fill_rectangle(back, x - 2, y - 2, x + w + 2, y + h + 2, step=3)
    if frac > 0:
        fill_rectangle(color, x, y, x + w * max(0.0, min(1.0, frac)), y + h, step=3)


def draw_panel(x0, y0, x1, y1, border=(0.30, 0.42, 0.55), fill=(0.04, 0.07, 0.13)):
    fill_rectangle(fill, x0, y0, x1, y1, step=5)
    draw_outline(border, [[x0, y0], [x1, y0], [x1, y1], [x0, y1]])


def draw_hud_panels():
    """Drawn with points, before the text, so the HUD stays readable on any sky."""
    for left in (True, False):
        x = -668 if left else 388
        draw_panel(x, 246, x + 280, 372)
    fill_rectangle((0.04, 0.07, 0.13), -150, 344, 150, 372, step=5)


def reload_time(sub, kind='light'):
    cooldown = WEAPONS[kind]['reload']
    if sub.rapid > 0:
        cooldown *= RAPID_FACTOR
    if sub.life <= LAST_STAND_AT:
        cooldown *= LAST_STAND_RELOAD
    if vs_cpu and sub.num == 2:
        cooldown *= CPU_LEVELS[cpu_level]['reload']
    return cooldown


def last_fired(sub, kind='light'):
    if kind == 'heavy':
        return heavy_time[sub.num]
    return tor_time1 if sub.num == 1 else tor_time2


def reload_frac(sub, kind='light'):
    return min(1.0, (time.time() - last_fired(sub, kind)) / reload_time(sub, kind))


def draw_hud_shapes():
    for sub in submarines:
        team = sub.team
        left = sub.num == 1
        x = -650 if left else 406
        y = 330

        frac = sub.life / sub.max_life
        bar_color = (0.30, 0.80, 0.40) if frac > 0.6 else \
                    ((0.95, 0.75, 0.20) if frac > 0.3 else (0.90, 0.25, 0.25))
        draw_bar(x, y, 240, 16, frac, bar_color)

        # one pip per life, so the number is readable without counting pixels
        for i in range(sub.max_life):
            cx = x + 10 + i * 24
            on = i < sub.life
            draw_filled_circle(cx, y - 18, 7,
                               team['trim'] if on else (0.25, 0.27, 0.31))

        # what is ready: light torpedo, heavy torpedo, dash, decoy. A full
        # bar is ready; the heavy one flashes when it is, because it is the
        # one worth waiting for.
        # Only what this level has is shown.
        heavy_col = (1.0, 0.55, 0.25)
        if reload_frac(sub, 'heavy') >= 1.0 and sin(time.time() * 8) > 0:
            heavy_col = (1.0, 0.85, 0.45)
        bars = [(reload_frac(sub, 'light'), (0.55, 0.75, 0.95))]
        if rule('heavy'):
            bars.append((reload_frac(sub, 'heavy'), heavy_col))
        bars.append((1.0 - sub.dash_cd / DASH_COOLDOWN, (0.55, 0.95, 0.70)))
        if rule('decoy'):
            bars.append((min(1.0, (time.time() - decoy_time[sub.num]) / DECOY_COOLDOWN),
                         (0.6, 0.9, 1.0)))
        gap = 6
        w = (240 - gap * (len(bars) - 1)) / len(bars)
        for i, (frac_, col) in enumerate(bars):
            draw_bar(x + i * (w + gap), y - 40, w, 7, frac_, col)

        # active power ups
        badge_x = x
        for label, remaining, full, col in (
                ("SHIELD", sub.shield, SHIELD_TIME, (0.25, 0.65, 0.95)),
                ("RAPID", sub.rapid, RAPID_TIME, (0.98, 0.72, 0.16)),
                ("BOOST", sub.boost, BOOST_TIME, (0.35, 0.85, 0.45))):
            if remaining > 0:
                draw_bar(badge_x, y - 58, 60, 7, remaining / full, col)
                badge_x += 70


def control_hint(sub, short=False):
    """The keys for this submarine, in words, for the HUD and the READY screen."""
    if vs_cpu and sub.num == 2:
        return "" if short else f"COMPUTER  -  {CPU_LEVELS[cpu_level]['name']}"
    p1 = sub.num == 1
    fire_key, heavy_key, dash_key, decoy_key = ("Space", "F", "E", "Q") if p1 else ("P", "O", "L", "K")
    if short:
        move = "WASD / ARROWS" if vs_cpu else ("W A S D" if p1 else "ARROWS")
        keys = fire_key + ("  " + heavy_key if rule('heavy') else "")
        return f"{move}  +  {keys}"
    parts = [f"{fire_key} torp"]
    if rule('heavy'):
        parts.append(f"{heavy_key} heavy")
    parts.append(f"{dash_key} dash")
    if rule('decoy'):
        parts.append(f"{decoy_key} decoy")
    if not vs_cpu and not rule('heavy'):
        parts.insert(0, "WASD move" if p1 else "ARROWS move")
    return "  ".join(parts)


def draw_hud_text():
    for sub in submarines:
        team = sub.team
        x = -650 if sub.num == 1 else 406
        render_text(team['name'], x, 354, FONT, (1.0, 1.0, 1.0))
        render_text(sub_label(sub), x + text_width(team['name'], FONT) + 10, 354,
                    FONT_SMALL, team['trim'])
        render_text(f"{score[sub.num]}/{ROUNDS_TO_WIN}", x + 205, 354, FONT, team['trim'])
        render_text(control_hint(sub), x, 252, FONT_SMALL, (0.70, 0.78, 0.88))

    if sudden_death():
        if sin(time.time() * 8) > -0.3:
            render_text("SUDDEN DEATH", 0, 352, FONT, (1.0, 0.35, 0.3), center=True)
    else:
        header = f"ROUND {round_no}   {CPU_LEVELS[cpu_level]['name']}"
        if state in (STATE_PLAY, STATE_SINKING) and round_clock >= 0:
            left = max(0, int(SUDDEN_DEATH_AT - round_clock + 0.999))
            header += f"     {left // 60}:{left % 60:02d}"
        render_text(header, 0, 352, FONT, (1.0, 0.92, 0.55), center=True)
    render_text(f"{fps_shown:.0f} FPS", 600, -374, FONT_SMALL, (0.7, 0.75, 0.8))
    render_text("H  help", 232, -355, FONT_SMALL, (0.80, 0.85, 0.92))


def draw_world_text():
    """Text that sits in the water: labels, popups, announcements, READY."""
    draw_sub_markers_text()
    for text, x, y, color, life, max_life in popups:
        # kept in the water, clear of the corner panels above it
        x = max(WORLD_L + 60, min(WORLD_R - 60, x))
        y = min(y, SURFACE_Y - 12)
        render_text(text, x, y, FONT, color, center=True, shadow=True)
    if announcement and time.time() < announce_until:
        render_text(announcement, 0, 96, FONT, (1.0, 0.92, 0.55), center=True, shadow=True)
    if state == STATE_PLAY and round_clock < 0.6:
        word = "READY" if round_clock < 0 else "GO!"
        render_text(f"ROUND {round_no}", 0, 70, FONT, (0.9, 0.95, 1.0), center=True, shadow=True)
        render_text(word, 0, 30, FONT_BIG, (1.0, 0.85, 0.35), center=True, shadow=True)


def announce(text, seconds=1.6):
    global announcement, announce_until
    announcement = text
    announce_until = time.time() + seconds


BUTTONS_X = (-100, 0, 100, 200)     # restart, pause, menu, help


def draw_button_chrome():
    """The discs behind the buttons. Static, so they get baked."""
    for cx in BUTTONS_X:
        draw_filled_circle(cx, -350, 20, (0.12, 0.14, 0.19))
        draw_hollow_circle(cx, -350, 21, (0.40, 0.45, 0.55), 2)


def draw_button_bar():
    draw_restart()
    draw_pause()
    draw_cancel()
    draw_help_button()


def draw_restart():
    center_x, base_y, s = -100, -350, 20
    color = (0.95, 0.55, 0.30)
    draw_lines(color, center_x - s // 2, base_y, center_x + s // 2, base_y, 3)
    draw_lines(color, center_x - s // 2, base_y, center_x, base_y + s // 2, 3)
    draw_lines(color, center_x - s // 2, base_y, center_x, base_y - s // 2, 3)


def draw_pause():
    center_x, base_y, s, gap = 0, -350, 20, 6
    color = (1.0, 0.80, 0.30)
    if not paused:
        draw_lines(color, center_x - gap, base_y + s // 2, center_x - gap, base_y - s // 2, 3)
        draw_lines(color, center_x + gap, base_y + s // 2, center_x + gap, base_y - s // 2, 3)
    else:
        draw_lines(color, center_x - gap, base_y + s // 2, center_x - gap, base_y - s // 2, 3)
        draw_lines(color, center_x - gap, base_y + s // 2, center_x + s // 2, base_y, 3)
        draw_lines(color, center_x - gap, base_y - s // 2, center_x + s // 2, base_y, 3)


def draw_cancel():
    center_x, base_y, s = 100, -350, 20
    color = (0.92, 0.32, 0.32)
    draw_lines(color, center_x - s // 2, base_y + s // 2, center_x + s // 2, base_y - s // 2, 3)
    draw_lines(color, center_x + s // 2, base_y + s // 2, center_x - s // 2, base_y - s // 2, 3)


def draw_help_button():
    """A question mark: the top half of a midpoint circle, a hook and a dot."""
    cx, cy = 200, -350
    color = (0.55, 0.85, 1.0)
    draw_arc(cx, cy + 5, 7, color, (0, 1, 2, 3, 7), 3)
    draw_lines(color, cx + 5, cy, cx, cy - 4, 3)
    draw_lines(color, cx, cy - 4, cx, cy - 7, 3)
    draw_filled_circle(cx, cy - 12, 2, color)


# ====================================================================== #
#  Rounds and match flow
# ====================================================================== #

def end_round(winner):
    """A round always has a winner: damage() stops landing the moment the loser
    starts sinking, so the two of them cannot go down together."""
    global state, round_winner, round_over_at, match_winner, game_over, player
    if state not in (STATE_PLAY, STATE_SINKING):
        return
    round_winner = winner
    player = winner
    score[winner] += 1
    round_over_at = time.time()
    # whoever just lost is usually still leaning on a key. Without this the
    # banner is gone before either of them has read it.
    held.clear()
    if score[winner] >= ROUNDS_TO_WIN:
        match_winner = winner
        state = STATE_MATCH_OVER
        game_over = True
        if vs_cpu:
            if winner == 1:
                records['wins'][cpu_level] += 1
                records['streak'] += 1
                records['best_streak'] = max(records['best_streak'], records['streak'])
            else:
                records['losses'][cpu_level] += 1
                records['streak'] = 0
            save_records()
    else:
        state = STATE_ROUND_OVER
    play('lose' if vs_cpu and winner == 2 else 'win')


def banner_settled():
    """Ignore the first moment of a result screen, so it cannot be skipped by
    a key or a click that was already on its way when the round ended."""
    return time.time() - round_over_at > BANNER_GRACE


def start_round():
    global state, round_winner, game_over, paused, player, shake
    global last_spawn_time, last_spawn_time_shark, last_mine_time
    global tor_time1, tor_time2, round_clock, hitstop, slowmo, help_paused
    now = time.time()
    # these are wall clock stamps: without resetting them, twenty seconds on
    # the round banner meant a pickup, a shark and a mine all arrived at once.
    # They start counting when READY turns into GO.
    last_spawn_time = now + READY_TIME
    last_spawn_time_shark = now + READY_TIME
    last_mine_time = now + READY_TIME
    tor_time1 = tor_time2 = now - 5
    for n in (1, 2):
        heavy_time[n] = now - 30
        decoy_time[n] = now - 30
    decoys.clear()
    shake = 0.0
    hitstop = slowmo = 0.0
    round_clock = -READY_TIME
    state = STATE_PLAY
    round_winner = None
    game_over = False
    paused = False
    help_paused = False
    player = None
    for sub in submarines:
        sub.control = True
        sub.life = sub.max_life
        sub.speed_mul = CPU_LEVELS[cpu_level]['speed'] if (vs_cpu and sub.num == 2) else 1.0
    for st in stats.values():
        st['combo'] = 0
    torpedo1.clear()
    torpedo2.clear()
    bubbles.clear()
    sharks.clear()
    unique_circles.clear()
    particles.clear()
    mines.clear()
    popups.clear()
    cpu.reset()
    reset_submarine_positions()
    reset_bombs()
    reset_rains()
    play('ready')


def next_round():
    global round_no
    round_no += 1
    start_round()


def reset_game():
    global round_no, match_winner, stats
    round_no = 1
    score[1] = score[2] = 0
    match_winner = None
    stats = fresh_stats()
    start_round()


def start_match(against_cpu):
    global vs_cpu
    vs_cpu = against_cpu
    reset_game()


# ====================================================================== #
#  Spawning
# ====================================================================== #

def handle_spawn_events(current_time, dt, t):
    global last_spawn_time, last_spawn_time_shark, last_mine_time

    if current_time - last_spawn_time > spawn_interval:
        spawn_unique_circle()
        last_spawn_time = current_time

    if current_time - last_spawn_time_shark > 14:
        spawn_shark()
        last_spawn_time_shark = current_time

    mine_gap, mine_cap = (5, 6) if sudden_death() else (10, 4)
    if current_time - last_mine_time > mine_gap and len(mines) < mine_cap:
        mines.append(Mine())
        last_mine_time = current_time

    update_unique_circles(dt, t)
    check_collision_with_unique_circle(sub11)
    check_collision_with_unique_circle(sub22)
    update_sharks(dt, t)
    update_mines(dt, t)


# ====================================================================== #
#  Input
#
#  Keys set an intent that the physics step reads once a frame, instead of
#  moving the submarine directly. Holding a key accelerates smoothly and
#  releasing it lets the submarine settle. Holding fire keeps firing as fast
#  as the reload allows.
# ====================================================================== #

held = set()

BINDINGS = {
    1: {'move': {b'w': (0, 1), b's': (0, -1), b'a': (-1, 0), b'd': (1, 0)},
        'fire': (b' ', b'c'), 'heavy': (b'f',), 'dash': (b'e', b'v'), 'decoy': (b'q',)},
    2: {'move': {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)},
        'fire': (b'p', b'\r', b'0'), 'heavy': (b'o', b'1'), 'dash': (b'l', b'.'),
        'decoy': (b'k', b'2')},
}


def bindings_for(sub):
    """Against the computer, the one human can use either set of keys."""
    if vs_cpu:
        return (BINDINGS[1], BINDINGS[2]) if sub.num == 1 else ()
    return (BINDINGS[sub.num],)


def apply_input(dt):
    if state not in (STATE_PLAY, STATE_SINKING) or paused:
        return
    for sub in submarines:
        if vs_cpu and sub.num == 2:
            cpu_update(sub, sub11, dt)
            continue
        ax = ay = 0
        firing = heavy = False
        for b in bindings_for(sub):
            for key, (kx, ky) in b['move'].items():
                if key in held:
                    ax += kx
                    ay += ky
            firing = firing or any(k in held for k in b['fire'])
            heavy = heavy or any(k in held for k in b['heavy'])
        sub.ix = float(max(-1, min(1, ax)))
        sub.iy = float(max(-1, min(1, ay)))
        # the keys swing the tube towards the way they point; let go and the
        # tube stays at whatever angle it had reached
        sub.aim_target = math.atan2(sub.iy, sub.ix) if (ax or ay) else None
        if firing:
            fire(sub)
        if heavy:
            fire(sub, 'heavy')


def is_cpu(sub):
    return vs_cpu and sub.num == 2


def aim_of(sub):
    """
    Where a torpedo fired now would go: along the tube's angle, nudged onto
    the other submarine if it is within AIM_ASSIST of it. The nudge is what
    makes a diagonal or corner shot possible without landing on the exact
    degree - and the sight shows the nudged line, so it never lies.

    The nudge is for people on a keyboard. The computer does not get it: it
    fires down its tube, at where it last looked for you.
    """
    ux, uy = cos(sub.aim), sin(sub.aim)
    enemy = sub22 if sub.num == 1 else sub11
    if enemy.control and not is_cpu(sub):
        cx, cy = sub.center()
        ex, ey = enemy.center()
        want = math.atan2(ey - cy, ex - cx)
        diff = (want - sub.aim + pi) % (2 * pi) - pi
        if abs(diff) <= AIM_ASSIST:
            ux, uy = cos(want), sin(want)
    return ux, uy


TUBE = 78          # centre of the hull to the centre of a torpedo leaving it


def fire(sub, kind='light'):
    global tor_time1, tor_time2
    if (state not in (STATE_PLAY, STATE_SINKING) or paused or not sub.control
            or round_clock < 0):
        return

    if kind == 'heavy' and not rule('heavy'):
        return          # EASY is light torpedoes only

    now = time.time()
    if now - last_fired(sub, kind) < reload_time(sub, kind):
        return

    spec = WEAPONS[kind]
    ux, uy = aim_of(sub)
    cx, cy = sub.center()
    tube = TUBE + (spec['scale'] - 1) * TORPEDO_TAIL
    nose_x = cx + ux * tube
    nose_y = cy + uy * tube
    (torpedo1 if sub.num == 1 else torpedo2).append(
        Torpedo(nose_x, nose_y, ux * spec['speed'], uy * spec['speed'], sub.num, kind))
    stats[sub.num]['shots'] += 1

    heavy = kind == 'heavy'
    burst(nose_x, nose_y, 18 if heavy else 9, [(1.0, 0.9, 0.5), (1.0, 0.7, 0.3)],
          speed=180 if heavy else 140, life=0.35, size=4 if heavy else 3)
    # firing kicks the submarine back a little, the heavy one more so
    kick = 120 if heavy else 35
    sub.vx -= ux * kick
    sub.vy -= uy * kick
    play('fire')

    if heavy:
        heavy_time[sub.num] = now
    elif sub.num == 1:
        tor_time1 = now
    else:
        tor_time2 = now


# far enough to cross the map, because a sight that stops short of where the
# torpedo would still be flying is telling you the wrong thing
AIM_RANGE = 1440
AIM_STEP = 16            # one dash every this many units
AIM_PROBE = 8            # ...and a collision test every this many

_trace_cache = {}


def aim_trace(sub):
    """
    Walk the line a light torpedo's nose would take and stop at the first
    thing it would hit. A light torpedo flies straight at a constant speed, so
    the same swept tests the collision code does frame by frame can be done
    all at once here, and the sight is telling the truth rather than guessing.
    (A heavy one starts down the same line and then homes.)

    Returns the dashes to draw, where the shot ends, and whether the thing it
    ends on is the other submarine.
    """
    enemy = sub22 if sub.num == 1 else sub11
    key = (sub.num, sub.center(), sub.aim, sub.facing, enemy.center(),
           enemy.control, round(enemy.shape()[0][3], 2),
           tuple((m.x, m.y) for m in mines if m.active))
    hit = _trace_cache.get(key)
    if hit is not None:
        return hit
    if len(_trace_cache) > 64:
        _trace_cache.clear()

    ux, uy = aim_of(sub)
    ox, oy = sub.center()
    x = ox + ux * (TUBE + TORPEDO_NOSE)
    y = oy + uy * (TUBE + TORPEDO_NOSE)
    dashes = []
    result = None
    # Clip the whole line of fire to the water with Cohen-Sutherland first:
    # the walk then only covers the part of it that is inside, and ends
    # exactly on the wall, the surface or the sand.
    clipped = cohen_sutherland(x, y, x + ux * AIM_RANGE, y + uy * AIM_RANGE,
                               WORLD_L, SEABED_Y, WORLD_R, SURFACE_Y)
    if clipped is None or (clipped[0], clipped[1]) != (x, y):
        # the tube itself is already out of the water, against a wall
        result = ([], (x, y), False)
        _trace_cache[key] = result
        return result
    reach = math.hypot(clipped[2] - x, clipped[3] - y)
    for i in range(int(reach // AIM_PROBE)):
        px, py = x, y
        x += ux * AIM_PROBE
        y += uy * AIM_PROBE
        if capsule_hits_shape(WRECK_SHAPE, px, py, x, y, TORPEDO_R):
            break
        if any(m.active and seg_dist(px, py, x, y, m.x, m.y) <= MINE_R + TORPEDO_R
               for m in mines):
            break
        if path_hits_sub(enemy, px, py, x, y, TORPEDO_R):
            result = (dashes, (x, y), True)
            break
        if i % (AIM_STEP // AIM_PROBE) == 0:
            dashes.append((x, y))
    if result is None:
        result = (dashes, (x, y), False)
    _trace_cache[key] = result
    return result


def draw_aim_line(sub):
    """The sight: a dashed line that stops where the shot would, red on a lock."""
    if not sub.control:
        return
    dashes, (hx, hy), locked = aim_trace(sub)
    if locked:
        # a lock is the one thing worth interrupting the colour scheme for
        blink = 0.5 + 0.5 * sin(time.time() * 12)
        set_color(mix((1.0, 0.28, 0.20), (1.0, 0.70, 0.25), blink))
        draw_points_batch(dashes, 4)
        draw_hollow_circle(int(hx), int(hy), 15, (1.0, 0.35, 0.22), 2)
    else:
        set_color(mix(sub.team['trim'], (1, 1, 1), 0.35))
        draw_points_batch(dashes, 3)


# ====================================================================== #
#  The computer opponent
#
#  It plays by the same rules and through the same controls: it sets an
#  intent, fires with fire() and dashes with dash(), and turns its tube the
#  way a player does.
#
#  It does not see you all the time. It looks every so often and aims at
#  where you were when it last looked, with its tube turning at its own
#  rate, so a player who keeps moving is a player it has to hunt: fire, then
#  move, and its shot goes where you used to be. It gets no aim snap, and
#  it has to wait between shots. The levels differ in how often it looks,
#  how fast it turns, how long it waits, and how well it dodges.
# ====================================================================== #

CPU_LEVELS = [
    # look: seconds between looks at you; lead: how much of your movement it
    # allows for when it looks; turn: its tube's turn rate; gap: the least
    # time between its shots; aim_err: degrees it can be off by;
    # dodge / dash / decoy: how often it reacts to a torpedo coming at it
    {'name': 'EASY', 'think': 0.55, 'look': 1.5, 'lead': 0.0, 'turn': 1.5, 'gap': 2.4,
     'aim_err': 12, 'dodge': 0.30, 'dash': 0.0, 'decoy': 0.15, 'speed': 0.75, 'reload': 1.6},
    {'name': 'NORMAL', 'think': 0.30, 'look': 1.0, 'lead': 0.0, 'turn': 2.2, 'gap': 1.6,
     'aim_err': 7, 'dodge': 0.65, 'dash': 0.35, 'decoy': 0.5, 'speed': 0.90, 'reload': 1.15},
    {'name': 'HARD', 'think': 0.15, 'look': 0.55, 'lead': 0.25, 'turn': 3.0, 'gap': 1.0,
     'aim_err': 2, 'dodge': 0.92, 'dash': 0.75, 'decoy': 0.9, 'speed': 1.0, 'reload': 1.0},
]


class CpuBrain:
    def __init__(self):
        self.reset()

    def reset(self):
        self.timer = 0.0
        self.goal = None
        self.lock = 0.0
        self.err = 0.0          # how far off its tube is, re-rolled each look
        self.seen = {}          # per torpedo: (will it dodge, will it dash, decoy)
        self.look = 0.0         # until it next looks for the player
        self.spotted = None     # where it saw the player last time it looked
        self.last_shot = -99.0  # round_clock when it last fired


cpu = CpuBrain()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def cpu_pick_goal(sub, foe, lv):
    cx, cy = sub.center()
    fx, fy = cpu.spotted or foe.center()
    # a pickup it can reach before the player can
    best = None
    for c in unique_circles:
        dm = math.hypot(c.x - cx, c.y - cy)
        df = math.hypot(c.x - fx, c.y - fy)
        if c.kind == KIND_HEALTH and sub.life == sub.max_life:
            continue
        if dm < df + 40 and dm < 600 and (best is None or dm < best[0]):
            best = (dm, c.x, c.y)
    if best:
        return best[1], best[2]
    # otherwise a firing position at some distance on its own side - above,
    # level or below, since it can aim at an angle as well as anyone
    side = 1 if cx >= fx else -1
    dist = random.uniform(300, 520)
    gx = fx + side * dist
    if not WORLD_L + 110 < gx < WORLD_R - 110:
        gx = fx - side * dist
    gx = clamp(gx, WORLD_L + 110, WORLD_R - 110)
    gy = clamp(fy + random.uniform(-160, 160), SEABED_Y + 70, SURFACE_Y - 70)
    return gx, gy


def cpu_update(sub, foe, dt):
    lv = CPU_LEVELS[cpu_level]
    br = cpu
    sub.ix = sub.iy = 0.0
    if not sub.control:
        return
    cx, cy = sub.center()
    # it looks for the player every so often, not every frame
    br.look -= dt
    if br.look <= 0 or br.spotted is None:
        br.look = lv['look'] * random.uniform(0.8, 1.25)
        px, py = foe.center()
        # a sharp one allows for where you are heading, a little
        travel = math.hypot(px - cx, py - cy) / WEAPONS['light']['speed']
        br.spotted = (px + foe.vx * travel * lv['lead'], py + foe.vy * travel * lv['lead'])
        br.err = math.radians(random.uniform(-lv['aim_err'], lv['aim_err']))
    fx, fy = br.spotted
    sub.aim_turn = lv['turn']
    wx = wy = 0.0
    threatened = urgent = False

    # torpedoes on a course to hit it
    for tor in (torpedo1 if sub.num == 2 else torpedo2):
        k = id(tor)
        if k not in br.seen:
            br.seen[k] = (random.random() < lv['dodge'], random.random() < lv['dash'],
                          random.random() < lv['decoy'])
        will_dodge, will_dash, will_decoy = br.seen[k]
        # a heavy torpedo homes, so the answer to one is a decoy
        if (tor.kind == 'heavy' and will_decoy
                and math.hypot(tor.x - cx, tor.y - cy) < 380):
            drop_decoy(sub)
        if not will_dodge:
            continue
        v2 = tor.vx * tor.vx + tor.vy * tor.vy or 1.0
        tt = ((cx - tor.x) * tor.vx + (cy - tor.y) * tor.vy) / v2
        if tt < 0 or tt > 1.0:
            continue
        mx = tor.x + tor.vx * tt - cx
        my = tor.y + tor.vy * tt - cy
        if math.hypot(mx, my) > 95:
            continue
        ux, uy = tor.direction()
        px, py = -uy, ux
        across = mx * px + my * py
        if abs(across) > 5:
            side = -1 if across > 0 else 1
        else:
            side = 1 if SEABED_Y + 90 < cy + py * 90 < SURFACE_Y - 90 else -1
        wx += px * side
        wy += py * side
        threatened = True
        urgent = urgent or (tt < 0.4 and will_dash)

    # depth charges falling on it
    if bomb_delay <= 0:
        for i, b in enumerate(bombs):
            if not bombN[i] or b[1] < cy:
                continue
            t = (b[1] - cy) / bomb_fall_speed()
            if t > 1.4:
                continue
            if abs(b[0] + bomb_vx[i] * t - cx) < 90:
                wx += 1 if cx >= b[0] + bomb_vx[i] * t else -1
                threatened = True

    # a shark coming its way
    for sh in sharks:
        if (sh.active and sh.warn <= 0 and abs(sh.y - cy) < 80
                and (cx - sh.x) * sh.direction > 0 and abs(cx - sh.x) < 420):
            up = cy > sh.y
            if cy > SURFACE_Y - 120:
                up = False
            elif cy < SEABED_Y + 120:
                up = True
            wy += 1 if up else -1
            threatened = True

    # mines push it away
    for m in mines:
        d = math.hypot(cx - m.x, cy - m.y) or 1.0
        if d < 140:
            wx += (cx - m.x) / d * (140 - d) / 70
            wy += (cy - m.y) / d * (140 - d) / 70

    if not threatened:
        br.timer -= dt
        if br.timer <= 0 or br.goal is None:
            br.timer = lv['think'] * random.uniform(0.8, 1.4)
            br.goal = cpu_pick_goal(sub, foe, lv)
        gx, gy = br.goal
        dx, dy = gx - cx, gy - cy
        d = math.hypot(dx, dy)
        if d > 18:
            s = min(1.0, d / 90)
            wx += dx / d * s
            wy += dy / d * s

    m = math.hypot(wx, wy)
    if m > 1:
        wx, wy = wx / m, wy / m
    sub.ix, sub.iy = wx, wy
    if urgent:
        dash(sub)

    # its tube swings towards where it last saw the player, at its own rate
    to_spot = math.atan2(fy - cy, fx - cx) + br.err
    sub.aim_target = to_spot

    # it fires when its tube has come round onto that spot, the way is not
    # blocked, and it has waited long enough since its last shot
    now = round_clock
    off = abs((to_spot - sub.aim + pi) % (2 * pi) - pi)
    dist = math.hypot(fx - cx, fy - cy)
    if off < math.radians(4) and now - br.last_shot >= lv['gap']:
        dashes, end, locked = aim_trace(sub)
        reach = math.hypot(end[0] - cx, end[1] - cy)
        if locked or reach >= dist - 60:
            # on NORMAL and HARD, a long shot is worth the heavy torpedo; on
            # HARD it homes as well
            heavy = (rule('heavy') and dist > 300 and random.random() < 0.35
                     and reload_frac(sub, 'heavy') >= 1.0)
            count = len(torpedo2)
            fire(sub, 'heavy' if heavy else 'light')
            if len(torpedo2) > count:
                br.last_shot = now
    if len(br.seen) > 200:
        br.seen.clear()


# ====================================================================== #
#  Keyboard and mouse
# ====================================================================== #

def set_night(on):
    global night, PAL, background_update_needed
    night = on
    PAL = dict(NIGHT if on else DAY)
    background_update_needed = True


def toggle_help():
    """The help screen pauses a game in progress, and closing it resumes."""
    global show_help, help_paused, paused
    show_help = not show_help
    if show_help:
        if state in (STATE_PLAY, STATE_SINKING) and not paused:
            paused = True
            help_paused = True
    else:
        if help_paused:
            paused = False
        help_paused = False
    play('click')


def menu_move(step):
    global menu_choice
    menu_choice = (menu_choice + step) % MENU_ROWS
    play('click')


def menu_level(step):
    global cpu_level
    if menu_choice in (0, 1):      # the level applies to one player and two
        cpu_level = clamp(cpu_level + step, 0, len(CPU_LEVELS) - 1)
        play('click')


def menu_activate():
    if menu_choice == 2:
        toggle_help()
    else:
        start_match(menu_choice == 0)


def go_to_menu():
    global state, paused, help_paused
    state = STATE_MENU
    paused = help_paused = False
    held.clear()


def keyboardListener(key, x, y):
    global paused, restart_game, sound_on, help_paused

    # every comparison below uses the lowered key, so caps lock changes
    # nothing - it used to let both players swim while neither could shoot
    k = key.lower()
    if state == STATE_INTRO:
        end_intro()              # any key skips the intro, and does nothing else
        glutPostRedisplay()
        return
    held.add(k)

    if k == b'h':
        toggle_help()
        glutPostRedisplay()
        return
    if show_help:
        if k in (b'\x1b', b'\r', b' '):
            toggle_help()
        glutPostRedisplay()
        return

    if k == b'n':
        set_night(not night)
    if k == b'm':
        sound_on = not sound_on
        announce("SOUND ON" if sound_on else "SOUND OFF", 1.0)

    if state == STATE_MENU:
        if k == b'w':
            menu_move(-1)
        elif k == b's':
            menu_move(1)
        elif k == b'a':
            menu_level(-1)
        elif k == b'd':
            menu_level(1)
        elif k in (b'\r', b' '):
            menu_activate()
        elif k == b'1':
            start_match(True)
        elif k == b'2':
            start_match(False)
        glutPostRedisplay()
        return

    if state in (STATE_ROUND_OVER, STATE_MATCH_OVER) and k in (b'\r', b' '):
        if banner_settled():
            if state == STATE_ROUND_OVER:
                next_round()
            else:
                reset_game()
        glutPostRedisplay()
        return

    if k == b'i':
        if state in (STATE_PLAY, STATE_SINKING):
            paused = not paused
            help_paused = False
    if k == b'r':
        restart_game = True
    if key == b'\x1b':
        go_to_menu()

    # fire and dash on the key press itself, so the shot leaves this frame
    for sub in submarines:
        for b in bindings_for(sub):
            if k in b['fire']:
                fire(sub)
            if k in b['heavy']:
                fire(sub, 'heavy')
            if k in b['dash']:
                dash(sub)
            if k in b['decoy']:
                drop_decoy(sub)

    glutPostRedisplay()


def keyboardUpListener(key, x, y):
    held.discard(key)
    held.discard(key.lower())


def entryListener(state_):
    """
    Clear the held keys when the pointer leaves the window.

    A key up event that lands in another window never reaches us, and the
    submarine keeps accelerating on a key nobody is holding. GLUT has no
    focus callback, so leaving the window is the signal we get.
    """
    held.clear()


SPECIAL = {GLUT_KEY_UP: 'up', GLUT_KEY_DOWN: 'down',
           GLUT_KEY_LEFT: 'left', GLUT_KEY_RIGHT: 'right'}


def specialKeyListener(key, x, y):
    if state == STATE_INTRO:
        end_intro()
        glutPostRedisplay()
        return
    if key == GLUT_KEY_F1:
        toggle_help()
        glutPostRedisplay()
        return
    name = SPECIAL.get(key)
    if name:
        held.add(name)
        if state == STATE_MENU and not show_help:
            if name == 'up':
                menu_move(-1)
            elif name == 'down':
                menu_move(1)
            elif name == 'left':
                menu_level(-1)
            else:
                menu_level(1)
    glutPostRedisplay()


def specialUpListener(key, x, y):
    name = SPECIAL.get(key)
    if name:
        held.discard(name)


MENU_ROW_Y = (45, 5, -35)


def menu_row_at(x, y):
    for i, ry in enumerate(MENU_ROW_Y):
        if -300 <= x <= 300 and ry - 12 <= y <= ry + 24:
            return i
    return None


def mouseListener(button, state_, x, y):
    global restart_game, paused, menu_choice, help_paused

    if button != GLUT_LEFT_BUTTON or state_ != GLUT_DOWN:
        return
    c_X, c_y = convert_coordinate(x, y)

    if state == STATE_INTRO:
        end_intro()
        glutPostRedisplay()
        return

    if show_help:
        toggle_help()
        glutPostRedisplay()
        return

    if state == STATE_MENU:
        row = menu_row_at(c_X, c_y)
        if row is not None:
            menu_choice = row
            if row in (0, 1) and c_X > 150:
                menu_level(-1 if c_X < 232 else 1)     # the < and > round the level
            else:
                menu_activate()
        glutPostRedisplay()
        return

    if math.hypot(c_X - 100, c_y + 350) <= 22:
        go_to_menu()
    elif math.hypot(c_X - 200, c_y + 350) <= 22:
        toggle_help()
    elif state in (STATE_ROUND_OVER, STATE_MATCH_OVER):
        if banner_settled():
            if state == STATE_ROUND_OVER:
                next_round()
            else:
                reset_game()
    elif math.hypot(c_X + 100, c_y + 350) <= 22:
        restart_game = True
    elif math.hypot(c_X, c_y + 350) <= 22:
        paused = not paused
        help_paused = False

    glutPostRedisplay()


# ====================================================================== #
#  Title lettering and the intro
#
#  The name is drawn in its own pixel font rather than a GLUT bitmap font,
#  which cannot be scaled: each letter is a 5 x 7 grid, and each lit cell a
#  small square filled by scanline, with a darker copy stepped down and to the
#  right behind it for depth. Because every cell is placed by a translation
#  and sized by a scale, the same lettering can rise out of the water in the
#  intro and then shrink and slide up to become the title-screen heading.
# ====================================================================== #

TITLE_FONT = {
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
}
TITLE_LINES = ("SUBMARINE", "SAGA")
TITLE_ROWS = 7


def title_cells(text):
    """The lit cells (column, row) of a line of lettering, and its width in cells."""
    cells = []
    col = 0
    for ch in text:
        for r, row in enumerate(TITLE_FONT[ch]):
            for c, bit in enumerate(row):
                if bit == '#':
                    cells.append((col + c, r))
        col += 6
    return cells, col - 1


TITLE_CELLS = [title_cells(line) for line in TITLE_LINES]

# (centre x, centre y, cell size) of each line: big in the intro, small as
# the heading of the title screen
INTRO_LAYOUT = ((0.0, 95.0, 13.0), (0.0, -15.0, 13.0))
MENU_LAYOUT = ((0.0, 188.0, 5.0), (0.0, 146.0, 5.0))

TITLE_TOP = (1.0, 0.93, 0.55)       # the face runs from gold at the top...
TITLE_BOTTOM = (0.97, 0.50, 0.18)   # ...to orange at the bottom
TITLE_DEPTH = (0.05, 0.09, 0.18)


def title_row_color(r):
    """Gold at the top of a capital, orange at the baseline, a shade darker
    again in a g's tail below it."""
    if r <= 6:
        return mix(TITLE_BOTTOM, TITLE_TOP, 1.0 - r / 6.0)
    return mix(TITLE_BOTTOM, (0.0, 0.0, 0.0), 0.12 * (r - 6))


def title_cell_spot(line, col, r, layout):
    """Bottom left corner of a cell, and the cell size, for a layout."""
    cx, cy, cell = layout[line]
    width = TITLE_CELLS[line][1]
    return cx + (col - width / 2.0) * cell, cy + (3.5 - r) * cell, cell


def cell_geometry(cell):
    """Square size, extrusion layers and the step between them, for a cell size."""
    size = max(2, cell - max(1, int(round(cell / 6.0))))
    steps = max(1, int(round(cell / 4.0)))
    shift = max(1.0, cell / 8.0)
    return size, steps, shift


def glyph_part(ch, cell, part):
    """
    One layer of one letter as a single shape, relative to the letter's top
    left corner: ('face', row) is that row of its face, ('depth', k) the k-th
    step of its extrusion. A letter is drawn as a handful of these, each a
    translated display list, rather than cell by cell.
    """
    def build():
        size, steps, shift = cell_geometry(cell)
        square = [(x, y) for y in range(0, size + 1, 2) for x in range(0, size + 1, 2)]
        pts = []
        for r, row in enumerate(TITLE_FONT[ch]):
            if part[0] == 'face' and r != part[1]:
                continue
            for c, bit in enumerate(row):
                if bit != '#':
                    continue
                ox = c * cell + (part[1] * shift if part[0] == 'depth' else 0)
                oy = -r * cell - size - (part[1] * shift if part[0] == 'depth' else 0)
                pts.extend((ox + x, oy + y) for x, y in square)
        return pts
    return cached_shape(('glyph', ch, cell, part), build)


def draw_title(layout, t, reveal=None, shine=None, bob=0.0):
    """
    The lettering. reveal(x, y) gives the time a letter appears, for the
    intro; shine is the x of a band of light passing over it; bob is how far
    the letters sway with the water, as a share of a cell.
    """
    letters = []
    for line, text in enumerate(TITLE_LINES):
        cx, cy, cell_f = layout[line]
        cell = max(2, int(round(cell_f)))
        width = TITLE_CELLS[line][1]
        for j, ch in enumerate(text):
            # placed on the exact (animated) cell size, drawn at the nearest whole one
            x = cx + (j * 6 - width / 2.0) * cell_f
            y = cy + 3.5 * cell_f
            if reveal is not None:
                start = reveal(x + 2.5 * cell_f, y - 3.5 * cell_f)
                if t < start:
                    continue
                # it rises out of the water, easing to a stop
                u = min(1.0, (t - start) / 0.45)
                y -= 34.0 * (1.0 - u) ** 2
            if bob:
                y += sin(t * 2.2 + x * 0.015) * cell_f * bob
            letters.append((ch, int(round(x)), int(round(y)), cell))
    # the depth of every letter first, under all the faces
    for ch, x, y, cell in letters:
        size, steps, shift = cell_geometry(cell)
        for k in range(steps, 0, -1):
            set_color(mix(TITLE_DEPTH, (0.0, 0.0, 0.0), k / (steps + 1.0)))
            draw_points_batch(translate(glyph_part(ch, cell, ('depth', k)), x, y), 2)
    for ch, x, y, cell in letters:
        for r in range(TITLE_ROWS):
            set_color(title_row_color(r))
            draw_points_batch(translate(glyph_part(ch, cell, ('face', r)), x, y), 2)
    if shine is None:
        return
    # a band of light: only the cells inside it are drawn again, lighter
    for ch, x, y, cell in letters:
        size = cell_geometry(cell)[0]
        for r, row in enumerate(TITLE_FONT[ch]):
            for c, bit in enumerate(row):
                if bit != '#':
                    continue
                qx, qy = x + c * cell, y - r * cell
                if abs(qx - qy * 0.6 - shine) < cell * 2.4:
                    face = mix(title_row_color(r), (1.0, 1.0, 1.0), 0.8)
                    fill_rectangle(face, qx, qy - size, qx + size, qy, step=2)


def lerp_layout(a, b, p):
    return tuple(tuple(u + (v - u) * p for u, v in zip(la, lb)) for la, lb in zip(a, b))


INTRO_TIME = 4.4
SONAR_ORIGIN = (0.0, 40.0)
SONAR_SPEED = 430.0
INTRO_SHRINK = 3.5              # when the lettering starts moving to the title screen
MENU_PANEL = (-470, -292, 470, 214)
intro_t = 0.0


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def intro_reveal(x, y):
    """A cell appears the moment the sonar ping reaches it."""
    return 0.2 + math.hypot(x - SONAR_ORIGIN[0], y - SONAR_ORIGIN[1]) / SONAR_SPEED


def intro_sub_x(t):
    return -800.0 + t * 400.0


def draw_intro():
    t = intro_t
    ox, oy = SONAR_ORIGIN
    # three sonar pings, spreading and fading into the water
    for k in range(3):
        r = (t - 0.1 - k * 0.5) * SONAR_SPEED * 1.1
        if 4 < r < 780:
            fade = r / 780.0
            draw_hollow_circle(ox, oy, int(r), mix((0.55, 1.0, 1.0), PAL['water_top'], fade), 3)
    # a submarine glides past underneath
    draw_menu_sub(intro_sub_x(t), -150, 1, 1)

    p = ease((t - INTRO_SHRINK) / (INTRO_TIME - INTRO_SHRINK))
    if p > 0:
        # the title screen's panel opens out from the middle behind the name
        x0, y0, x1, y1 = MENU_PANEL
        cx, cy = 0.0, (y0 + y1) / 2.0
        draw_panel(cx + (x0 - cx) * p, cy + (y0 - cy) * p, cx + (x1 - cx) * p,
                   cy + (y1 - cy) * p, (0.25, 0.65, 0.85), (0.02, 0.06, 0.14))
    shine = -480 + (t - 2.2) * 1100 if 2.2 < t < 3.3 else None
    draw_title(lerp_layout(INTRO_LAYOUT, MENU_LAYOUT, p), t,
               reveal=intro_reveal, shine=shine, bob=0.12 * (1 - p))


def draw_intro_text():
    t = intro_t
    if t < INTRO_SHRINK:
        if t > 1.5:
            render_text("A Torpedo Duel under the Waves", 0, -105, FONT, (0.85, 0.93, 1.0),
                        center=True, shadow=True)
        if t > 2.0:
            render_text("CSE423 Computer Graphics   -   BRAC University", 0, -130,
                        FONT_SMALL, (0.70, 0.80, 0.90), center=True, shadow=True)
    if sin(time.time() * 5) > -0.3:
        render_text("Press any key", 0, -345, FONT_SMALL, (0.95, 0.97, 1.0),
                    center=True, shadow=True)


def update_intro(dt):
    global intro_t
    before = intro_t
    intro_t += dt
    if before < 0.1 <= intro_t:
        play('sonar')
    # bubbles off the passing submarine's propeller
    if random.random() < 0.6:
        particles.append(Particle(intro_sub_x(intro_t) - 70 + random.uniform(-6, 6),
                                  -150 + random.uniform(-10, 10),
                                  random.uniform(-40, -10), random.uniform(20, 60),
                                  0.9, (0.85, 0.95, 1.0), 3))
    if intro_t >= INTRO_TIME:
        end_intro()


def end_intro():
    global state
    if state == STATE_INTRO:
        state = STATE_MENU
        held.clear()


# ====================================================================== #
#  Screens: title, help, pause, round results
#
#  Each screen is laid out once as a list of items, and the list is drawn
#  twice: its shapes with the points, then its words after the points have
#  been flushed, because bitmap text has to go on top.
# ====================================================================== #

ARROWS = {'UP': (0, 1), 'DOWN': (0, -1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}
CAP_H = 26


def add_cap(items, x, y, label):
    """A key drawn as a key. x, y is its bottom left corner."""
    w = 30 if label in ARROWS else max(30, int(text_width(label, FONT_SMALL)) + 18)
    items.append(('cap', x, y, w, label))
    return x + w + 6


def add_text(items, x, y, text, font=FONT_SMALL, color=(0.85, 0.90, 0.96), center=False):
    items.append(('text', x, y, text, font, color, center))


def caps_row(items, x, y, labels, words, color=(0.85, 0.90, 0.96)):
    """Keys then what they do. Returns where the next group can start."""
    for lab in labels:
        x = add_cap(items, x, y, lab)
    add_text(items, x + 4, y + 8, words, FONT_SMALL, color)
    return x + 4 + text_width(words, FONT_SMALL) + 16


def draw_items_shapes(items):
    for it in items:
        kind = it[0]
        if kind == 'panel':
            _, x0, y0, x1, y1, border = it
            draw_panel(x0, y0, x1, y1, border, (0.03, 0.06, 0.12))
            draw_outline(mix(border, (0, 0, 0), 0.4),
                         [[x0 + 6, y0 + 6], [x1 - 6, y0 + 6], [x1 - 6, y1 - 6], [x0 + 6, y1 - 6]])
        elif kind == 'cap':
            _, x, y, w, label = it
            fill_rectangle((0.08, 0.09, 0.12), x, y - 3, x + w, y + CAP_H - 3, step=2)
            fill_rectangle((0.20, 0.23, 0.30), x, y, x + w, y + CAP_H, step=2)
            draw_outline((0.60, 0.67, 0.78), [[x, y], [x + w, y], [x + w, y + CAP_H], [x, y + CAP_H]])
            if label in ARROWS:
                dx, dy = ARROWS[label]
                cx, cy = x + w / 2, y + CAP_H / 2
                col = (0.95, 0.97, 1.0)
                tipx, tipy = cx + dx * 7, cy + dy * 7
                draw_lines(col, cx - dx * 7, cy - dy * 7, tipx, tipy, 2)
                draw_lines(col, tipx, tipy, tipx - dx * 5 - dy * 5, tipy - dy * 5 - dx * 5, 2)
                draw_lines(col, tipx, tipy, tipx - dx * 5 + dy * 5, tipy - dy * 5 + dx * 5, 2)
        elif kind == 'rect':
            _, x0, y0, x1, y1, col = it
            fill_rectangle(col, x0, y0, x1, y1, step=3)
        elif kind == 'pickup':
            _, x, y, k = it
            draw_pickup_icon(x, y, 18, k)
        elif kind == 'mine':
            draw_mine_icon(it[1], it[2])
        elif kind == 'charge':
            _, x, y = it
            draw_filled_circle(x, y, 7, (0.12, 0.12, 0.14))
            draw_hollow_circle(x, y, 11, (0.85, 0.25, 0.2), 2)
            draw_lines((0.5, 0.5, 0.5), x, y + 11, x, y + 20, 2)
        elif kind == 'fin':
            _, x, y = it
            fill_polygon((0.40, 0.46, 0.56), [(x - 14, y - 10), (x, y + 16), (x + 14, y - 10)], step=2)
        elif kind == 'sub':
            _, x, y, num, facing = it
            draw_menu_sub(x, y, num, facing)
        elif kind == 'title':
            # a band of light passes over the name every few seconds
            t = time.time()
            phase = t % 6.0
            draw_title(MENU_LAYOUT, t, shine=-330 + phase * 700 if phase < 1.0 else None)


def draw_items_text(items):
    for it in items:
        if it[0] == 'text':
            _, x, y, text, font, color, center = it
            render_text(text, x, y, font, color, center=center)
        elif it[0] == 'cap' and it[4] not in ARROWS:
            _, x, y, w, label = it
            render_text(label, x + w / 2, y + 8, FONT_SMALL, (0.95, 0.97, 1.0), center=True)


def draw_menu_sub(cx, cy, num, facing):
    """A small submarine on the title screen, in each team's colours."""
    team = TEAM[num]
    hull = team['hull']
    dark = mix(hull, (0, 0, 0), 0.45)
    d = facing
    body = [(cx - 52, cy + 17), (cx + 52, cy + 17), (cx + 52, cy - 17), (cx - 52, cy - 17)]
    draw_filled_circle(cx - 52, cy, 17, hull)
    draw_filled_circle(cx + 52, cy, 17, hull)
    fill_polygon(hull, body, step=2)
    fill_polygon(mix(hull, (1, 1, 1), 0.22),
                 [(cx - 52, cy + 17), (cx + 52, cy + 17),
                  (cx + 52, cy + 9), (cx - 52, cy + 9)], step=2)
    fill_polygon(dark, [(cx - 16 * d, cy + 17), (cx + 14 * d, cy + 17),
                        (cx + 6 * d, cy + 34), (cx - 16 * d, cy + 34)], step=2)
    fill_polygon(dark, [(cx - 62 * d, cy - 5), (cx - 74 * d, cy - 5),
                        (cx - 74 * d, cy + 5), (cx - 62 * d, cy + 5)], step=2)
    fill_polygon(dark, [(cx - 74 * d, cy - 15), (cx - 66 * d, cy - 15),
                        (cx - 66 * d, cy + 15), (cx - 74 * d, cy + 15)], step=2)
    draw_filled_circle(cx - 18, cy, 7, team['trim'])
    draw_filled_circle(cx + 16, cy, 7, team['trim'])
    draw_outline(mix(hull, (0, 0, 0), 0.55), body)


def team_name(num):
    """A team's name as the screens show it: MARKAVA is Markava. The capitals
    stay for the in-game labels and call-outs."""
    return TEAM[num]['name'].title()


def level_name(i=None):
    return CPU_LEVELS[cpu_level if i is None else i]['name'].title()


def menu_items():
    items = [('panel', -470, -292, 470, 214, (0.25, 0.65, 0.85)),
             ('sub', -250, 112, 1, 1), ('sub', 250, 112, 2, -1)]
    items.append(('title',))
    add_text(items, 0, 102, "A Torpedo Duel under the Waves", FONT_SMALL, (0.70, 0.80, 0.90), True)

    rows = ["1 Player   -   Against the computer",
            "2 Players   -   One keyboard",
            "How to play"]
    for i, (text, y) in enumerate(zip(rows, MENU_ROW_Y)):
        on = i == menu_choice
        if on:
            items.append(('rect', -300, y - 12, 300, y + 24, (0.10, 0.22, 0.34)))
        col = (1.0, 0.88, 0.40) if on else (0.78, 0.84, 0.92)
        add_text(items, -262, y, ("> " if on else "   ") + text, FONT, col)
        if i in (0, 1):
            add_text(items, 232, y, f"<  {level_name()}  >", FONT, col, True)

    # the controls are on the title screen itself, not one menu away
    y = -118
    add_text(items, -430, y + 34, f"Player 1  -  {team_name(1)}", FONT_SMALL, TEAM[1]['trim'])
    caps_row(items, -430, y, ['W', 'A', 'S', 'D'], "Move and aim")
    x = caps_row(items, -430, y - 36, ['Space'], "Torpedo")
    x = caps_row(items, x, y - 36, ['F'], "Heavy")
    x = caps_row(items, x, y - 36, ['E'], "Dash")
    caps_row(items, x, y - 36, ['Q'], "Decoy")
    add_text(items, 40, y + 34, f"Player 2  -  {team_name(2)}", FONT_SMALL, TEAM[2]['trim'])
    caps_row(items, 40, y, ['UP', 'LEFT', 'DOWN', 'RIGHT'], "Move and aim")
    x = caps_row(items, 40, y - 36, ['P'], "Torpedo")
    x = caps_row(items, x, y - 36, ['O'], "Heavy")
    x = caps_row(items, x, y - 36, ['L'], "Dash")
    caps_row(items, x, y - 36, ['K'], "Decoy")
    add_text(items, 0, -190, LEVEL_NOTES[cpu_level], FONT_SMALL, (0.70, 0.80, 0.90), True)

    rec = records
    levels = "   ".join(f"{level_name(i)} {rec['wins'][i]}-{rec['losses'][i]}"
                        for i in range(len(CPU_LEVELS)))
    add_text(items, 0, -222, f"Record vs computer:   {levels}      Best win streak {rec['best_streak']}",
             FONT_SMALL, (0.95, 0.80, 0.45), True)
    add_text(items, 0, -262, "W/S  Choose     A/D  Level     Enter  Start     H  Help     M  Sound     N  Night",
             FONT_SMALL, (0.60, 0.68, 0.78), True)
    # who made it, on the sand under the panel
    half = text_width(CREDIT_LINE, FONT_SMALL) / 2 + 14
    items.append(('rect', -half, -342, half, -318, (0.03, 0.06, 0.12)))
    add_text(items, 0, -334, CREDIT_LINE, FONT_SMALL, (0.85, 0.90, 0.96), True)
    return items


def help_items():
    items = [('panel', -610, -332, 610, 224, (1.0, 0.85, 0.35))]
    add_text(items, 0, 190, "How to Play", FONT_BIG, (1.0, 0.92, 0.55), True)

    for num, x in ((1, -560), (2, 60)):
        team = TEAM[num]
        who = team_name(num)
        if vs_cpu:
            who += "  (you)" if num == 1 else "  (computer)"
        add_text(items, x, 152, f"Player {num}  -  {who}", FONT, team['trim'])
        # what this level does not have is greyed out and says where it is
        on, off = (0.85, 0.90, 0.96), (0.42, 0.46, 0.52)
        heavy_col = on if rule('heavy') else off
        decoy_col = on if rule('decoy') else off
        if not rule('heavy'):
            heavy_note = "   (Normal and Hard)"
        elif not rule('homing'):
            heavy_note = ", runs straight"
        else:
            heavy_note = ", homes in"
        decoy_note = "" if rule('decoy') else "   (Hard)"
        if num == 1:
            caps_row(items, x, 112, ['W', 'A', 'S', 'D'], "Swim, and swing the torpedo tube round")
            caps_row(items, x, 80, ['Space'], "Torpedo  -  1 damage, quick reload   (C too)")
            caps_row(items, x, 48, ['F'], "Heavy torpedo  -  3 damage" + heavy_note, heavy_col)
            nx = caps_row(items, x, 16, ['E'], "Dash")
            caps_row(items, nx, 16, ['Q'], "Decoy  -  pulls heavy torpedoes away" + decoy_note,
                     decoy_col)
        else:
            caps_row(items, x, 112, ['UP', 'LEFT', 'DOWN', 'RIGHT'], "Swim, and swing the tube")
            caps_row(items, x, 80, ['P'], "Torpedo  -  1 damage   (Enter, numpad 0)")
            caps_row(items, x, 48, ['O'], "Heavy torpedo  -  3 damage" + heavy_note, heavy_col)
            nx = caps_row(items, x, 16, ['L'], "Dash")
            caps_row(items, nx, 16, ['K'], "Decoy" + decoy_note, decoy_col)
    if vs_cpu:
        add_text(items, 0, -12, "Against the computer you are Markava, and either set of keys steers you.",
                 FONT_SMALL, (0.70, 0.80, 0.90), True)

    rules = [
        "The tube turns towards the keys you hold, and stays there when you let go: aim, then fire.",
        "The dotted sight shows the shot.  Close to the enemy it snaps on and turns red - fire!",
        "10 lives each.  Win 2 rounds to win the match.  After 1:00 comes Sudden Death.",
        "Torpedoes also destroy mines, sharks, depth charges, and the other player's torpedoes.",
    ]
    for i, line in enumerate(rules):
        add_text(items, -560, -40 - i * 24, f"{i + 1}.  {line}", FONT, (0.92, 0.95, 1.0))

    y = -160
    add_text(items, -560, y + 22, "Swim through these", FONT_SMALL, (0.65, 0.95, 0.70))
    for i, (k, label) in enumerate(((KIND_HEALTH, f"+{HEALTH_PICKUP} Health"), (KIND_SHIELD, "Shield"),
                                    (KIND_RAPID, "Rapid fire"), (KIND_BOOST, "Speed"))):
        x = -540 + i * 150
        items.append(('pickup', x, y - 12, k))
        add_text(items, x + 26, y - 16, label)
    add_text(items, 60, y + 22, "Keep away from these", FONT_SMALL, (1.0, 0.55, 0.45))
    items.append(('charge', 80, y - 16))
    add_text(items, 100, y - 16, "Depth charge - lands on the marks")
    items.append(('mine', 350, y - 12))
    add_text(items, 378, y - 16, "Mine - a ring means arming")

    y = -240
    items.append(('fin', 80, y - 8))
    add_text(items, 100, y - 16, "Shark - its fin shows at the surface first")
    add_text(items, -560, y - 16, "The wreck on the seabed blocks shots - use it as cover.",
             FONT_SMALL)
    add_text(items, -560, y - 38, f"At {LAST_STAND_AT} lives or fewer you swim and reload faster:"
             " Last Stand.", FONT_SMALL)
    add_text(items, 0, -312, "I  Pause     R  Restart     N  Day / night     M  Sound     Esc  Menu"
             "          H, Enter or click to close", FONT_SMALL, (0.60, 0.68, 0.78), True)
    return items


def pause_items():
    items = [('panel', -250, -20, 250, 110, (1.0, 0.8, 0.3))]
    add_text(items, 0, 64, "Paused", FONT_BIG, (1.0, 0.85, 0.35), True)
    add_text(items, 0, 24, "I  Resume      H  Help      R  Restart      Esc  Menu",
             FONT_SMALL, (0.85, 0.90, 0.96), True)
    return items


def stats_line(num):
    st = stats[num]
    acc = int(round(100 * st['hits'] / st['shots'])) if st['shots'] else 0
    return (f"{team_name(num)}   Hits {st['hits']} / {st['shots']}   "
            f"Accuracy {acc}%   Best combo {st['best_combo']}")


def banner_items():
    if state == STATE_ROUND_OVER:
        title = f"{team_name(round_winner)} takes round {round_no}"
        more = "Press Enter for the next round"
    elif state == STATE_MATCH_OVER:
        if vs_cpu:
            title = "You win the match!" if match_winner == 1 else "The computer wins the match"
        else:
            title = f"{team_name(match_winner)} wins the match!"
        more = "Enter to play again          Esc for the menu"
    else:
        return []
    items = [('panel', -450, -120, 450, 100, (1.0, 0.85, 0.35))]
    add_text(items, 0, 58, title, FONT, (1.0, 0.92, 0.55), True)
    add_text(items, 0, 28, f"{team_name(1)}  {score[1]}   -   {score[2]}  {team_name(2)}",
             FONT, (0.9, 0.95, 1.0), True)
    add_text(items, 0, -4, stats_line(1), FONT_SMALL, TEAM[1]['trim'], True)
    add_text(items, 0, -24, stats_line(2), FONT_SMALL, TEAM[2]['trim'], True)
    if state == STATE_MATCH_OVER and vs_cpu:
        lv = cpu_level
        add_text(items, 0, -54,
                 f"Against {level_name(lv)}:  {records['wins'][lv]} won, {records['losses'][lv]} lost"
                 f"      Win streak {records['streak']}  (best {records['best_streak']})",
                 FONT_SMALL, (0.95, 0.80, 0.45), True)
    if banner_settled():
        add_text(items, 0, -96, more, FONT_SMALL, (0.85, 0.90, 0.96), True)
    return items


# ====================================================================== #
#  Frame
# ====================================================================== #

def display():
    global background_update_needed

    glClear(GL_COLOR_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # the screen shake is a small offset on the projection, so everything moves
    global shake_x, shake_y
    shake_x = random.uniform(-shake, shake) if shake > 0.2 else 0.0
    shake_y = random.uniform(-shake, shake) if shake > 0.2 else 0.0
    glOrtho(WORLD_L + shake_x, WORLD_R + shake_x,
            WORLD_B + shake_y, WORLD_T + shake_y, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if background_list is None or background_update_needed:
        create_background_list()
        create_wreck_list()
        create_static_list()
        background_update_needed = False
    if background_list:
        glCallList(background_list)

    t = time.time()

    draw_rain(rains)
    draw_light_rays(t)
    draw_sun_moon(t)
    draw_seaweed(t)
    if wreck_list:
        flush_points()
        glCallList(wreck_list)
    draw_fishes()
    draw_surface(t)
    boatMaker(t)

    in_game = state not in (STATE_MENU, STATE_INTRO)
    if in_game:
        draw_bubble()
        draw_decoys()
        draw_unique_circles()
        draw_mines(t)
        draw_bomb_warnings()
        draw_shark_warnings()
        draw_bombs()
        draw_torpedo(torpedo1)
        draw_torpedo(torpedo2)
        for shark in sharks:
            draw_shark(shark, t)
        for sub in submarines:
            draw_aim_line(sub)
        draw_submarine(submarines)
        draw_sub_markers()
        draw_threat_warnings()

    draw_particles()

    # Everything above is drawn with points. Text is not, so every point has to
    # reach the screen before any text goes on top of it, or the next batch of
    # points covers the text up.
    overlay = []
    if state == STATE_INTRO:
        draw_intro()
    elif not in_game:
        overlay = menu_items()
    else:
        if static_list:
            flush_points()
            glCallList(static_list)
        draw_button_bar()
        draw_hud_shapes()
        overlay = banner_items()
        if paused and not show_help:
            overlay = overlay + pause_items()
    if show_help:
        # the help screen replaces whatever else was up, rather than sitting
        # on top of it: bitmap text cannot be covered, so it would show through
        overlay = help_items()
    draw_items_shapes(overlay)

    flush_points()

    if in_game:
        draw_hud_text()
        if not show_help and not paused and not banner_items():
            draw_world_text()
    if state == STATE_INTRO:
        draw_intro_text()
    draw_items_text(overlay)

    glutSwapBuffers()


def shift_timers(dt):
    """Move every wall clock deadline forward, for time the game did not run."""
    global start_time1, start_time2, tor_time1, tor_time2, announce_until
    global last_spawn_time, last_spawn_time_shark, last_mine_time
    start_time1 += dt
    start_time2 += dt
    tor_time1 += dt
    tor_time2 += dt
    for n in (1, 2):
        heavy_time[n] += dt
        decoy_time[n] += dt
    announce_until += dt
    last_spawn_time += dt
    last_spawn_time_shark += dt
    last_mine_time += dt


def animate():
    global last_frame, restart_game, shake, fps_shown, _fps_frames, _fps_clock
    global hitstop, slowmo, round_clock

    now = time.time()
    dt = now - last_frame
    if dt < 0.008:
        time.sleep(0.002)      # do not spin a core while waiting for the frame
        return
    last_frame = now
    dt = min(dt, 0.05)          # never let one slow frame teleport anything

    _fps_frames += 1
    if now - _fps_clock >= 0.5:
        fps_shown = _fps_frames / (now - _fps_clock)
        _fps_frames, _fps_clock = 0, now

    if restart_game:
        reset_game()
        restart_game = False

    shake = max(0.0, shake - dt * 34)
    t = now

    running = state in (STATE_PLAY, STATE_SINKING) and not paused
    if paused:
        # the cooldowns below are wall clock stamps and the wall clock does not
        # stop when the game does. Pushing them along by dt keeps them the same
        # distance in the past, otherwise a thirty second pause leaves every
        # timer overdue and the mines, the shark and both torpedoes all arrive
        # in the first frame after unpausing.
        shift_timers(dt)
    elif running and hitstop > 0:
        # a hit freezes everything for a blink; the timers wait with it
        hitstop -= dt
        shift_timers(dt)
        running = False

    if state == STATE_INTRO:
        update_intro(dt)
    update_fishes(dt, t)
    update_particles(dt)
    update_rains(dt)

    if running:
        sdt = dt * (SLOWMO_SCALE if slowmo > 0 else 1.0)
        slowmo = max(0.0, slowmo - dt)
        before = round_clock
        round_clock += sdt
        if before < 0 <= round_clock:
            play('go')
        if before < SUDDEN_DEATH_AT <= round_clock:
            announce("SUDDEN DEATH  -  THE SEA GETS ANGRY", 2.5)
            play('go')
        apply_input(sdt)
        apply_physics(sdt)
        if round_clock >= 0:
            handle_spawn_events(now, sdt, t)
            update_bombs(sdt)
        update_bubbles(now, sdt)
        update_submarine_positions(sdt)
        update_decoys(sdt)
        update_torpedoes(sdt)
        update_popups(dt)
    elif state in (STATE_ROUND_OVER, STATE_MATCH_OVER):
        update_submarine_positions(dt)
        update_popups(dt)
        if state == STATE_MATCH_OVER and random.random() < dt * 3.5:
            # fireworks over the water in the winner's colours
            trim = TEAM[match_winner]['trim']
            burst(random.uniform(-600, 600), random.uniform(270, 360), 55,
                  [trim, mix(trim, (1, 1, 1), 0.6), (1.0, 1.0, 1.0)],
                  speed=240, life=1.3, size=6)

    glutPostRedisplay()


def reshape(width, height):
    global W_Width, W_Height, background_update_needed
    W_Width, W_Height = max(1, width), max(1, height)
    fit_viewport(W_Width, W_Height)
    glViewport(VIEW_X, VIEW_Y, VIEW_W, VIEW_H)
    # the display lists have their point sizes baked in, so they are rebuilt
    # for the new scale
    background_update_needed = True


def init():
    glClearColor(0, 0, 0, 0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(WORLD_L, WORLD_R, WORLD_B, WORLD_T, -1, 1)
    glMatrixMode(GL_MODELVIEW)


glutInit()
glutInitWindowSize(W_Width, W_Height)
glutInitWindowPosition(0, 0)
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB)

wind = glutCreateWindow(b"Submarine Saga")
init()
init_sound()
glutDisplayFunc(display)
glutIdleFunc(animate)
glutReshapeFunc(reshape)
# without this, X11 sends a key up and a key down for every auto repeat, which
# makes the held key set flicker and stutters the movement
glutIgnoreKeyRepeat(1)
glutKeyboardFunc(keyboardListener)
glutKeyboardUpFunc(keyboardUpListener)
glutEntryFunc(entryListener)
glutSpecialFunc(specialKeyListener)
glutSpecialUpFunc(specialUpListener)
glutMouseFunc(mouseListener)
glutMainLoop()

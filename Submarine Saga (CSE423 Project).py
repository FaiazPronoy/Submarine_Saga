# OpenGL Imports
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Standard Library Imports
import math
import time
import random

from math import pi, sin, cos

# numpy makes the point batches a little cheaper to hand to OpenGL, but the
# game has to run on a machine where only PyOpenGL is installed, so it is
# optional and there is a plain fallback below.
try:
    import numpy
except ImportError:
    numpy = None

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
state = STATE_MENU
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

# Timing
start_time1 = time.time()
start_time2 = time.time() + 3
tor_time1 = time.time() - 2
tor_time2 = time.time() - 2
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
SUB_DRAG = 3.1            # water resistance, gives the glide
speed_rad = 0.015
speed_tor = 1000.0
fall_speed = 210
TORPEDO_COOLDOWN = 1.0
RAPID_COOLDOWN = 0.5

# Collision sizes, all measured off the art, so a near miss on screen is a
# near miss in the maths. They live together here rather than at the call
# sites, because they only make sense next to each other.
HULL_END_R = 24          # the round nose and tail of a hull
TORPEDO_R = 12
BOMB_R = 9
MINE_R = 18
SHARK_R = 26            # the shark is drawn 90 long, so one circle at the
SHARK_NOSE = 34         # centre leaves the snout outside its own hitbox.
SHARK_NOSE_R = 16       # the nose gets a second, smaller circle
PICKUP_GRAB = 14         # added to the pickup's own radius
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


def convert_coordinate(x, y):
    """Window pixels to world units, with the screen shake taken into account."""
    return ((x / W_Width) * (WORLD_R - WORLD_L) + WORLD_L + shake_x,
            WORLD_T - (y / W_Height) * (WORLD_T - WORLD_B) + shake_y)


# ====================================================================== #
#  Point batching
#
#  Everything on screen is still drawn with GL_POINTS through the midpoint
#  algorithms below. The original called glBegin/glEnd once per point, which
#  held the game at about 12 frames a second. Points are now collected into
#  runs of the same colour and size and sent in one go. The drawing order is
#  kept exactly, so what ends up on screen is identical.
# ====================================================================== #

_cur_color = (1.0, 1.0, 1.0)
_runs = []


def set_color(c):
    global _cur_color
    _cur_color = (c[0], c[1], c[2])


def draw_points_batch(points, size):
    """Adds to the run in progress when the colour and size match."""
    if not points:
        return
    if _runs and _runs[-1][0] == _cur_color and _runs[-1][1] == size:
        _runs[-1][2].extend(points)
    else:
        _runs.append([_cur_color, size, list(points)])


def flush_points():
    """
    Sends every collected run to OpenGL, in the order it was drawn.

    The points go across as one vertex array per run rather than one
    glVertex2f call each. Same GL_POINTS, same pixels, but the per point
    Python call is gone, which is where all the time was going.
    """
    if numpy is None:
        for color, size, pts in _runs:
            if not pts:
                continue
            glColor3f(color[0], color[1], color[2])
            glPointSize(size)
            glBegin(GL_POINTS)
            for x, y in pts:
                glVertex2f(x, y)
            glEnd()
        _runs.clear()
        return

    glEnableClientState(GL_VERTEX_ARRAY)
    for color, size, pts in _runs:
        if not pts:
            continue
        glColor3f(color[0], color[1], color[2])
        glPointSize(size)
        arr = numpy.asarray(pts, dtype=numpy.float32)
        glVertexPointer(2, GL_FLOAT, 0, arr)
        glDrawArrays(GL_POINTS, 0, len(pts))
    glDisableClientState(GL_VERTEX_ARRAY)
    _runs.clear()


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


def convertToZoneM(color, zone, points, s=2):
    set_color(color)
    if zone == 0:
        out = points
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
    draw_points_batch(out, s)


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
    draw_points_batch([(x + dx, y + dy) for dx, dy in disc_points(rad)], 2)


def draw_lines(color, x1, y1, x2, y2, s=2):
    zone = findZone(x1, y1, x2, y2)
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    x1, y1, x2, y2 = convertToZone0(zone, x1, y1, x2, y2)
    points = MidPointLine(x1, y1, x2, y2)
    convertToZoneM(color, zone, points, s)


def draw_filled_circle(x, y, rad, color):
    filled_circle_helper(x, y, rad, color)
    set_color(color)
    draw_points_batch([(px, py) for group in zone_converter(x, y, circle_points(rad))
                       for px, py in group], 2)


def draw_hollow_circle(x, y, rad, color, s=2):
    set_color(color)
    draw_points_batch([(px, py) for group in zone_converter(x, y, circle_points(rad))
                       for px, py in group], s)


def draw_outline(color, vertices):
    """Outline of a polygon, drawn edge by edge with the midpoint line."""
    for i in range(len(vertices)):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % len(vertices)]
        draw_lines(color, x1, y1, x2, y2)


def fill_polygon(color, vertices, step=2):
    """
    Solid fill for a polygon, by scanline.

    The original only ever drew the outline of the submarine and called it
    filled, which is why the hulls looked like wireframes. Each scanline still
    ends up as a run of GL_POINTS.
    """
    if len(vertices) < 3:
        return
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
    set_color(color)
    draw_points_batch(pts, step)


def fill_rectangle(color, x_min, y_min, x_max, y_max, step=3):
    pts = []
    for y in range(int(y_min), int(y_max) + 1, step):
        for x in range(int(x_min), int(x_max) + 1, step):
            pts.append((x, y))
    set_color(color)
    draw_points_batch(pts, step)


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
    # only a shade lighter than the water it sits on, so it reads as light
    # coming through rather than as a pattern painted on top
    # only a shade lighter than the water behind them, and slanted, so they
    # read as light coming through the surface rather than painted bars
    # two passes: a wide faint one, then a narrow brighter one inside it, so
    # the edges fade instead of ending in a hard line
    for wide in (True, False):
        col = mix(PAL['water_top'], PAL['ray'], 0.05 if wide else 0.11)
        pts = []
        for i in range(5):
            x0 = -520 + i * 260 + sin(t * 0.3 + i * 1.7) * 30
            for k in range(0, 290, 6):
                f = k / 290.0
                w = (26 + 34 * f) if wide else (12 + 18 * f)
                x = x0 + k * 0.22
                y = SURFACE_Y - k
                pts.extend((x + dx, y) for dx in range(int(-w / 2), int(w / 2) + 1, 6))
        set_color(col)
        draw_points_batch(pts, 7)


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
    flush_points()
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
    flush_points()
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
    flush_points()
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
        tail = [(self.x + s * d, self.y), (self.x + s * 1.9 * d, self.y + s * 0.7),
                (self.x + s * 1.9 * d, self.y - s * 0.7)]
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
#  Torpedoes
# ====================================================================== #

class Torpedo:
    """
    A torpedo carries its own direction. The original stored only a vertical
    step and worked out the horizontal one from who fired it, which meant a
    torpedo could not be aimed and player two's shots climbed when they should
    have dived.
    """

    def __init__(self, x, y, vx, vy, owner):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.active = True
        self.owner = owner
        self.px, self.py = x, y   # where it was last frame, for swept hits
        self.trail = 0.0
        self.armed = 0.0        # travelled distance, used for the arming ring

    def center(self):
        return self.x, self.y


def draw_torpedo(torpedo_list):
    for tor in torpedo_list:
        if not tor.active:
            continue
        team = TEAM[tor.owner]
        cx, cy = tor.x, tor.y
        h = math.hypot(tor.vx, tor.vy) or 1.0
        ux, uy = tor.vx / h, tor.vy / h        # along the torpedo
        px, py = -uy, ux                       # across it

        def at(along, across):
            return (cx + ux * along + px * across, cy + uy * along + py * across)

        body = [at(26, 0), at(12, 7), at(-16, 7), at(-16, -7), at(12, -7)]
        fill_polygon((0.15, 0.16, 0.19), body, step=2)
        draw_outline((0.45, 0.48, 0.54), body)
        fill_polygon(team['trim'], [at(-14, 6), at(-24, 14), at(-20, 0)], step=2)
        fill_polygon(team['trim'], [at(-14, -6), at(-24, -14), at(-20, 0)], step=2)
        draw_filled_circle(*at(20, 0), 3, (1.0, 0.92, 0.6))


def spawn_trail(tor, dt):
    tor.trail += dt
    if tor.trail > 0.03:
        tor.trail = 0.0
        h = math.hypot(tor.vx, tor.vy) or 1.0
        particles.append(Particle(
            tor.x - tor.vx / h * 22, tor.y - tor.vy / h * 22 + random.uniform(-4, 4),
            -tor.vx / h * 40, random.uniform(6, 24), 0.45,
            (0.85, 0.94, 1.0), 3))


def hits_sub(sub, x, y, radius):
    """
    One test for every hazard: the hull box, then the two round ends.

    Every radius passed in here is measured off the art, so what looks like a
    clear miss on screen is a clear miss in the maths.
    """
    if not sub.control:
        return False
    if has_collided(AABB(x - radius, y - radius, radius * 2, radius * 2),
                    sub.get_bounding_box()):
        return True
    for cx, cy in (sub.circle1, sub.circle2):
        if math.hypot(x - cx, y - cy) <= radius + HULL_END_R:
            return True
    return False


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


def update_torpedoes(dt):
    """
    Torpedoes now hit each other, the mines and the sharks as well as the other
    player. That is what turns four separate hazards into one system: the mine
    between you and a pickup is something you can clear, and a torpedo coming
    at you is something you can shoot down.
    """
    for lst, target in ((torpedo1, sub22), (torpedo2, sub11)):
        for tor in lst:
            if not tor.active:
                continue
            tor.px, tor.py = tor.x, tor.y
            tor.x += tor.vx * dt
            tor.y += tor.vy * dt
            tor.armed += math.hypot(tor.vx, tor.vy) * dt
            spawn_trail(tor, dt)

            if not (WORLD_L - 60 < tor.x < WORLD_R + 60) or \
               not (SEABED_Y - 20 < tor.y < SURFACE_Y + 20):
                tor.active = False
                continue

            # the wreck on the seabed stops a torpedo, so it is real cover
            if wreck_blocks(tor.x, tor.y):
                tor.active = False
                burst(tor.x, tor.y, 16, [(0.7, 0.72, 0.75), (0.9, 0.85, 0.7)],
                      speed=150, life=0.5)
                continue

            for mine in mines:
                if mine.active and seg_dist(tor.px, tor.py, tor.x, tor.y,
                                            mine.x, mine.y) <= 24:
                    mine.active = False
                    tor.active = False
                    burst(mine.x, mine.y, 34, speed=280, life=0.8, size=5)
                    break
            if not tor.active:
                continue

            for shark in sharks:
                if shark.active and seg_dist(tor.px, tor.py, tor.x, tor.y,
                                             shark.x, shark.y) <= 34:
                    shark.active = False
                    tor.active = False
                    burst(shark.x, shark.y, 26, [(0.8, 0.25, 0.25), (0.9, 0.6, 0.5)],
                          speed=220, life=0.7)
                    break
            if not tor.active:
                continue

            if hits_sub(target, tor.x, tor.y, TORPEDO_R):
                tor.active = False
                burst(tor.x, tor.y, 30)
                damage(target, 1)

    # two torpedoes meeting cancel each other out
    for a in torpedo1:
        if not a.active:
            continue
        for b in torpedo2:
            if b.active and seg_dist(a.px - b.px, a.py - b.py,
                                     a.x - b.x, a.y - b.y, 0.0, 0.0) <= 26:
                a.active = b.active = False
                burst((a.x + b.x) / 2, (a.y + b.y) / 2, 24,
                      [(1.0, 0.9, 0.5), (0.9, 0.95, 1.0)], speed=210, life=0.6)
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
        self.life = 5
        self.max_life = 5
        # movement is now a velocity the keys push against, which is what makes
        # it glide instead of jumping a fixed distance per key event
        self.vx = 0.0
        self.vy = 0.0
        self.shield = 0.0
        self.rapid = 0.0
        self.boost = 0.0
        self.flash = 0.0
        self.prop_spin = 0.0

    @property
    def team(self):
        return TEAM[self.num]

    def parts(self):
        return (self.main_body, self.propeller, self.top_body,
                self.air_duct, self.door, self.lower_body)

    def move_by(self, dx, dy):
        for part in self.parts():
            for key in part:
                part[key][0] += dx
                part[key][1] += dy
        self.circle1 = [self.circle1[0] + dx, self.circle1[1] + dy]
        self.circle2 = [self.circle2[0] + dx, self.circle2[1] + dy]

    def rotate_by(self, radians):
        """Turn the whole submarine about its own centre.

        Only the sinking animation uses this. Every hit box in the game is
        axis aligned, so a tilted hull would not be tested honestly - but by
        the time this runs the submarine is out of the round and nothing is
        testing it. The pivot is the average of the four hull corners rather
        than center(), because that average is the one point a rotation
        leaves where it is.
        """
        corners = list(self.main_body.values())
        px = sum(p[0] for p in corners) / len(corners)
        py = sum(p[1] for p in corners) / len(corners)
        c, s = cos(radians), sin(radians)
        for part in self.parts():
            for key in part:
                x, y = part[key][0] - px, part[key][1] - py
                part[key][0] = px + x * c - y * s
                part[key][1] = py + x * s + y * c
        for circle in (self.circle1, self.circle2):
            x, y = circle[0] - px, circle[1] - py
            circle[0], circle[1] = px + x * c - y * s, py + x * s + y * c

    def center(self):
        b = self.main_body
        return ((b['mp1'][0] + b['mp2'][0]) / 2.0, (b['mp1'][1] + b['mp3'][1]) / 2.0)

    def extent(self):
        """The drawn size, round nose and tail included, for the wall clamp."""
        xs, ys = [], []
        for part in self.parts():
            for key in part:
                xs.append(part[key][0])
                ys.append(part[key][1])
        return (min(xs) - HULL_END_R, min(ys),
                max(xs) + HULL_END_R, max(ys))

    # the tower and the periscope are a third of the drawn height, so they
    # belong in the box. the propeller does not - it is a thin spinning blade
    # and clipping it should not cost anyone a life.
    HITBOX_PARTS = ('main_body', 'lower_body', 'top_body', 'air_duct')

    def get_bounding_box(self):
        xs, ys = [], []
        for name in self.HITBOX_PARTS:
            for point in getattr(self, name).values():
                xs.append(point[0])
                ys.append(point[1])
        # has_collided() reads x, y as the bottom left corner, so this returns
        # the corner and the size rather than the centre.
        return AABB(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


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

        mb = sub.main_body
        body = [mb["mp1"], mb["mp2"], mb["mp3"], mb["mp4"]]

        px1 = mb["mp1"][0]
        py1 = (mb['mp1'][1] + mb['mp4'][1]) / 2
        px2 = mb['mp2'][0]
        py2 = (mb['mp2'][1] + mb['mp3'][1]) / 2

        # nose and tail caps, then the hull, so the shape reads as one piece
        draw_filled_circle(px1, py1, 25, hull)
        draw_filled_circle(px2, py2, 25, hull)
        fill_polygon(hull, body, step=2)

        # a lighter band along the top of the hull for a bit of shading
        top_band = [[mb['mp1'][0], mb['mp1'][1]], [mb['mp2'][0], mb['mp2'][1]],
                    [mb['mp2'][0], mb['mp2'][1] - 12], [mb['mp1'][0], mb['mp1'][1] - 12]]
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

        # propeller: a shaft out of the hull, then blades spun by a sine
        pp = sub.propeller
        cxp = (pp['pp1'][0] + pp['pp2'][0]) / 2
        cyp = (pp['pp1'][1] + pp['pp3'][1]) / 2
        tail_x = px1 if sub.num == 2 else px2
        fill_polygon(dark, [[tail_x, cyp - 5], [cxp, cyp - 5],
                            [cxp, cyp + 5], [tail_x, cyp + 5]], step=2)
        blade = abs(sin(sub.prop_spin)) * 17 + 4
        fill_polygon(mix(dark, (1, 1, 1), 0.18),
                     [[cxp - 5, cyp - blade], [cxp + 5, cyp - blade],
                      [cxp + 5, cyp + blade], [cxp - 5, cyp + blade]], step=2)
        draw_filled_circle(cxp, cyp, 5, team['trim'])

        # a darker outline round the hull, so it stands off the water
        outline = mix(hull, (0, 0, 0), 0.55)
        draw_outline(outline, body)
        draw_hollow_circle(px1, py1, 25, outline, 3)
        draw_hollow_circle(px2, py2, 25, outline, 3)
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
            cx, cy = sub.center()
            r = 92 + sin(time.time() * 6) * 4
            pulse = 0.5 + 0.5 * sin(time.time() * 8)
            draw_hollow_circle(cx, cy, int(r), mix((0.3, 0.8, 1.0), (1, 1, 1), pulse), 3)
            draw_hollow_circle(cx, cy, int(r) - 4, (0.25, 0.65, 0.95), 2)


def damage(sub, amount):
    """One entry point for losing life, so shields and effects live in one place."""
    global shake, state
    # STATE_SINKING is the three seconds a loser takes to reach the seabed. The
    # round is already decided, so the winner cannot blunder into a mine during
    # the animation and turn their win into a draw.
    if not sub.control or state != STATE_PLAY:
        return
    # Without this, four hazards landing in the same frame took four lives at
    # once, with one flash to show for it.
    if sub.flash > IFRAMES * 0.45:
        return
    if sub.shield > 0:
        cx, cy = sub.center()
        burst(cx, cy, 18, [(0.4, 0.85, 1.0), (0.8, 0.95, 1.0)], speed=180, life=0.5)
        sub.shield = 0.0
        # the same i-frames a normal hit gets. Without them a minefield eats
        # the shield and a life in the same frame and the shield reads as
        # having done nothing.
        sub.flash = IFRAMES
        announce(f"{sub.team['name']} SHIELD ABSORBED IT")
        return
    sub.life = max(0, sub.life - amount)
    sub.flash = IFRAMES
    shake = min(16.0, shake + 9.0)
    cx, cy = sub.center()
    burst(cx, cy, 34)
    if sub.life == 0:
        sub.control = False
        state = STATE_SINKING
        announce(f"{sub.team['name']} IS GOING DOWN", 2.0)
        burst(cx, cy, 70, [(1.0, 0.9, 0.4), (1.0, 0.5, 0.1), (0.6, 0.6, 0.6)],
              speed=340, life=1.2, size=6)
    elif sub.life == 1:
        announce(f"{sub.team['name']} LAST STAND", 1.8)


def heal(sub, amount):
    sub.life = min(sub.max_life, sub.life + amount)


def update_submarine_positions(dt):
    for sub in submarines:
        sub.flash = max(0.0, sub.flash - dt)
        sub.shield = max(0.0, sub.shield - dt)
        sub.rapid = max(0.0, sub.rapid - dt)
        sub.boost = max(0.0, sub.boost - dt)
        if sub.control:
            sub.prop_spin += dt * (14 + abs(sub.vx) * 0.04)
        else:
            auto_fall(sub, dt)


def apply_physics(dt):
    """
    Velocity, drag and the walls.

    The original moved a submarine a fixed 20 units inside the key handler, so
    how fast you actually moved depended on the operating system key repeat
    rate. Keys now set an intent, and the movement happens here once a frame.
    """
    for sub in submarines:
        if not sub.control:
            continue
        top = SUB_MAX * (1.25 if sub.boost > 0 else 1.0)
        if sub.life == 1:
            top *= 1.22          # last stand, see fire() as well
        # clamp the speed, not each axis on its own, or travelling diagonally
        # is 41 percent faster than travelling straight
        speed = math.hypot(sub.vx, sub.vy)
        if speed > top:
            sub.vx *= top / speed
            sub.vy *= top / speed
        sub.vx -= sub.vx * SUB_DRAG * dt
        sub.vy -= sub.vy * SUB_DRAG * dt

        dx, dy = sub.vx * dt, sub.vy * dt
        sub.move_by(dx, dy)

        min_x, min_y, max_x, max_y = sub.extent()
        # keep the whole hull on screen and under the water. Pushing into a wall
        # stops the submarine dead rather than bouncing it, so holding the key
        # against a wall is steady instead of a jitter.
        if min_x < WORLD_L + 10:
            sub.move_by(WORLD_L + 10 - min_x, 0)
            sub.vx = max(0.0, sub.vx)
        if max_x > WORLD_R - 10:
            sub.move_by(WORLD_R - 10 - max_x, 0)
            sub.vx = min(0.0, sub.vx)
        if max_y > SURFACE_Y - 5:
            sub.move_by(0, SURFACE_Y - 5 - max_y)
            sub.vy = min(0.0, sub.vy)
        # the wreck is a ledge in the middle of the seabed. Standing on it puts
        # you 70 units higher but in the open, and there is no way to sit
        # inside it where nothing can reach you.
        floor = SEABED_Y + 8
        if WRECK[0] < sub.center()[0] < WRECK[2]:
            floor = WRECK[3]
        if min_y < floor:
            sub.move_by(0, floor - min_y)
            sub.vy = max(0.0, sub.vy)


SINK_TILT_RATE = 0.22    # radians a second, while a hull is on its way down


def auto_fall(sub, dt):
    if sub.main_body['mp3'][1] > SEABED_Y + 10:
        sub.move_by(0, -150 * dt)
        # a hull going down goes down nose first, and the tilt is what makes
        # it read as sinking rather than as being lowered on a rope
        sub.rotate_by(-SINK_TILT_RATE * dt * (1 if sub.num == 1 else -1))
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
        sub.vx = sub.vy = 0.0
        sub.shield = sub.rapid = sub.boost = sub.flash = 0.0


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

    for i in range(len(bombs)):
        bombs[i][0] += bomb_vx[i] * dt
        bombs[i][1] -= fall_speed * dt

    if all(bomb[1] < SEABED_Y for bomb in bombs):
        reset_bombs()

    for i, bomb in enumerate(bombs):
        if bombN[i]:
            check_bomb_collisions(bomb, BOMB_R, i)


def bomb_landing_x(i):
    """Where charge i will cross the seabed, so it can be marked in advance."""
    drop = bombs[i][1] - SEABED_Y
    if drop <= 0:
        return bombs[i][0]
    return bombs[i][0] + bomb_vx[i] * (drop / fall_speed)


def draw_bomb_warnings():
    """
    A ring where each charge is heading.

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
        y = SEABED_Y + 16
        # a small bracket on the sand where this charge is going to land
        for k in range(0, 15, 3):
            pts += [(x - 18, y + k), (x + 18, y + k),
                    (x - 18 + k, y), (x + 18 - k, y)]
    set_color(col)
    draw_points_batch(pts, 3)


def check_bomb_collisions(bomb, bomb_radius, index):
    bx, by = bomb
    if wreck_blocks(bx, by):
        bombN[index] = False
        burst(bx, by, 20, [(0.7, 0.72, 0.75)], speed=150, life=0.5)
        return
    for sub in submarines:
        if hits_sub(sub, bx, by, bomb_radius):
            bombN[index] = False
            burst(bx, by, 26)
            damage(sub, 1)
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
    bomb_delay = 0.8


# The wreck is solid: torpedoes stop against it and submarines stand on it.
# It is the only fixed feature on the map, so it is the only reason to care
# where you are. The box is the drawn hull only - the three funnels above it
# are thin enough to shoot between, which is half the point of them.
WRECK = (-220, -252, 220, -230)


def wreck_blocks(x, y):
    return WRECK[0] < x < WRECK[2] and WRECK[1] < y < WRECK[3]


def draw_titanic():
    color_body = (0.30, 0.31, 0.33)
    hull = [[-220, -230], [220, -230], [200, -252], [-200, -252]]
    fill_polygon(color_body, hull, step=3)
    draw_outline((0.45, 0.46, 0.48), hull)
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
    for circle in unique_circles:
        if not circle.active:
            continue
        circle.radius += circle.direction * 22 * dt
        if circle.radius >= circle.max_radius or circle.radius <= circle.min_radius:
            circle.direction *= -1
        circle.y -= 95 * dt
        circle.x += sin(t * 1.6 + circle.phase) * 26 * dt
        if circle.y < SEABED_Y:
            circle.active = False
    unique_circles[:] = [c for c in unique_circles if c.active]


def draw_hollow_cross(x, y, size, color):
    draw_lines(color, x, y - size, x, y + size, 3)
    draw_lines(color, x - size, y, x + size, y, 3)


def draw_unique_circles():
    for c in unique_circles:
        if not c.active:
            continue
        color, symbol = PICKUP_STYLE[c.kind]
        r = int(c.radius)
        draw_filled_circle(c.x, c.y, r - 6, mix(color, (0, 0, 0), 0.55))
        draw_hollow_circle(c.x, c.y, r, color, 3)
        draw_hollow_circle(c.x, c.y, r - 3, mix(color, (1, 1, 1), 0.4), 2)
        s = r - 10
        if symbol == 'plus':
            draw_hollow_cross(c.x, c.y, s, color)
        elif symbol == 'ring':
            draw_hollow_circle(c.x, c.y, max(2, s), color, 3)
        elif symbol == 'bolt':
            draw_lines(color, c.x - s * 0.5, c.y + s, c.x + s * 0.2, c.y, 3)
            draw_lines(color, c.x + s * 0.2, c.y, c.x - s * 0.2, c.y, 3)
            draw_lines(color, c.x - s * 0.2, c.y, c.x + s * 0.5, c.y - s, 3)
        else:
            draw_lines(color, c.x - s, c.y - s * 0.4, c.x, c.y + s * 0.7, 3)
            draw_lines(color, c.x, c.y + s * 0.7, c.x + s, c.y - s * 0.4, 3)


def apply_pickup(sub, kind):
    if kind == KIND_HEALTH:
        gained = min(2, sub.max_life - sub.life)
        heal(sub, 2)
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
        if not (-640 < self.x < 640):
            self.drift *= -1

    def draw(self, t):
        pulse = 0.5 + 0.5 * sin(t * 5 + self.phase)
        body = (0.16, 0.17, 0.20) if self.armed <= 0 else (0.35, 0.35, 0.38)
        draw_filled_circle(self.x, self.y, 13, body)
        for i in range(8):
            a = i * (pi / 4)
            draw_lines((0.45, 0.45, 0.5), self.x + cos(a) * 13, self.y + sin(a) * 13,
                       self.x + cos(a) * 21, self.y + sin(a) * 21, 3)
        if self.armed <= 0:
            draw_filled_circle(self.x, self.y, 5, mix((0.5, 0.1, 0.1), (1.0, 0.3, 0.2), pulse))
            if self.life < 5:
                # blinking out, so it is clear it is about to go
                draw_hollow_circle(self.x, self.y, 26, (0.6, 0.6, 0.65) if pulse > 0.5
                                   else (0.3, 0.3, 0.35), 2)
        else:
            # a tightening ring while it arms, so a fresh mine is obviously
            # not yet dangerous
            draw_hollow_circle(self.x, self.y, int(19 + 9 * self.armed),
                               (0.95, 0.75, 0.3), 2)


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
                damage(sub, 1)
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
        nose_x = shark.x + SHARK_NOSE * shark.direction
        for sub in submarines:
            if (hits_sub(sub, shark.x, shark.y, SHARK_R)
                    or hits_sub(sub, nose_x, shark.y, SHARK_NOSE_R)):
                shark.active = False
                burst(shark.x, shark.y, 22, [(0.8, 0.2, 0.2), (0.9, 0.5, 0.4)],
                      speed=200, life=0.6)
                damage(sub, 1)
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
#  HUD
# ====================================================================== #

def render_text(text, x, y, font, color):
    glColor3f(color[0], color[1], color[2])
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(font, ord(char))


def draw_bar(x, y, w, h, frac, color, back=(0.10, 0.12, 0.16)):
    fill_rectangle(back, x - 2, y - 2, x + w + 2, y + h + 2, step=3)
    if frac > 0:
        fill_rectangle(color, x, y, x + w * max(0.0, min(1.0, frac)), y + h, step=3)


def draw_hud_panels():
    """Drawn with points, before the text, so the HUD stays readable on any sky."""
    for left in (True, False):
        x = -668 if left else 388
        fill_rectangle((0.04, 0.07, 0.13), x, 246, x + 280, 372, step=5)
        draw_outline((0.30, 0.42, 0.55),
                          [[x, 246], [x + 280, 246], [x + 280, 372], [x, 372]])
    fill_rectangle((0.04, 0.07, 0.13), -150, 344, 150, 372, step=5)


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
            cx = x + 12 + i * 22
            on = i < sub.life
            draw_filled_circle(cx, y - 20, 7,
                               team['trim'] if on else (0.25, 0.27, 0.31))

        # torpedo cooldown
        gap = time.time() - (tor_time1 if left else tor_time2)
        cd = RAPID_COOLDOWN if sub.rapid > 0 else TORPEDO_COOLDOWN
        draw_bar(x, y - 44, 240, 7, min(1.0, gap / cd), (0.55, 0.75, 0.95))

        # active power ups
        badge_x = x
        for label, remaining, full, col in (
                ("SHIELD", sub.shield, SHIELD_TIME, (0.25, 0.65, 0.95)),
                ("RAPID", sub.rapid, RAPID_TIME, (0.98, 0.72, 0.16)),
                ("BOOST", sub.boost, BOOST_TIME, (0.35, 0.85, 0.45))):
            if remaining > 0:
                draw_bar(badge_x, y - 66, 60, 7, remaining / full, col)
                badge_x += 70


def draw_hud_text():
    for sub in submarines:
        team = sub.team
        x = -650 if sub.num == 1 else 406
        render_text(team['name'], x, 354, FONT, (1.0, 1.0, 1.0))
        render_text(f"{score[sub.num]}/{ROUNDS_TO_WIN}", x + 205, 354, FONT, team['trim'])

    header = f"ROUND {round_no}"
    render_text(header, -len(header) * 4, 352, FONT, (1.0, 0.92, 0.55))
    render_text(f"{fps_shown:.0f} FPS", 600, -374, FONT_SMALL, (0.7, 0.75, 0.8))

    if announcement and time.time() < announce_until:
        render_text(announcement, -len(announcement) * 5, 96, FONT, (1.0, 0.92, 0.55))


def announce(text, seconds=1.6):
    global announcement, announce_until
    announcement = text
    announce_until = time.time() + seconds


def draw_button_chrome():
    """The three discs behind the buttons. Static, so they get baked."""
    for cx in (-100, 0, 100):
        draw_filled_circle(cx, -350, 20, (0.12, 0.14, 0.19))
        draw_hollow_circle(cx, -350, 21, (0.40, 0.45, 0.55), 2)


def draw_button_bar():
    draw_restart()
    draw_pause()
    draw_cancel()


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
    else:
        state = STATE_ROUND_OVER


def banner_settled():
    """Ignore the first moment of a result screen, so it cannot be skipped by
    a key or a click that was already on its way when the round ended."""
    return time.time() - round_over_at > BANNER_GRACE


def start_round():
    global state, round_winner, game_over, paused, player, shake
    global last_spawn_time, last_spawn_time_shark, last_mine_time
    global tor_time1, tor_time2
    now = time.time()
    # these are wall clock stamps: without resetting them, twenty seconds on
    # the round banner meant a pickup, a shark and a mine all arrived at once
    last_spawn_time = now
    last_spawn_time_shark = now
    last_mine_time = now
    tor_time1 = tor_time2 = now - 5
    shake = 0.0
    state = STATE_PLAY
    round_winner = None
    game_over = False
    paused = False
    player = None
    for sub in submarines:
        sub.control = True
        sub.life = sub.max_life
    torpedo1.clear()
    torpedo2.clear()
    bubbles.clear()
    sharks.clear()
    unique_circles.clear()
    particles.clear()
    mines.clear()
    reset_submarine_positions()
    reset_bombs()
    reset_rains()
    announce(f"ROUND {round_no}  -  FIGHT", 1.4)


def next_round():
    global round_no
    round_no += 1
    start_round()


def reset_game():
    global round_no, match_winner
    round_no = 1
    score[1] = score[2] = 0
    match_winner = None
    start_round()


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

    if current_time - last_mine_time > 10 and len(mines) < 4:
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
#  moving the submarine directly. Holding a key now accelerates smoothly and
#  releasing it lets the submarine coast.
# ====================================================================== #

held = set()

CONTROLS_P1 = {b'w': (0, 1), b's': (0, -1), b'a': (-1, 0), b'd': (1, 0)}
CONTROLS_P2 = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}


def apply_input(dt):
    if state not in (STATE_PLAY, STATE_SINKING) or paused:
        return

    ax = ay = 0
    for key, (kx, ky) in CONTROLS_P1.items():
        if key in held:
            ax += kx
            ay += ky
    if sub11.control and (ax or ay):
        mag = math.hypot(ax, ay) or 1
        sub11.vx += (ax / mag) * SUB_ACCEL * dt
        sub11.vy += (ay / mag) * SUB_ACCEL * dt

    ax = ay = 0
    for key, (kx, ky) in CONTROLS_P2.items():
        if key in held:
            ax += kx
            ay += ky
    if sub22.control and (ax or ay):
        mag = math.hypot(ax, ay) or 1
        sub22.vx += (ax / mag) * SUB_ACCEL * dt
        sub22.vy += (ay / mag) * SUB_ACCEL * dt


def aim_of(sub):
    """
    Where a submarine is pointing.

    A torpedo goes where the submarine is moving, so lining up a shot and
    getting out of the way pull against each other. Standing still fires
    level, towards the other player's half.
    """
    speed = math.hypot(sub.vx, sub.vy)
    if speed < 45:
        return (1.0, 0.0) if sub.num == 1 else (-1.0, 0.0)
    return sub.vx / speed, sub.vy / speed


def fire(sub):
    global tor_time1, tor_time2
    if state not in (STATE_PLAY, STATE_SINKING) or paused or not sub.control:
        return

    now = time.time()
    last = tor_time1 if sub.num == 1 else tor_time2
    cooldown = RAPID_COOLDOWN if sub.rapid > 0 else TORPEDO_COOLDOWN
    if sub.life == 1:
        cooldown *= 0.65            # last stand
    if now - last < cooldown:
        return

    ux, uy = aim_of(sub)
    cx, cy = sub.center()
    nose_x = cx + ux * 74
    nose_y = cy + uy * 74
    (torpedo1 if sub.num == 1 else torpedo2).append(
        Torpedo(nose_x, nose_y, ux * speed_tor, uy * speed_tor, sub.num))

    burst(nose_x, nose_y, 9, [(1.0, 0.9, 0.5), (1.0, 0.7, 0.3)],
          speed=140, life=0.3, size=3)

    if sub.num == 1:
        tor_time1 = now
    else:
        tor_time2 = now


# far enough to cross the map, because a sight that stops short of where the
# torpedo would still be flying is telling you the wrong thing
AIM_RANGE = 1440
AIM_STEP = 16            # one dash every this many units


def aim_trace(sub):
    """
    Walk the line a torpedo would take and stop at the first thing it would
    hit. A torpedo flies straight at a constant speed, so the same walk the
    collision code does frame by frame can be done all at once here, and the
    sight is telling the truth rather than guessing.

    Returns the dashes to draw, where the shot ends, and whether the thing it
    ends on is the other submarine.
    """
    ux, uy = aim_of(sub)
    ox, oy = sub.center()
    x, y = ox, oy
    enemy = sub22 if sub.num == 1 else sub11
    dashes = []
    for _ in range(AIM_RANGE // AIM_STEP):
        x += ux * AIM_STEP
        y += uy * AIM_STEP
        if not WORLD_L < x < WORLD_R or not SEABED_Y < y < SURFACE_Y:
            break
        if wreck_blocks(x, y):
            break
        if any(m.active and math.hypot(x - m.x, y - m.y) <= MINE_R for m in mines):
            break
        if hits_sub(enemy, x, y, TORPEDO_R):
            return dashes, (x, y), True
        # the first few dashes sit inside our own hull, so they are skipped
        if math.hypot(x - ox, y - oy) > 74:
            dashes.append((x, y))
    return dashes, (x, y), False


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
        # on the last dash rather than on the hull, or the submarine it is
        # pointing at gets drawn over the top of it
        rx, ry = dashes[-1] if dashes else (hx, hy)
        draw_hollow_circle(int(rx), int(ry), 15, (1.0, 0.35, 0.22), 2)
    else:
        set_color(mix(sub.team['trim'], (1, 1, 1), 0.35))
        draw_points_batch(dashes, 3)


def set_night(on):
    global night, PAL, background_update_needed
    night = on
    PAL = dict(NIGHT if on else DAY)
    background_update_needed = True


def keyboardListener(key, x, y):
    global paused, restart_game, state

    # every comparison below uses the lowered key. Movement was already
    # lowered but the action keys were not, so with caps lock on both
    # players could swim and neither could shoot, pause or restart.
    k = key.lower()
    held.add(k)

    if k == b'n':
        set_night(not night)

    if k in (b'\r', b' '):
        if state == STATE_MENU:
            reset_game()
        elif state == STATE_ROUND_OVER:
            if banner_settled():
                next_round()
        elif state == STATE_MATCH_OVER:
            if banner_settled():
                reset_game()

    if k == b'i':
        if state in (STATE_PLAY, STATE_SINKING):
            paused = not paused
    if k == b'r':
        if state != STATE_MENU:
            restart_game = True
    if k == b'c':
        fire(sub11)
    if k == b'p':
        fire(sub22)
    if key == b'\x1b':
        state = STATE_MENU

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
    name = SPECIAL.get(key)
    if name:
        held.add(name)
    glutPostRedisplay()


def specialUpListener(key, x, y):
    name = SPECIAL.get(key)
    if name:
        held.discard(name)


def mouseListener(button, state_, x, y):
    global restart_game, paused, state

    if button != GLUT_LEFT_BUTTON or state_ != GLUT_DOWN:
        return
    c_X, c_y = convert_coordinate(x, y)

    if state in (STATE_MENU, STATE_ROUND_OVER, STATE_MATCH_OVER):
        # the quit button still quits, even on a banner
        if math.hypot(c_X - 100, c_y + 350) <= 22:
            state = STATE_MENU
        elif state == STATE_MENU:
            reset_game()
        elif not banner_settled():
            pass
        elif state == STATE_ROUND_OVER:
            next_round()
        else:
            reset_game()
        glutPostRedisplay()
        return

    if math.hypot(c_X + 100, c_y + 350) <= 22:
        restart_game = True
    elif math.hypot(c_X, c_y + 350) <= 22:
        paused = not paused
    elif math.hypot(c_X - 100, c_y + 350) <= 22:
        state = STATE_MENU

    glutPostRedisplay()


# ====================================================================== #
#  Screens
# ====================================================================== #

MENU_LINES = [
    ("MARKAVA        W A S D to move        C to fire", -4, (0.45, 0.90, 0.75), FONT),
    ("DESTROYER      ARROW KEYS to move     P to fire", -36, (0.98, 0.62, 0.45), FONT),
    ("I pause      R restart      N day and night      ESC menu",
     -92, (0.80, 0.85, 0.92), FONT_SMALL),
    ("Collect the falling circles. Dodge the depth charges, the mines",
     -136, (0.72, 0.80, 0.88), FONT_SMALL),
    ("and the shark. First to two rounds wins the match.",
     -158, (0.72, 0.80, 0.88), FONT_SMALL),
    ("PRESS ENTER TO DIVE", -212, (1.0, 0.85, 0.35), FONT),
]


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


def draw_menu_panel():
    fill_rectangle((0.02, 0.06, 0.14), -430, -260, 430, 220, step=5)
    draw_outline((0.25, 0.65, 0.85),
                      [[-430, -260], [430, -260], [430, 220], [-430, 220]])
    draw_outline((0.15, 0.40, 0.58),
                      [[-424, -254], [424, -254], [424, 214], [-424, 214]])
    draw_menu_sub(-215, 108, 1, 1)
    draw_menu_sub(215, 108, 2, -1)
    for k in range(-90, 91, 6):
        draw_filled_circle(k, 108 + sin(k * 0.09 + time.time() * 2.2) * 9, 3,
                           (0.55, 0.80, 0.95))


def draw_menu_text():
    title = "SUBMARINE SAGA"
    render_text(title, -len(title) * 7, 174, FONT_BIG, (1.0, 0.92, 0.55))
    for text, y, color, font in MENU_LINES:
        if not text:
            continue
        render_text(text, -len(text) * 5, y, font, color)


def round_banner_lines():
    if state == STATE_ROUND_OVER:
        title = f"{TEAM[round_winner]['name']} TAKES ROUND {round_no}"
        sub_line = f"{score[1]} - {score[2]}      PRESS ENTER FOR THE NEXT ROUND"
    elif state == STATE_MATCH_OVER:
        title = f"{TEAM[match_winner]['name']} WINS THE MATCH"
        sub_line = f"FINAL {score[1]} - {score[2]}      PRESS ENTER TO PLAY AGAIN"
    else:
        return None
    return title, sub_line


def draw_banner_panel():
    if round_banner_lines():
        fill_rectangle((0.03, 0.07, 0.15), -410, -60, 410, 90, step=5)
        draw_outline((1.0, 0.85, 0.35),
                          [[-410, -60], [410, -60], [410, 90], [-410, 90]])


def draw_banner_text():
    lines = round_banner_lines()
    if not lines:
        return
    title, sub_line = lines
    render_text(title, -len(title) * 5, 40, FONT, (1.0, 0.92, 0.55))
    render_text(sub_line, -len(sub_line) * 4, -20, FONT_SMALL, (0.85, 0.90, 0.96))


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

    if state != STATE_MENU:
        draw_bubble()
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

    draw_particles()

    # Everything above is drawn with points. Text is not, so every point has to
    # reach the screen before any text goes on top of it, or the next batch of
    # points covers the text up.
    if state == STATE_MENU:
        draw_menu_panel()
    else:
        if static_list:
            flush_points()
            glCallList(static_list)
        draw_button_bar()
        draw_hud_shapes()
        draw_banner_panel()

    flush_points()

    if state == STATE_MENU:
        draw_menu_text()
    else:
        draw_hud_text()
        if paused:
            render_text("PAUSED", -32, 60, FONT, (1.0, 0.8, 0.3))
        draw_banner_text()

    glutSwapBuffers()


def shift_timers(dt):
    """Move every wall clock deadline forward, for time the game did not run."""
    global start_time1, start_time2, tor_time1, tor_time2, announce_until
    global last_spawn_time, last_spawn_time_shark, last_mine_time
    start_time1 += dt
    start_time2 += dt
    tor_time1 += dt
    tor_time2 += dt
    announce_until += dt
    last_spawn_time += dt
    last_spawn_time_shark += dt
    last_mine_time += dt


def animate():
    global last_frame, restart_game, shake, fps_shown, _fps_frames, _fps_clock

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

    if paused:
        # the cooldowns below are wall clock stamps and the wall clock does not
        # stop when the game does. Pushing them along by dt keeps them the same
        # distance in the past, otherwise a thirty second pause leaves every
        # timer overdue and the mines, the shark and both torpedoes all arrive
        # in the first frame after unpausing.
        shift_timers(dt)

    update_fishes(dt, t)
    update_particles(dt)
    update_rains(dt)

    if state in (STATE_PLAY, STATE_SINKING) and not paused:
        apply_input(dt)
        apply_physics(dt)
        handle_spawn_events(now, dt, t)
        update_bubbles(now, dt)
        update_submarine_positions(dt)
        update_bombs(dt)
        update_torpedoes(dt)
    elif state in (STATE_ROUND_OVER, STATE_MATCH_OVER):
        update_submarine_positions(dt)

    glutPostRedisplay()


def reshape(width, height):
    global W_Width, W_Height
    W_Width, W_Height = max(1, width), max(1, height)
    glViewport(0, 0, W_Width, W_Height)


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

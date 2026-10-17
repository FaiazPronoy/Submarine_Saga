# Submarine Saga - Copyright (c) 2024-2026 Faiaz Abrar Zaman Pronoy and
# Sinthia Khandoker. All rights reserved. See LICENSE.
"""
Checks for Submarine Saga.

Loads the game without starting the GLUT main loop, then drives it a frame at
a time: holds keys, fires torpedoes, takes damage, wins rounds, and makes sure
the entity lists do not grow for ever.

Run from anywhere:   python tests/test_game.py
"""
import os
import sys
import random
import time
import math

# The OpenGL package ships in the project folder, one level up from this one.
# Python only puts the script's own directory on the path, so without this the
# import below fails for anyone who has not installed PyOpenGL system wide.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

GAME = os.path.join(ROOT, 'Submarine Saga (CSE423 Project).py')

sys.argv = ['game']
from OpenGL.GL import *      # noqa: E402  (path has to be set up first)
from OpenGL.GLUT import *    # noqa: E402

import tempfile
src = open(GAME, encoding='utf-8').read().replace('glutMainLoop()','')
g={'__name__':'__main__'}
exec(compile(src, GAME, 'exec'), g)
# The checks drive the two player game frame by frame: no countdown, no
# sound, and a record file that is not the player's own.
g['READY_TIME'] = 0.0
g['sound_on'] = False
g['menu_choice'] = 1
g['vs_cpu'] = False
g['SAVE_PATH'] = os.path.join(tempfile.gettempdir(), 'submarine_saga_test_save.json')
_d, _a = g['display'], g['animate']
def a():
    # animate() skips a frame that comes sooner than 8ms after the last one;
    # pretend a normal frame's worth of time has passed so none are skipped
    g['last_frame'] -= 0.02
    _a()
def d():
    _d()
PASS, FAIL = [], []
def check(name, cond, extra=''):
    (PASS if cond else FAIL).append(name)
    print(('  ok   ' if cond else '  FAIL ') + name + ('' if cond else f'  -> {extra}'))
def frames(n=6):
    for _ in range(n):
        a(); d()

def wait_out_banner():
    """Sit through the grace period a result screen holds input for."""
    g['round_over_at'] -= g['BANNER_GRACE'] + 0.1


def hit(sub, times=1):
    """Damage with a gap, because a hit now grants a moment of invulnerability."""
    for _ in range(times):
        # let the moment of cover from the last hit run out first
        sub.flash = 0.0
        g['damage'](sub, 1)
        frames(5)

random.seed(7)
frames(3)
check("the game opens on the intro", g['state'] == g['STATE_INTRO'], g['state'])
g['keyboardListener'](b'\r', 0, 0); frames(2)
check("any key skips the intro to the title screen", g['state'] == g['STATE_MENU'], g['state'])
check("and the key that skipped it does nothing else", not g['held'], g['held'])

# the intro also ends by itself, and a click skips it too
g['state'] = g['STATE_INTRO']; g['intro_t'] = 0.0
for _ in range(int(g['INTRO_TIME'] / 0.02) + 40):
    a(); d()
    if g['state'] != g['STATE_INTRO']:
        break
check("the intro ends by itself", g['state'] == g['STATE_MENU'], g['state'])
g['state'] = g['STATE_INTRO']; g['intro_t'] = 1.0
g['mouseListener'](GLUT_LEFT_BUTTON, GLUT_DOWN, 683, 384)
check("a click skips the intro", g['state'] == g['STATE_MENU'], g['state'])
check("without starting a game", g['state'] != g['STATE_PLAY'])

# the lettering is the pixel font, cell for cell
cells, width = g['title_cells']("SAGA")
check("the title font lays letters out five wide with a gap", width == 4 * 6 - 1, width)
check("every letter of the name has a glyph",
      all(ch in g['TITLE_FONT'] for line in g['TITLE_LINES'] for ch in line))
x, y, cell = g['title_cell_spot'](0, 0, 0, g['MENU_LAYOUT'])
check("the heading sits inside the title screen's panel",
      g['MENU_PANEL'][1] < y - 7 * cell and y <= g['MENU_PANEL'][3], (x, y))
# the tail of the g in "Saga" must clear the line under it
_, gy, gcell = g['title_cell_spot'](1, 0, g['TITLE_ROWS'] - 1, g['MENU_LAYOUT'])
check("the heading stays clear of the subtitle", gy - gcell > 102 + 12, gy - gcell)
check("the name is in capitals", g['TITLE_LINES'] == ("SUBMARINE", "SAGA"))
check("a cell appears when the sonar ping reaches it",
      g['intro_reveal'](*g['SONAR_ORIGIN']) < g['intro_reveal'](500, 40))
frames(2)

g['keyboardListener'](b'\r', 0, 0); frames(3)
check("enter starts a round", g['state'] == g['STATE_PLAY'], g['state'])
check("both submarines start alive", g['sub11'].life == g['MAX_LIFE'] and g['sub22'].life == g['MAX_LIFE'])
check("the score starts at nil all", g['score'] == {1:0, 2:0}, g['score'])

# held keys move a submarine, and releasing lets it coast
x0 = g['sub11'].center()[0]
g['held'].add(b'd'); frames(14); g['held'].discard(b'd')
x1 = g['sub11'].center()[0]
check("holding a key moves the submarine", x1 > x0 + 5, (x0, x1))
v = g['sub11'].vx
frames(14)
check("it slows down after the key is released", abs(g['sub11'].vx) < abs(v), (v, g['sub11'].vx))

# the walls
g['sub11'].vx = -6000; frames(20)
check("a submarine cannot leave the left wall", g['sub11'].extent()[0] >= g['WORLD_L'] - 1,
      g['sub11'].extent()[0])
g['sub11'].vy = 9000; frames(20)
check("a submarine cannot break the surface", g['sub11'].extent()[3] <= g['SURFACE_Y'] + 1,
      g['sub11'].extent()[3])

# the crash the original had: firing with the two subs on the same column
g['reset_game']()
g['sub22'].move_by(g['sub11'].center()[0] - g['sub22'].center()[0], 0)
try:
    g['fire'](g['sub11']); frames(2); ok = True; err = ''
except Exception as e:
    ok = False; err = repr(e)
check("firing straight up the same column does not crash", ok, err)

# cooldown
g['reset_game']()
g['tor_time1'] = 0
g['fire'](g['sub11']); n1 = len(g['torpedo1'])
g['fire'](g['sub11']); n2 = len(g['torpedo1'])
check("a torpedo cannot be fired twice in a row", n1 == 1 and n2 == 1, (n1, n2))

# damage, shields and death
g['reset_game']()
hit(g['sub22'])
check("a hit takes one life", g['sub22'].life == g['MAX_LIFE'] - 1, g['sub22'].life)

# four hazards landing together used to take four lives in one frame
g['sub22'].flash = 0.0
before = g['sub22'].life
for _ in range(4):
    g['damage'](g['sub22'], 1)
check("four hits in the same instant only cost one life",
      g['sub22'].life == before - 1, (before, g['sub22'].life))

g['sub22'].flash = 0.0
g['sub22'].shield = 5.0
g['damage'](g['sub22'], 1)
check("a shield absorbs the next hit", g['sub22'].shield == 0)
g['heal'](g['sub22'], 99)
check("health never goes past the maximum", g['sub22'].life == g['sub22'].max_life)
hit(g['sub22'], 2 * g['MAX_LIFE'])
check("life never goes below zero", g['sub22'].life == 0, g['sub22'].life)
check("a submarine with no life loses control", not g['sub22'].control)

# the round ends once it has sunk
for _ in range(400):
    a(); d()
    if g['state'] == g['STATE_ROUND_OVER']:
        break
check("sinking ends the round", g['state'] == g['STATE_ROUND_OVER'], g['state'])
check("the round is awarded to the survivor", g['score'][1] == 1, g['score'])

# a key that was already down when the round ended must not skip the banner
g['keyboardListener'](b'\r', 0, 0); frames(3)
check("the result banner cannot be skipped instantly",
      g['state'] == g['STATE_ROUND_OVER'], g['state'])
wait_out_banner()
g['keyboardListener'](b'\r', 0, 0); frames(3)
check("enter starts the next round", g['state'] == g['STATE_PLAY'] and g['round_no'] == 2,
      (g['state'], g['round_no']))
check("the next round restores full health", g['sub22'].life == g['MAX_LIFE'])

# win the match
hit(g['sub22'], 2 * g['MAX_LIFE'])
for _ in range(400):
    a(); d()
    if g['state'] == g['STATE_MATCH_OVER']:
        break
check("two round wins takes the match", g['state'] == g['STATE_MATCH_OVER'], g['state'])
check("the match winner is recorded", g['match_winner'] == 1, g['match_winner'])

wait_out_banner()
g['keyboardListener'](b'\r', 0, 0); frames(3)
check("enter after the match starts a fresh one",
      g['state'] == g['STATE_PLAY'] and g['round_no'] == 1 and g['score'] == {1:0, 2:0},
      (g['round_no'], g['score']))

# pause
g['keyboardListener'](b'i', 0, 0)
check("i pauses", g['paused'])
before = g['sub11'].center()
g['held'].add(b'd'); frames(10); g['held'].discard(b'd')
check("nothing moves while paused", g['sub11'].center() == before)
g['keyboardListener'](b'i', 0, 0)
check("i unpauses", not g['paused'])

# day / night
g['keyboardListener'](b'n', 0, 0); frames(2)
check("n switches to night", g['night'])
g['keyboardListener'](b'N', 0, 0); frames(2)
check("N switches back to day", not g['night'])

# pickups
g['reset_game']()
g['sub11'].life = 2
g['sub11'].flash = 0.0
cx, cy = g['sub11'].center()
g['unique_circles'].append(g['UniqueCircle'](cx, cy, 20, g['KIND_HEALTH']))
g['check_collision_with_unique_circle'](g['sub11'])
check("a health pickup heals", g['sub11'].life == 2 + g['HEALTH_PICKUP'], g['sub11'].life)
g['unique_circles'].append(g['UniqueCircle'](cx, cy, 20, g['KIND_SHIELD']))
g['check_collision_with_unique_circle'](g['sub11'])
check("a shield pickup raises a shield", g['sub11'].shield > 0)
g['unique_circles'].append(g['UniqueCircle'](cx, cy, 20, g['KIND_RAPID']))
g['check_collision_with_unique_circle'](g['sub11'])
check("a rapid fire pickup shortens the cooldown", g['sub11'].rapid > 0)

# lists must not grow for ever
g['reset_game']()
for _ in range(700):
    a(); d()
check("bubbles are cleaned up", len(g['bubbles']) < 60, len(g['bubbles']))
check("particles are cleaned up", len(g['particles']) < 700, len(g['particles']))
check("dead sharks are removed", len(g['sharks']) < 12, len(g['sharks']))
check("mines are capped", len(g['mines']) <= 5, len(g['mines']))
check("pickups are cleaned up", len(g['unique_circles']) < 20, len(g['unique_circles']))

# restart and escape
g['keyboardListener'](b'r', 0, 0); frames(3)
check("r restarts the match", g['round_no'] == 1 and g['score'] == {1:0, 2:0})
g['keyboardListener'](b'\x1b', 0, 0); frames(2)
check("escape returns to the menu", g['state'] == g['STATE_MENU'])

# the mouse buttons along the bottom
g['reset_game']()
g['mouseListener'](GLUT_LEFT_BUTTON, GLUT_DOWN, 683, 734)   # pause button
check("clicking the pause button pauses", g['paused'])
g['mouseListener'](GLUT_LEFT_BUTTON, GLUT_DOWN, 683, 734)
check("clicking it again resumes", not g['paused'])

# ---- the bugs a second review found ----

g['reset_game']()
# player two's torpedoes used to climb when they should have dived
g['sub22'].aim = math.atan2(-1, -1)      # down and to the left
g['tor_time2'] = 0
g['fire'](g['sub22'])
t2 = g['torpedo2'][-1]
check("player two's torpedo goes the way it is pointed", t2.vx < 0 and t2.vy < 0,
      (t2.vx, t2.vy))
g['sub11'].aim = math.atan2(-1, 1)       # down and to the right
g['tor_time1'] = 0
g['fire'](g['sub11'])
t1 = g['torpedo1'][-1]
check("player one's torpedo goes the way it is pointed", t1.vx > 0 and t1.vy < 0,
      (t1.vx, t1.vy))

g['reset_game']()
g['sub11'].vx = g['sub11'].vy = 0.0
g['tor_time1'] = 0
g['fire'](g['sub11'])
check("standing still fires level", abs(g['torpedo1'][-1].vy) < 1e-6)

# the collision box has to actually sit on the hull
g['reset_game']()
cx, cy = g['sub11'].center()
box = g['sub11'].get_bounding_box()
check("the collision box covers the hull centre",
      box.x <= cx <= box.x + box.width and box.y <= cy <= box.y + box.height,
      (cx, cy, box.x, box.y, box.width, box.height))
check("a hazard on the hull registers", g['hits_sub'](g['sub11'], cx, cy, 4))
check("a hazard a long way off does not",
      not g['hits_sub'](g['sub11'], cx + 320, cy + 220, 4))

# torpedoes clear mines and shoot each other down
g['reset_game']()
g['mines'].append(g['Mine']())
m = g['mines'][-1]
m.x, m.y = 0, 0
g['torpedo1'].append(g['Torpedo'](0, 0, 100, 0, 1))
g['update_torpedoes'](0.016)
check("a torpedo clears a mine", not m.active)

g['reset_game']()
g['torpedo1'].append(g['Torpedo'](0, 0, 500, 0, 1))
g['torpedo2'].append(g['Torpedo'](5, 0, -500, 0, 2))
g['update_torpedoes'](0.001)
check("two torpedoes cancel each other out",
      not g['torpedo1'] and not g['torpedo2'],
      (len(g['torpedo1']), len(g['torpedo2'])))

# the wreck is cover
g['reset_game']()
wx = (g['WRECK'][0] + g['WRECK'][2]) / 2
wy = (g['WRECK'][1] + g['WRECK'][3]) / 2
g['torpedo1'].append(g['Torpedo'](wx, wy, 100, 0, 1))
g['update_torpedoes'](0.016)
check("the wreck stops a torpedo", not g['torpedo1'])

# depth charges must never be flung off the map
worst = 0.0
for _ in range(300):
    g['reset_bombs']()
    worst = max(worst, max(abs(v) for v in g['bomb_vx']))
check("no depth charge is flung off the map", worst < 400, worst)

# a sinking loser cannot turn a win into a draw
g['reset_game']()
hit(g['sub22'], 2 * g['MAX_LIFE'])
check("the loser sinking puts the game in the sinking state",
      g['state'] == g['STATE_SINKING'], g['state'])
before_life = g['sub11'].life
g['damage'](g['sub11'], 99)
check("the winner cannot be hurt while the loser sinks",
      g['sub11'].life == before_life and g['sub11'].control)
for _ in range(400):
    a(); d()
    if g['state'] == g['STATE_ROUND_OVER']:
        break
check("the round still goes to the survivor", g['score'][1] == 1, g['score'])

# a long pause must not queue up a burst of spawns
g['reset_game']()
g['last_spawn_time'] -= 100
g['last_spawn_time_shark'] -= 100
g['last_mine_time'] -= 100
g['start_round']()
frames(3)
check("a long gap does not spawn everything at once",
      len(g['unique_circles']) + len(g['sharks']) + len(g['mines']) <= 1,
      (len(g['unique_circles']), len(g['sharks']), len(g['mines'])))

# losing focus must not leave a key stuck down
g['reset_game']()
g['keyboardListener'](b'd', 0, 0)
g['entryListener'](0)
check("losing focus releases every key", not g['held'])

# caps lock
g['keyboardListener'](b'D', 0, 0)
check("caps lock still moves the submarine", b'd' in g['held'])
g['keyboardUpListener'](b'D', 0, 0)
check("and releasing it still works", b'd' not in g['held'])

# r on the title screen should not start a match behind the menu
g['keyboardListener'](b'\x1b', 0, 0); frames(2)
g['keyboardListener'](b'r', 0, 0); frames(3)
check("r on the menu does nothing", g['state'] == g['STATE_MENU'], g['state'])

# the speed cap is on the whole velocity, not one axis at a time
g['keyboardListener'](b'\r', 0, 0); frames(2)
g['sub11'].vx, g['sub11'].vy = 9000.0, 9000.0
g['apply_physics'](0.001)
diagonal = (g['sub11'].vx ** 2 + g['sub11'].vy ** 2) ** 0.5
g['sub11'].vx, g['sub11'].vy = 9000.0, 0.0
g['apply_physics'](0.001)
straight = abs(g['sub11'].vx)
check("diagonal travel is not faster than straight travel",
      diagonal <= straight * 1.02, (straight, diagonal))
# ---------------------------------------------------------------- sinking

g['start_round']()
sub = g['sub22']
def hull_span():
    b = sub.main_body
    return (math.hypot(b['mp2'][0] - b['mp1'][0], b['mp2'][1] - b['mp1'][1]),
            math.hypot(b['mp4'][0] - b['mp1'][0], b['mp4'][1] - b['mp1'][1]))

def tilt_degrees():
    b = sub.main_body
    return abs(math.degrees(math.atan2(b['mp2'][1] - b['mp1'][1],
                                       b['mp2'][0] - b['mp1'][0])))

before = hull_span()
sub.rotate_by(0.5)
check("turning a hull does not stretch it",
      all(abs(a - b) < 1e-6 for a, b in zip(before, hull_span())), (before, hull_span()))
sub.rotate_by(-0.5)
check("and turning it back leaves it level", tilt_degrees() < 1e-6, tilt_degrees())

g['start_round']()
sub = g['sub22']
cx, cy = sub.center()
sub.move_by(0 - cx, 150 - cy)
sub.flash = 0.0
for _ in range(2 * g['MAX_LIFE']):
    g['damage'](sub, 1)
    sub.flash = 0.0
check("losing every life starts the sinking animation",
      g['state'] == g['STATE_SINKING'], g['state'])
for _ in range(400):
    a(); d()
    if g['state'] != g['STATE_SINKING']:
        break
check("a sinking hull tilts on the way down", tilt_degrees() > 3, tilt_degrees())
wait_out_banner()
g['keyboardListener'](b'\r', 0, 0); frames(3)
check("and the next round puts it back level", tilt_degrees() < 1e-6, tilt_degrees())

# ---------------------------------------------------------------- hit boxes

g['reset_game']()
sub = g['sub11']
box = sub.get_bounding_box()
drawn_top = max(p[1] for p in sub.air_duct.values())
check("the periscope is inside the hit box", box.y + box.height >= drawn_top,
      (box.y + box.height, drawn_top))
drawn_bottom = min(p[1] for p in sub.lower_body.values())
check("the keel is inside the hit box", box.y <= drawn_bottom, (box.y, drawn_bottom))

# the shark bites with its nose, which is 46 units ahead of its centre
def shark_at(gap):
    g['start_round']()
    s = g['sub11']
    cx, cy = s.center()
    g['sharks'].clear()
    sh = g['Shark'](cx - gap, cy, 1)
    sh.warn = 0.0
    g['sharks'].append(sh)
    s.flash = 0.0
    g['update_sharks'](0.001, time.time())
    return s.life < s.max_life

check("the shark's snout bites", shark_at(100))
check("the shark still misses from clear water", not shark_at(190))

# ---------------------------------------------------------------- shields

g['start_round']()
sub = g['sub11']
sub.shield = g['SHIELD_TIME']
sub.flash = 0.0
g['damage'](sub, 1)
check("a shield absorbs the hit", sub.life == sub.max_life and sub.shield == 0)
g['damage'](sub, 1)
check("breaking a shield still grants the usual moment of cover",
      sub.life == sub.max_life, sub.life)

# a health crate on full health is worth something
g['start_round']()
sub = g['sub11']
sub.shield = 0.0
g['apply_pickup'](sub, g['KIND_HEALTH'])
check("a health crate on full health is not wasted", sub.shield > 0, sub.shield)

# the HUD bar and the effect have to agree, or a fresh power up reads as
# already half spent
for name, dur in (('SHIELD_TIME', 9.0), ('RAPID_TIME', 6.0), ('BOOST_TIME', 7.0)):
    check(f"{name} is a named duration the HUD can divide by", g[name] == dur, g[name])

# ---------------------------------------------------------------- the wreck

def park(x):
    g['start_round']()
    s = g['sub11']
    cx, cy = s.center()
    s.move_by(x - cx, 0)
    for _ in range(120):
        s.vy = -400.0
        g['apply_physics'](1 / 30.0)
    return s

WRECK = g['WRECK']
on_wreck = park(0)
check("a submarine stands on the wreck, not inside it",
      on_wreck.extent()[1] >= WRECK[3] - 1, on_wreck.extent()[1])
check("and nothing about it is hidden from a torpedo",
      not g['wreck_blocks'](*on_wreck.center()))
on_wreck.flash = 0.0
before = on_wreck.life
g['damage'](on_wreck, 1)
check("a submarine on the wreck can still be hurt", on_wreck.life < before)

off_wreck = park(-500)
check("away from the wreck the seabed is still the floor",
      off_wreck.extent()[1] < WRECK[3] - 40, off_wreck.extent()[1])

# ---------------------------------------------------------------- the sight

def line_up(y1, y2, x1=-300, x2=200):
    g['start_round']()
    for s, x, y in ((g['sub11'], x1, y1), (g['sub22'], x2, y2)):
        cx, cy = s.center()
        s.move_by(x - cx, y - cy)
    g['sub11'].vx = g['sub11'].vy = g['sub22'].vx = g['sub22'].vy = 0.0

line_up(0, 0)
dashes, end, locked = g['aim_trace'](g['sub11'])
check("the sight locks on a clear shot", locked)

line_up(-241, -241, -400, 400)
dashes, end, locked = g['aim_trace'](g['sub11'])
check("the wreck breaks the lock", not locked)
check("and the sight stops at the wreck", end[0] <= WRECK[0] + g['AIM_STEP'], end[0])

line_up(0, 0)
m = g['Mine']()
m.x, m.y = -100.0, g['sub11'].center()[1]
m.active = True
g['mines'].clear(); g['mines'].append(m)
dashes, end, locked = g['aim_trace'](g['sub11'])
check("a mine on the line breaks the lock too", not locked)

line_up(150, -150)
dashes, end, locked = g['aim_trace'](g['sub11'])
check("aimed at open water the sight just runs out", not locked and len(dashes) > 20)

# ---------------------------------------------------------------- pausing

g['start_round']()
g['paused'] = True
before = time.time() - g['last_mine_time']
t0 = time.time()
while time.time() - t0 < 0.6:
    _a()      # the real clock here: this is a test of wall clock timers
after = time.time() - g['last_mine_time']
check("a pause does not bank up spawn cooldowns", abs(after - before) < 0.15,
      (before, after))
g['paused'] = False

# ---------------------------------------------------------------- the rework

# only GL_POINTS may be used to draw: everything else is built from the
# midpoint line, the midpoint circle and the scanline fill
code = src.split('glutInit()')[0]
banned = [p for p in ('GL_LINES', 'GL_LINE_STRIP', 'GL_LINE_LOOP', 'GL_TRIANGLES', 'GL_QUADS',
                      'GL_POLYGON', 'glRect', 'gluDisk', 'glutSolid', 'glutWire')
          if p in code]
check("nothing is drawn with anything but GL_POINTS", not banned, banned)
# and every vertex goes through glBegin(GL_POINTS) / glVertex2f, not arrays
arrays = [p for p in ('glDrawArrays', 'glDrawElements', 'glVertexPointer', 'GL_VERTEX_ARRAY')
          if p in code]
check("no vertex arrays: every point is a glVertex2f", not arrays, arrays)
check("glBegin is only ever GL_POINTS",
      code.count('glBegin(') == code.count('glBegin(GL_POINTS)'),
      (code.count('glBegin('), code.count('glBegin(GL_POINTS)')))

# the midpoint line joins its two ends with no gaps, in all eight zones
worst_gap = 0
bad_ends = []
for ex, ey in ((40, 13), (13, 40), (-13, 40), (-40, 13), (-40, -13), (-13, -40), (13, -40), (40, -13),
               (30, 0), (0, 30), (-30, 0), (0, -30), (25, 25), (-25, -25)):
    pts = g['line_points'](0, 0, ex, ey)
    if not {(0, 0), (ex, ey)} <= set(map(tuple, pts)):
        bad_ends.append((ex, ey))
    s = sorted(pts, key=lambda p: p[0] * ex + p[1] * ey)
    for p, q in zip(s, s[1:]):
        worst_gap = max(worst_gap, max(abs(p[0] - q[0]), abs(p[1] - q[1])))
check("the midpoint line reaches both ends in every zone", not bad_ends, bad_ends)
check("the midpoint line has no gaps in any zone", worst_gap <= 1, worst_gap)

# the midpoint circle: every point is within half a pixel of the radius,
# and the eight octants make a shape that is symmetric both ways
ring = set(g['ring_points'](20))
off = max(abs(math.hypot(x, y) - 20) for x, y in ring)
check("every midpoint circle point sits on the radius", off < 0.75, off)
check("the midpoint circle is symmetric",
      all((-x, y) in ring and (x, -y) in ring and (y, x) in ring for x, y in ring))

# the scanline fill covers the inside of a shape and nothing outside it
tri = [(0, 0), (40, 0), (0, 40)]
fill = g['scanline_points'](tri, 1)
check("the scanline fill stays inside its polygon",
      all(x + y <= 41 and x >= 0 and y >= 0 for x, y in fill))
check("and fills it", len(fill) > 700, len(fill))

# credits: the authors are in the code and on the title screen
for name in ("Faiaz Abrar Zaman Pronoy", "Sinthia Khandoker"):
    check(f"{name} is in the copyright notice", name in g['__copyright__'])
    check(f"{name} is in the title screen credits", name in g['CREDIT_LINE'])
texts = [it[3] for it in g['menu_items']() if it[0] == 'text']
check("the title screen shows the credits", g['CREDIT_LINE'] in texts)

# the fine grain along the bottom of the sand
check("there are 64 grains in the pattern", len(g['grain_bits']()) == 64)
g['_runs'].clear()
g['draw_sand_grain']()
grains = [run for run in g['_runs'] if run[1] == 3]
check("the sand draws 64 grains", sum(len(c) for r in grains for c in r[2]) == 64)
sand = g['mix'](g['PAL']['sand_dark'], g['PAL']['sand'],
                (g['GRAIN_Y'] - g['WORLD_B']) / (g['SEABED_Y'] - g['WORLD_B']))
shades = {round((r[0][0] - sand[0]) * 255) for r in grains}
check("each grain is only a shade off the sand", shades <= {-6, 6}, shades)
g['_runs'].clear()

# Cohen-Sutherland clipping
cs = g['cohen_sutherland']
check("a line inside the rectangle is kept whole", cs(1, 1, 5, 5, 0, 0, 10, 10) == (1, 1, 5, 5))
check("a line wholly off one side is rejected", cs(-5, 1, -1, 9, 0, 0, 10, 10) is None)
check("a line off two sides but crossing a corner region is rejected",
      cs(-5, 8, 2, 15, 0, 0, 10, 10) is None)
c = cs(-5, 5, 15, 5, 0, 0, 10, 10)
check("a line through the rectangle is cut at both walls",
      c is not None and abs(c[0]) < 1e-9 and abs(c[2] - 10) < 1e-9, c)
c = cs(5, 5, 25, 25, 0, 0, 10, 10)
check("a diagonal is cut where it leaves",
      c is not None and abs(c[2] - 10) < 1e-9 and abs(c[3] - 10) < 1e-9, c)
g['start_round']()
s = g['sub11']
s.aim = 0.0
dashes, end, locked = g['aim_trace'](s)
g['sub22'].control = False
dashes, end, locked = g['aim_trace'](s)
check("the sight runs to the wall and stops on it",
      g['WORLD_R'] - g['AIM_PROBE'] <= end[0] <= g['WORLD_R'], end)
g['sub22'].control = True

# a torpedo on its way in is flagged a second ahead
g['start_round']()
you = g['sub11']
cx, cy = you.center()
g['torpedo2'].append(g['Torpedo'](cx + 300, cy, -430, 0, 2))
check("a torpedo coming at you is flagged", g['incoming'](you) is not None)
g['torpedo2'][:] = [g['Torpedo'](cx + 300, cy + 200, -430, 0, 2)]
check("one that will pass well clear is not", g['incoming'](you) is None)
g['torpedo2'][:] = [g['Torpedo'](cx + 1200, cy, -430, 0, 2)]
check("nor one still more than a second away", g['incoming'](you) is None)
g['torpedo2'].clear()

# fish swim head first
f = g['Fish']()
f.dir = 1
f.x, f.y, f.size = 0.0, 0.0, 10.0
g['_runs'].clear()
f.draw()
tail_run = g['_runs'][-1]
tail_xs = [x for chunk in tail_run[2] for x, y in chunk]
check("a fish's tail trails behind it", max(tail_xs) <= 0, max(tail_xs))
g['_runs'].clear()

# the nose and tail caps are part of the hit shape now
g['start_round']()
sub = g['sub11']
(nx, ny), (tx, ty) = sub.nose_tail()
check("the nose cap can be hit", g['hits_sub'](sub, nx + g['HULL_R'] - 3, ny, 2))
check("the tail cap can be hit", g['hits_sub'](sub, tx - g['HULL_R'] + 3, ty, 2))
box = sub.get_bounding_box()
check("the empty water over the tail is not part of the hull",
      not g['hits_sub'](sub, box.x + 6, box.y + box.height - 4, 2))

# a torpedo registers the frame its nose touches, even on a long frame
g['start_round']()
sub = g['sub22']
box = sub.get_bounding_box()
cy = sub.center()[1]
tor = g['Torpedo'](box.x - 120, cy, 1000, 0, 1)
g['torpedo1'].append(tor)
sub.flash = 0.0
g['update_torpedoes'](0.05)          # 50 units: the nose goes from 94 short to 44 short
check("a torpedo that has not reached the hull has not hit it", sub.life == sub.max_life)
g['update_torpedoes'](0.05)          # the nose now reaches past the cap's edge
check("a torpedo hits the frame its nose touches", sub.life == sub.max_life - 1, sub.life)

# nothing slips through a thin part between frames
g['start_round']()
sub = g['sub22']
ap = sub.air_duct
px = (ap['ap1'][0] + ap['ap2'][0]) / 2
tor = g['Torpedo'](px, ap['ap1'][1] + 70, 0, -1000, 1)
g['torpedo1'].append(tor)
sub.flash = 0.0
for _ in range(4):
    g['update_torpedoes'](0.05)
check("a fast torpedo cannot skip over the periscope", sub.life == sub.max_life - 1, sub.life)

# torpedoes end on the waterline, not above it
g['start_round']()
tor = g['Torpedo'](0, g['SURFACE_Y'] - 40, 0, 1000, 1)
g['torpedo1'].append(tor)
highest = tor.y
for _ in range(5):
    g['update_torpedoes'](0.016)
    if g['torpedo1']:
        highest = max(highest, g['torpedo1'][0].y + g['TORPEDO_NOSE'])
check("a torpedo stops at the surface", not g['torpedo1'] and highest <= g['SURFACE_Y'] + 17,
      highest)

# the two submarines are solid to each other
g['start_round']()
a1, b1 = g['sub11'], g['sub22']
a1.move_by(-a1.center()[0] - 60, 0)
b1.move_by(-b1.center()[0] + 60, 0)
a1.facing, b1.facing = a1.facing, b1.facing
for _ in range(40):
    a1.vx, b1.vx = 300.0, -300.0
    g['apply_physics'](1 / 60)
ba, bb = a1.solid_boxes()[0], b1.solid_boxes()[0]
overlap = min(ba[2], bb[2]) - max(ba[0], bb[0])
check("two submarines cannot pass through each other", overlap <= 1.0, overlap)

# the wreck's side is a wall, not a step you teleport up
g['start_round']()
s = g['sub11']
cx, cy = s.center()
s.move_by(-450 - cx, 0)
for _ in range(200):
    s.vy = -400.0
    g['apply_physics'](1 / 60)
low_y = s.extent()[1]
ys = []
for _ in range(120):
    s.vx = 300.0
    g['apply_physics'](1 / 60)
    ys.append(s.extent()[1])
check("a submarine on the sand is stopped by the side of the wreck",
      s.solid_boxes()[0][2] <= g['WRECK'][0] + 1, s.solid_boxes()[0][2])
check("and does not jump up onto it", max(ys) - low_y < 1, max(ys) - low_y)

# the torpedo tube: it swings towards the keys and stays where it is left
g['start_round']()
s = g['sub11']
check("player one starts facing right", s.facing == 1)
g['held'].add(b'a')
frames(60)          # half a turn at AIM_TURN takes 0.7 s; each frame is at least 0.02 s
g['held'].discard(b'a')
check("holding left swings the tube round", abs(abs(s.aim) - math.pi) < 0.05, s.aim)
check("and the hull turns to face it", s.facing == -1)
check("with the nose now on the left", s.nose_tail()[0][0] < s.nose_tail()[1][0])
g['held'].add(b'w')
frames(4)
g['held'].discard(b'w')
held_at = s.aim
frames(20)
check("letting go leaves the tube where it was", abs(s.aim - held_at) < 1e-9, (held_at, s.aim))
check("part way round, so an angle can be set", 1.6 < abs(held_at) < 3.1, held_at)
s.vx = s.vy = 0.0
g['tor_time1'] = 0
g['torpedo1'].clear()
g['fire'](s)
t = g['torpedo1'][-1]
check("a torpedo leaves along the tube, not the way the hull drifts",
      abs(math.atan2(t.vy, t.vx) - s.aim) < 0.01, (math.atan2(t.vy, t.vx), s.aim))

# aim assist: close to the enemy counts as on it
g['start_round']()
s, e = g['sub11'], g['sub22']
cx, cy = s.center()
ex, ey = e.center()
want = math.atan2(ey - cy, ex - cx)
s.aim = want + math.radians(6)
ux, uy = g['aim_of'](s)
check("a shot a few degrees off is nudged onto the enemy",
      abs(math.atan2(uy, ux) - want) < 1e-6)
s.aim = want + math.radians(20)
ux, uy = g['aim_of'](s)
check("but a shot well off is not", abs(math.atan2(uy, ux) - want) > math.radians(15))

# light and heavy torpedoes
check("the heavy torpedo hits harder",
      g['WEAPONS']['heavy']['damage'] > g['WEAPONS']['light']['damage'])
check("and takes longer to reload",
      g['WEAPONS']['heavy']['reload'] > g['WEAPONS']['light']['reload'])
g['start_round']()
s = g['sub11']
g['fire'](s, 'heavy')
g['fire'](s, 'light')
kinds = sorted(t.kind for t in g['torpedo1'])
check("both kinds can be fired together, on their own reloads", kinds == ['heavy', 'light'], kinds)
g['fire'](s, 'heavy')
check("the heavy one cannot be fired again at once",
      sum(t.kind == 'heavy' for t in g['torpedo1']) == 1)

g['start_round']()
e = g['sub22']
cx, cy = e.center()
e.flash = 0.0
g['torpedo1'].append(g['Torpedo'](cx - 200, cy, 420, 0, 1, 'heavy'))
for _ in range(40):
    g['update_torpedoes'](1 / 60)
check("a heavy torpedo takes three lives", e.life == e.max_life - 3, e.life)

# the heavy torpedo homes, gently - on HARD, where homing, blast and decoys are
g['cpu_level'] = 2
g['start_round']()
e = g['sub22']
cx, cy = e.center()
tor = g['Torpedo'](cx - 500, cy - 120, 420, 0, 1, 'heavy')
g['torpedo1'].append(tor)
for _ in range(20):
    g['update_torpedoes'](1 / 60)
check("a heavy torpedo turns towards its target", tor.vy > 5, tor.vy)
check("but no faster than it is allowed to",
      math.degrees(math.atan2(tor.vy, tor.vx)) <= math.degrees(20 / 60 * 1.0) + 1e-6,
      math.degrees(math.atan2(tor.vy, tor.vx)))
light = g['Torpedo'](cx - 500, cy - 120, 650, 0, 1)
g['torpedo1'].append(light)
g['update_torpedoes'](1 / 60)
check("a light torpedo runs straight", light.vy == 0)

# a decoy draws a heavy torpedo off
g['start_round']()
e = g['sub22']
cx, cy = e.center()
tor = g['Torpedo'](cx - 400, cy, 420, 0, 1, 'heavy')
g['torpedo1'].append(tor)
g['decoys'].append(g['Decoy'](cx - 250, cy + 120, 2))
for _ in range(20):
    g['update_torpedoes'](1 / 60)
check("a heavy torpedo goes for a decoy instead", tor.vy > 5 or not tor.active, tor.vy)

# its blast hurts on a near miss, a light one's does not
g['start_round']()
e = g['sub22']
e.flash = 0.0
ex, ey = e.center()
heavy = g['Torpedo'](ex, ey + 110, 0, 0, 1, 'heavy')
g['detonate'](heavy, ex, ey + 110)
check("a heavy torpedo's blast hurts near it", e.life == e.max_life - 1, e.life)
e.flash = 0.0
g['detonate'](g['Torpedo'](ex, ey + 110, 0, 0, 1), ex, ey + 110)
check("a light one's does not", e.life == e.max_life - 1, e.life)

# the levels: EASY is light torpedoes only, NORMAL adds a straight heavy
# torpedo, HARD makes it home and blast and adds decoys
g['cpu_level'] = 0
g['start_round']()
s = g['sub11']
g['fire'](s, 'heavy')
check("EASY has no heavy torpedo", not g['torpedo1'])
check("EASY has no decoy", not g['drop_decoy'](s) and not g['decoys'])
g['fire'](s)
check("EASY still has the light torpedo", len(g['torpedo1']) == 1)

g['cpu_level'] = 1
g['start_round']()
s, e = g['sub11'], g['sub22']
g['fire'](s, 'heavy')
check("NORMAL has the heavy torpedo", [t.kind for t in g['torpedo1']] == ['heavy'])
check("but no decoy", not g['drop_decoy'](e))
cx, cy = e.center()
tor = g['Torpedo'](cx - 500, cy - 120, 420, 0, 1, 'heavy')
g['torpedo1'][:] = [tor]
for _ in range(20):
    g['update_torpedoes'](1 / 60)
check("and on NORMAL it runs straight", tor.vy == 0, tor.vy)
e.flash = 0.0
g['detonate'](g['Torpedo'](cx, cy + 110, 0, 0, 1, 'heavy'), cx, cy + 110)
check("with no blast", e.life == e.max_life, e.life)

g['cpu_level'] = 2
g['start_round']()
check("HARD has the decoy", g['drop_decoy'](g['sub11']))
g['cpu_level'] = 1

# the level can be chosen for two players as well
g['keyboardListener'](b'\x1b', 0, 0)
g['menu_choice'] = 1
g['keyboardListener'](b'd', 0, 0)
check("the level can be changed on the two player row", g['cpu_level'] == 2, g['cpu_level'])
g['keyboardListener'](b'a', 0, 0)
g['keyboardListener'](b'a', 0, 0)
check("down to EASY", g['cpu_level'] == 0, g['cpu_level'])
g['keyboardListener'](b'\r', 0, 0)
check("and a two player game starts on it", not g['vs_cpu'] and g['cpu_level'] == 0)
g['cpu_level'] = 1

# lives
check("each submarine has ten lives", g['sub11'].max_life == 10)

# dash
g['start_round']()
s = g['sub11']
s.ix, s.iy = 0.0, 1.0
check("a dash goes", g['dash'](s) and s.vy > 800)
check("and has to reload", not g['dash'](s))

# the READY countdown holds fire
g['READY_TIME'] = 1.0
g['start_round']()
g['tor_time1'] = 0
g['fire'](g['sub11'])
check("nothing can be fired during READY", not g['torpedo1'])
g['READY_TIME'] = 0.0

# holding fire keeps firing
g['start_round']()
g['held'].add(b' ')
for _ in range(90):
    a(); d()
g['held'].discard(b' ')
check("holding fire keeps firing", g['stats'][1]['shots'] >= 2, g['stats'][1]['shots'])

# help pauses a game and closing it resumes
g['start_round']()
g['keyboardListener'](b'h', 0, 0)
check("h opens the help and pauses", g['show_help'] and g['paused'])
g['keyboardListener'](b'h', 0, 0)
check("h again closes it and resumes", not g['show_help'] and not g['paused'])

# the computer plays a whole match on its own without anything going wrong
g['keyboardListener'](b'\x1b', 0, 0)
g['menu_choice'] = 0
g['cpu_level'] = 2
g['keyboardListener'](b'\r', 0, 0)
check("the first menu row starts a game against the computer", g['vs_cpu'])
shots = 0
err = ''
try:
    for _ in range(600):
        a(); d()
        if g['state'] != g['STATE_PLAY'] and g['state'] != g['STATE_SINKING']:
            break
except Exception as e:
    err = repr(e)
check("the computer plays without an error", not err, err)
check("the computer shoots", g['stats'][2]['shots'] > 0, g['stats'][2]['shots'])
check("the computer swims", abs(g['sub22'].center()[0] - 580) > 30, g['sub22'].center())

# the computer is fair: it gets no aim snap, and it aims at where it last
# saw you, not where you are
g['cpu_level'] = 1
g['vs_cpu'] = True
g['start_round']()
cpu_sub, you = g['sub22'], g['sub11']
cx, cy = cpu_sub.center()
yx, yy = you.center()
cpu_sub.aim = math.atan2(yy - cy, yx - cx) + math.radians(5)
ux, uy = g['aim_of'](cpu_sub)
check("the computer gets no aim snap",
      abs((math.atan2(uy, ux) - cpu_sub.aim + math.pi) % (2 * math.pi) - math.pi) < 1e-9)
g['cpu'].reset()
g['cpu_update'](cpu_sub, you, 1 / 60)
seen = g['cpu'].spotted
you.move_by(0, -200)
g['cpu_update'](cpu_sub, you, 1 / 60)
check("the computer does not see you move until it looks again",
      g['cpu'].spotted == seen, (seen, g['cpu'].spotted))
for _ in range(120):
    g['cpu_update'](cpu_sub, you, 1 / 60)
check("but it does look again", g['cpu'].spotted != seen)
g['vs_cpu'] = False

# the record is kept between runs (a win against the computer on Hard)
g['vs_cpu'] = True
g['cpu_level'] = 2
g['records']['wins'] = [0, 0, 0]
g['records']['streak'] = 0
g['state'] = g['STATE_PLAY']
g['score'][1] = g['ROUNDS_TO_WIN'] - 1
g['end_round'](1)
check("beating the computer is recorded", g['load_records']()['wins'][2] == 1,
      g['load_records']())
g['vs_cpu'] = False

# a maximised window keeps the world's shape, and the points grow with it so
# the gaps between them never show as a grid
g['reshape'](1906, 990)
# a hit earlier may have left the screen shaking, which offsets the mouse
g['shake'] = g['shake_x'] = g['shake_y'] = 0.0
check("a wide window keeps the world's shape",
      abs(g['VIEW_W'] / g['VIEW_H'] - 1366 / 768) < 0.01, (g['VIEW_W'], g['VIEW_H']))
check("with the world centred in it", g['VIEW_X'] > 0 and g['VIEW_Y'] == 0,
      (g['VIEW_X'], g['VIEW_Y']))
check("points grow with the window, so fills stay solid",
      all(g['point_px'](s) >= s * g['PIXEL_SCALE'] for s in (2, 3, 5, 8, 9)))
cx, cy = g['convert_coordinate'](1906 / 2, 990 / 2)
check("the middle of the window is the middle of the world", abs(cx) < 1 and abs(cy) < 1,
      (cx, cy))
lx, _ = g['convert_coordinate'](g['VIEW_X'], 0)
check("the left edge of the picture is the left wall", abs(lx - g['WORLD_L']) < 1, lx)
check("a resize rebuilds the baked background", g['background_update_needed'])
g['reshape'](1366, 768)
frames(2)


print("\n" + "="*58)
print(f"  {len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL: print("   FAILED: " + f)
print("="*58)
sys.exit(1 if FAIL else 0)

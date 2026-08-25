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

src = open(GAME).read().replace('glutMainLoop()','')
g={'__name__':'__main__'}
exec(compile(src, GAME, 'exec'), g)
d, a = g['display'], g['animate']
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
        g['damage'](sub, 1)
        frames(5)

random.seed(7)
frames(3)
check("the game opens on the menu", g['state'] == g['STATE_MENU'], g['state'])

g['keyboardListener'](b'\r', 0, 0); frames(3)
check("enter starts a round", g['state'] == g['STATE_PLAY'], g['state'])
check("both submarines start alive", g['sub11'].life == 5 and g['sub22'].life == 5)
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
check("a hit takes one life", g['sub22'].life == 4, g['sub22'].life)

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
hit(g['sub22'], 9)
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
check("the next round restores full health", g['sub22'].life == 5)

# win the match
hit(g['sub22'], 9)
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
check("a health pickup heals", g['sub11'].life == 4, g['sub11'].life)
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
g['sub22'].vx, g['sub22'].vy = -300.0, -300.0
g['tor_time2'] = 0
g['fire'](g['sub22'])
t2 = g['torpedo2'][-1]
check("player two's torpedo goes the way it is pointed", t2.vx < 0 and t2.vy < 0,
      (t2.vx, t2.vy))
g['sub11'].vx, g['sub11'].vy = 300.0, -300.0
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
hit(g['sub22'], 9)
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
for _ in range(9):
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
    a()
after = time.time() - g['last_mine_time']
check("a pause does not bank up spawn cooldowns", abs(after - before) < 0.15,
      (before, after))
g['paused'] = False


print("\n" + "="*58)
print(f"  {len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL: print("   FAILED: " + f)
print("="*58)
sys.exit(1 if FAIL else 0)

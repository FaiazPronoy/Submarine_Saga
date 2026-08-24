# Submarine Saga

A two player submarine duel, drawn entirely with `GL_POINTS`. Every line comes
from the midpoint line algorithm and every circle from the midpoint circle
algorithm, with the eight zone conversions in between — no `GL_LINES`, no
`GL_POLYGON`, no textures.

Built as the **CSE423 Computer Graphics** project at BRAC University.
Python and PyOpenGL, one file, no assets.

---

## Running it

```bash
python "Submarine Saga (CSE423 Project).py"
```

Nothing has to be installed: the `OpenGL` folder beside this file is a copy of
PyOpenGL, and Python finds it because it sits next to the script.

`numpy` is used if it is there and skipped if it is not. With it, the point
batches go to OpenGL as vertex arrays and the game runs noticeably faster; take
it if you have it:

```bash
pip install numpy
```

## Controls

| | Left submarine (Markava) | Right submarine (Destroyer) |
|---|---|---|
| Move | `W` `A` `S` `D` | arrow keys |
| Fire | `C` | `P` |

**A torpedo goes wherever the submarine is moving.** The dotted line out of the
nose is where the next one will go. Standing still fires level. So lining up a
shot and getting out of the way are the same set of keys, and they pull against
each other — that is the game.

`Enter` start / next round · `I` pause · `R` restart the match ·
`N` day and night · `Esc` back to the menu.
The three buttons along the bottom do restart, pause and quit to the menu.

## How a match works

Each submarine starts with five lives. Lose them all and you sink, and the
other player takes the round. **First to two rounds wins the match.** The score
sits next to each name in the corner panels.

Things that will hurt you:

- **Torpedoes** from the other player, in whatever direction they were heading
- **Depth charges** from the boat above. A yellow bracket marks the sand where
  each one is going to land, so the pass can be read before it arrives
- **Drifting mines.** A tightening ring means one is still arming and cannot
  hurt you yet; a blinking ring means it is about to expire
- **A shark.** A fin cuts the surface a second before it appears

Nothing here is only a hazard. **A torpedo destroys a mine, kills a shark, and
shoots down another torpedo**, so the things in the water are something to use
rather than only something to survive. The **wreck on the seabed is solid** —
torpedoes and depth charges break against it, so it is real cover, and it is
the one fixed thing on the map worth fighting over.

If you are down to your last life you move faster, reload faster, and pickups
start falling on your side.

Things worth swimming for — they fall from the surface and drift as they go:

| | |
|---|---|
| red cross | two lives back |
| blue ring | a shield that absorbs the next hit |
| yellow bolt | rapid fire, half the usual reload |
| green arrow | a speed boost |

## What changed in this version

The first version worked, but it ran at about **twelve frames a second** and
both submarines were the same colour, so you could not tell which one was
yours.

**Speed.** `draw_points` opened and closed a `glBegin`/`glEnd` block for every
single point, and the whole screen is points. Points are now collected into
runs of the same colour and size and sent as one vertex array each, and the
midpoint circle results are cached because the same radius comes up every
frame. The algorithms themselves are untouched — the same points end up on
screen, in the same order.

**Movement.** A key press moved a submarine a fixed twenty units, so how fast
you travelled depended on the operating system's key repeat rate, and holding a
key gave a stutter. Keys now set an intent, and a physics step runs once a
frame with acceleration, drag and walls, so a submarine builds up speed and
coasts when you let go.

**Aiming.** Torpedoes steered themselves to the other player, so firing was
never a decision — you held the key down and thought only about dodging. They
now go where you are pointing. That also fixed two bugs the auto-aim was
hiding: player two's torpedoes climbed when they should have dived, because the
vertical component was negated twice, and firing while the two submarines were
on the same vertical line divided by zero and killed the game.

**Collisions.** `get_bounding_box` returned the centre of the hull while
`has_collided` expects the bottom left corner, so every box test in the game was
off by half a submarine. The hit radii were also three to ten times the size of
the thing being drawn — a depth charge is 7 pixels across and killed you from
70 away. Every radius now matches the art and lives beside the other tunables at
the top of the file.

**Taking four hits in one frame.** Nothing stopped the torpedoes, the depth
charges, the mines and the shark from all calling `damage()` on the same frame,
so you could lose four of five lives at once with a single flash to show for it.
A hit now grants a short moment of invulnerability.

**Depth charges going to infinity.** The sideways speed was `1/tan(angle)` with
the angle picked from a sixty degree range. At some angles a charge fell dead
straight; at others it crossed the map in a single frame and was gone before it
could be seen. It is a plain horizontal speed now.

**Diagonal movement was 41% faster**, because the speed cap was applied to each
axis separately. Travelling at an angle was strictly the best way to move.

**Keys sticking down.** Alt tab while holding a key and the key up event went to
the other window, so the submarine accelerated into the wall for ever. There is
a focus handler now, and `glutIgnoreKeyRepeat` stops the auto repeat making the
held key set flicker.

**Bookkeeping.** Bubbles, sharks, spent torpedoes and used pickups were never
removed from their lists, so a long game got slower and slower.

**Drawing.** `draw_filled_shape` only ever drew the outline of a shape, which
is why the submarines looked like wireframes. There is a scanline fill now, so
a hull is a hull, and the function is called `draw_outline` because that is
what it does.

**New:** heading based aiming with an aim line, torpedoes that destroy mines,
sharks and each other, the wreck as cover, warning markers on the depth charges
and the shark, a last stand for whoever is behind, the round and match system,
the title screen, four kinds of pickup instead of one, mines that arm and
expire, explosion particles, fish, seaweed, light shafts, a depth gradient, a
wavy surface, screen shake, and a head up display with health, lives, reload
and the power ups that are running.

## Layout

```
Submarine Saga (CSE423 Project).py
├── point batching          set_color, draw_points_batch, flush_points
├── midpoint line           MidPointLine, findZone, convertToZone0, convertToZoneM
├── midpoint circle         MidPointCircle, zone_converter, disc_points
├── shape helpers           draw_lines, draw_filled_circle, fill_polygon, fill_gradient
├── background              sky, water, seabed, seaweed, light rays, sun and moon
├── entities                Torpedo, Bubble, rain, Particle, Fish, Mine,
│                           UniqueCircle, Shark, submarine
├── HUD                     health bars, lives, reload, power ups, banners
├── rounds                  start_round, end_round, next_round, reset_game
├── input                   held keys, apply_input, fire
└── frame                   display, animate, GLUT callbacks
```

## Tests

`tests/test_game.py` drives the game without anyone at the keyboard: it starts
a match, holds keys, fires, takes damage, wins rounds, and checks the entity
lists do not grow for ever. It covers the crash and the leaks described above,
so they cannot come back quietly.

```bash
python tests/test_game.py
```

It works from any directory. The test lives in `tests/`, so Python puts *that*
folder on the import path rather than the project root, and the bundled
`OpenGL` copy would not be found — the test puts the project root on the path
itself before importing anything.

**59 checks, all passing.** They include one per bug listed above, so none of
them can come back quietly: both players' torpedoes are checked for direction,
the collision box is checked against the hull it belongs to, four hits in one
frame are checked to cost one life, and three hundred depth charge passes are
checked for a sane speed.

## Known limitations

- There is no sound. GLUT has no audio of its own.
- Both players share one keyboard; there is no network play.
- The frame rate depends on the graphics driver, because everything is drawn as
  individual points. It is comfortable on a normal laptop and slow inside a
  virtual machine with software rendering.

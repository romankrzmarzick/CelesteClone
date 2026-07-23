# Architecture

How the pieces fit and where to add new things. Written to be read cold after
time away.

---

## The big picture

Three layers, each talking only to the one below:

```
Game (main.py)          window, assets, the loop, dt
  └─ Level (level.py)      sprite groups, the Tiled map, death/respawn
      └─ Player (player.py) + Sprite (sprites.py)
```

`settings.py`, `support.py`, `groups.py`, `event_timers.py` are shared helpers.

**The low-res canvas.** Nothing draws to the window directly. Everything draws
onto `internal_canvas`, a 320×180 surface, which is scaled ×5 to the window once
per frame. That is why every number is small — a tile is 8px, the hitbox is
7×13, top speed is 60. Only the two lines in `Game.run` know about `SCALE`.

**dt.** Seconds since the last frame. Speeds are pixels/second (accelerations
pixels/second²), multiplied by `dt` where applied, so movement is identical at
any framerate. The loop is capped to `FRAMERATE` (60) and `dt` is clamped to
`MAX_DT` (0.05s), so a hitch runs in slow motion instead of tunnelling the
player through a wall.

---

## One frame

```
Game.run
 ├─ dt = clamp(clock.tick(60) / 1000, MAX_DT)
 ├─ drain events (quit only, for now)
 ├─ Level.run(dt)
 │   ├─ fill the background
 │   ├─ all_sprites.update(dt)  → Player.update:
 │   │     update_timers · old_rect · input · contact · move · animate
 │   ├─ all_sprites.draw()      z-sorted blits
 │   └─ death check / respawn
 └─ scale up, blit to window, flip
```

Two orderings carry the design:

- **`contact` before `move`** — every movement decision is made against the
  world as it was at the start of the frame.
- **`old_rect` captured first** — collision resolution needs to know where the
  player *was* to tell which side of a tile it hit.

---

## The player's rects and vectors

| Rect | Size | Purpose |
| --- | --- | --- |
| `rect` | 15×17 | drawing only — where the image is blitted |
| `hitbox_rect` | 7×13 | everything else — movement, collision, probe origins |
| `old_rect` | 7×13 | where the hitbox was last frame |

The hitbox is `rect.inflate((-8, -4))`, narrower than the art so arms and hair
don't clip walls. Physics moves the hitbox; `update_rect()` drags the drawn
`rect` behind it with a small cosmetic nudge from `ANIMATION_CORRECTION`.

> A new animation state needs an entry in **both** `ANIMATION_INFO` and
> `ANIMATION_CORRECTION`, or you get a KeyError.

- `dir_vector` — **intent**, components −1/0/1 from the keyboard. Not
  overwritten during a dash, wall jump, or mantle; those own the direction.
- `move_vector` — **velocity** in px/s. Built up by gravity/acceleration,
  zeroed by collisions.

---

## contact() — how the game feels the world

Each question gets its own thin probe rect just outside the hitbox, tested
against the tiles. This is where most of the game's character comes from.

```
        climb ▏                  ← 7px beside the upper body
    ┌──────────┐
left▏│          │▕right           ← middle third of each side
    │  hitbox  │
    │   7×13   │▕dangle           ← 1px beside the upper body
    └──────────┘
    ▔▔▔▔▔▔▔▔▔▔▔▔ floor            ← strip along the bottom
         ▏edge                    ← 4px below the leading foot
         ▏embrace                 ← 5 tiles below the centre
```

| Key | True when | Drives |
| --- | --- | --- |
| `floor` | bottom strip touches a tile | jumping, dash refresh, most states |
| `left` / `right` | a side strip touches a tile | wall slide, wall jump, climb |
| `edge` | leading foot over **nothing**, but on the floor | `balance` teeter |
| `dangle` | upper-body probe touches **nothing** on a wall | `dangle` hang |
| `mantle` | climb probe touches **nothing** while gripping | ledge pull-up |
| `embrace` | nothing within 5 tiles below while falling | long-fall clip |

⚠️ `edge`, `dangle`, `mantle`, `embrace` are inverted — true when the probe
hits **nothing**. The leading-edge probes (`climb`, `edge`, `dangle`) flip with
`facing_left`.

---

## move() — a priority chain

An ordered list; the first mode that applies **returns early** and skips the
rest. The order *is* the design.

```
1. mantle    pulling over a ledge — uninterruptible
2. climb     gripping a wall — gravity cancelled
3. crouch    frozen while the crouch clip plays
4. dash      fixed-speed burst — gravity and momentum cancelled
5. default   wall slide OR gravity → resolve y → walk → resolve x → jumps
```

**Axis-separated collision.** In the default path, y moves and resolves, then x
moves and resolves. One axis at a time against the same tiles is what stops the
player snagging on tile seams. `collisions()` reads `old_rect` to tell which
face was hit: used to be left of the tile and now overlapping → hit its left
face → snap flush.

> Every collidable carries an `old_rect`. Static tiles copy theirs once; a
> **moving platform must refresh its `old_rect` at the top of each frame**,
> before the player moves.

**Leapfrog integration.** `gravity()` and `x_move()` add half the acceleration
before the position update and half after, so a jump arc keeps its shape at any
framerate.

**Coyote time.** `contact()` arms the window on the one frame the floor vanishes
from under the player. The `move_vector.y >= 0` guard separates *walking* off a
ledge from *jumping* off one — arming on a jump would grant a free mid-air
second jump.

---

## Timers, states, animation

`Timer` (`event_timers.py`) is a millisecond countdown: `activate()`, check
`if timer.active:`, `update()` once a frame to close it. Real ms, not dt.

| Timer | ms | Protects |
| --- | --- | --- |
| `balance_delay` | 500 | wait before the idle teeter |
| `wall_jump` | 190 | locks out steering so the push off the wall lands |
| `wall_jump_delay` | 250 | stops a jump instantly becoming a wall jump |
| `dash` | 290 | dash duration |
| `dash_delay` | 230 | dash cooldown; re-armed each frame of a climb |
| `mantle` | 100 | ledge pull-up duration |
| `coyote` | 180 | late-jump grace after walking off a ledge |

**State choice.** `now_state()` is a priority ladder — death, dash, grounded,
wall, airborne — first match wins. The string it returns must match a folder in
`graphics/player/` and a key in `ANIMATION_INFO`.

**Transition clips.** `ANIMATION_TRANSITIONS` maps `(leaving, entering)` to a
one-shot glue clip (landing → `fall-ground`, jumping → `ground-jump`). It plays
to the end before anything interrupts — the `clip_in_progress` guard — giving
landings their thump and jumps their wind-up.

**Frames.** `frame_index += fps * dt`. Looping clips wrap; one-shot clips hold
the last frame. Art is drawn facing left, mirrored when facing right.

**Death.** A kill volume sets `player.dead`. `update` then skips
input/contact/move so the body freezes, `animate` plays the death clip and
`kill()`s the sprite on its last frame, and after 3500ms `Level.player_spawn`
builds a fresh Player — which resets all movement state for free.

---

## Gaps worth knowing

Nothing here is broken; these are just the shapes to know before building on top.

- **No camera.** `AllSprites.draw` blits at absolute positions, so the level
  can't exceed one 320×180 screen. Add an offset in `draw()` — that's the only
  change needed.
- **No level switching.** `Game.tmx_maps` is keyed by stage number, but
  `current_stage` is hardcoded to 0.
- **`from settings import *` everywhere.** Works fine, but it's why a name can
  be hard to trace. Converting to explicit imports touches every file, so do it
  as its own change, not mixed with gameplay.
- **Input is polled, not evented.** `input()` sees "key is down", not "key was
  pressed", so a held jump auto-bunnyhops. A jump buffer would need a real
  `KEYDOWN` event in `Game.run`.

---

## How to add things

**A player animation** — make `graphics/player/<name>/` with frames named
`0.png`, `1.png`, … (bare numbers); add `<name>` to `ANIMATION_INFO` and
`ANIMATION_CORRECTION`; return it from `now_state()` at the right priority.

**A level** — draw it in Tiled with layers `Entities`, `Terrain`, `Spikes`,
`Death`; add it to `Game.tmx_maps`. (Switching between levels isn't built yet.)

**An object** — loop over its Tiled layer in `Level.setup`; put it in
`all_sprites` to be drawn and in a purpose-built group to be interacted with.
In both = visible and solid, like terrain.

**A movement ability** — pick where it sits in the `move()` chain, give it a
`Timer` if it needs a duration, add a probe in `contact()` if it senses
something new, add its branch to `now_state()`.

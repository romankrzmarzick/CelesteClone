# Celeste Clone

A small 2D platformer in Python and pygame, inspired by Celeste. The point of the project
was to get the movement to feel right — that's most of the work.

The player can run, jump, crouch, climb walls, wall jump, and dash. Touch something deadly
and you respawn at the start of the level.

## Running it

You need Python, pygame, and pytmx:

```
pip install pygame pytmx
```

Then run it from the project folder:

```
python code/main.py
```

## Controls

| Key | Does |
| --- | --- |
| Left / Right arrows | Move |
| Up arrow | Jump |
| Down arrow | Crouch |
| Space | Grab a wall and climb |
| X | Dash |

## Movement details

A few things that make it feel less stiff:

- **Coyote time** — you can still jump for a moment after walking off a ledge
- **Wall jump** — pushes you off the wall and briefly locks steering so it reads as a jump
- **Dash** — one per touchdown, refills when you land

These are handled by a small timer class in `code/event_timers.py` rather than counters
scattered through the player code.

## How it's put together

- `code/main.py` — sets up the window and runs the loop
- `code/player.py` — all the movement and state
- `code/level.py` — builds the level, handles death and respawn
- `code/settings.py` — screen size, tile size, animation speeds
- `code/support.py` — loads the images

Levels are drawn in [Tiled](https://www.mapeditor.org/) and loaded from `data/maps`.

The game renders at 320×180 and scales up 5×, which is what gives it the pixel look.

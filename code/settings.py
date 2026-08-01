from dataclasses import dataclass
import pygame, sys
from pytmx.util_pygame import load_pygame
from os.path import join
from os import walk
from pygame.math import Vector2 as vector
from pygame.time import get_ticks

# game renders at this low res onto an internal canvas, then gets scaled up by SCALE
WINDOW_WIDTH, WINDOW_HEIGHT = 320, 180
SCALE = 5

FRAMERATE = 120
MAX_DT = 0.05  # clamp so a lag spike slows the game down instead of clipping through walls

TILE_SIZE = 8

# per clip: (fps, loops) - loops False means it holds on the last frame
ANIMATION_INFO: dict[str, dict[str, tuple[float, bool]]] = {
    "player" : {
        "idle" : (5, True),
        "run" : (12, True),
        "crouch" : (25, False),
        "push" : (10, True),
        "jump" : (1, False),
        "wall" : (1, False),
        "fall" : (5, False),
        "embrace" : (5, False),
        "climb" : (18, True),
        "balance" : (8, True),
        "dash" : (15, False),
        "fall-ground" : (35, False),
        "ground-jump" : (25, False),
        "death" :  (35, False),
        "dangle" : (8, True),
    }
}

# one-shot clips played between two states before the real state takes over,
# e.g. a little landing thump between falling and idle
ANIMATION_TRANSITIONS: dict[str, dict[tuple[str, str], str]] = {
    "player" : {
        ("embrace", "idle") : "fall-ground",
        ("embrace", "run") : "fall-ground",
        ("fall", "idle") : "fall-ground",
        ("fall", "run") : "fall-ground",
        ("idle", "jump") : "ground-jump",
        ("run", "jump") : "ground-jump",
    }
}

# nudges the drawn sprite without moving the hitbox, since the art isn't
# centred the same way in every clip (e.g. a wall-grab leans into the wall)
ANIMATION_CORRECTION: dict[str, dict[str, vector]] = {
    "player" : {
        "idle" : vector(0, -2),
        "run" : vector(0, -2),
        "crouch" : vector(0, -2),
        "push" : vector(2, -2),
        "jump" : vector(0, -2),
        "wall" : vector(1, -2),
        "fall" : vector(0, -2),
        "embrace" : vector(0, -2),
        "climb" : vector(1, -2),
        "balance" : vector(1, -2),
        "dash" : vector(1, -2),
        "fall-ground" : vector(0, -2),
        "ground-jump" : vector(0, -2),
        "death" :  vector(0, -2),
        "dangle" : vector(2, -2),
    }
}

# AllSprites.draw sorts by .z, lower drawn first (so it ends up behind).
# player sits on tile_details so the terrain layer draws over it
Z_LAYERS: dict[str, int] = {
	'bg': 0,
    "bg_details" : 1,
	'tiles': 2,
	'tile_details': 3,
	'main': 4,
	'fg': 5
}

# all the tuning numbers for how the player feels, pulled out here so I don't
# have to go hunting through player.py to tweak jump height etc
@dataclass(frozen=True)
class PlayerPhysics:
    x_acceleration : float = 420  # ground acceleration; 420/60 = ~0.14s to top speed
    x_max_speed    : float = 60   # horizontal speed cap
    jump_height    : float = 120  # upward launch speed for jump and wall jump
    gravity_num    : float = 330  # downward acceleration; /8 of this is the wall-slide speed
    max_fall_speed : float = 160  # terminal velocity
    dash_speed     : float = 130  # speed while the dash timer is running
    climbing_speed : float = 50   # up/down speed while gripping a wall
    mantle_x_speed : float = 40   # sideways shove when pulling over a ledge
    mantle_y_speed : float = 80   # upward shove when pulling over a ledge

PLAYER_PHYSICS = PlayerPhysics()

"""
Global configuration, and the shared import surface for the whole game.

Every module does `from settings import *`, so this is also where the common
names (pygame, vector, join, walk, load_pygame) enter them -- if you can't find
where something came from, it came from here.

Contents:
    - screen / loop / tile constants
    - ANIMATION_INFO         playback speed + looping per clip
    - ANIMATION_TRANSITIONS  one-shot clips played between two states
    - ANIMATION_CORRECTION   per-clip pixel nudge when drawing
    - Z_LAYERS               draw order
    - PlayerPhysics          every tunable movement number
"""

from dataclasses import dataclass
import pygame, sys
from pytmx.util_pygame import load_pygame
from os.path import join
from os import walk
from pygame.math import Vector2 as vector
from pygame.time import get_ticks

# --- Screen parameters -------------------------------------------------------
# The game renders at this low resolution onto an internal canvas, then scales
# up by SCALE to fill the window. All game logic works in these small pixels.
WINDOW_WIDTH, WINDOW_HEIGHT = 320, 180
SCALE = 5

# --- Loop timing -------------------------------------------------------------
FRAMERATE = 60   # loop cap; the physics is dt-scaled, so this just spares the CPU
MAX_DT = 0.05    # largest dt a frame may report (0.05 = 20 FPS); a hitch then
                 # runs in slow motion instead of tunnelling through a wall

# --- Tiles -------------------------------------------------------------------
TILE_SIZE = 8    # pixel size of one Tiled tile; converts grid coords to pixels

# --- Animation ---------------------------------------------------------------
# Per clip: (frames_per_second, loops)
#   frames_per_second : how fast frame_index advances (frame_index += fps * dt)
#   loops             : True -> wraps to frame 0 forever; False -> holds the last
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

# One-shot "glue" clips played between two states, keyed by (leaving, entering).
# The clip finishes before the real state takes over, which gives the landing
# thump and the jump wind-up their weight.
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

# Cosmetic offset per clip. The art isn't centred identically in every clip
# (a wall-grab leans into the wall), so this nudges the drawn image without
# moving the hitbox. Positive x = toward the facing direction; Player.update_rect
# mirrors it when facing right.
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

# --- Draw order --------------------------------------------------------------
# AllSprites.draw sorts by .z before blitting: lower is painted first, so it
# ends up behind. The player sits on "tile_details" so terrain ("main") draws
# over the top of it.
Z_LAYERS: dict[str, int] = {
	'bg': 0,
    "bg_details" : 1,
	'tiles': 2,
	'tile_details': 3,
	'main': 4,
	'fg': 5
}

# --- Player tuning -----------------------------------------------------------
@dataclass(frozen=True)
class PlayerPhysics:
    """
    Every number that decides how the player feels. Frozen so nothing can
    accidentally retune the game at runtime -- edit the values here instead.

    Units: speeds are internal pixels per second, accelerations are pixels per
    second squared. Both are multiplied by dt at the point of use, so the feel
    is identical at any framerate.
    """

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

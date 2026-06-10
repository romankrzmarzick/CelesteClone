from dataclasses import dataclass
import pygame, sys
from pytmx.util_pygame import load_pygame
from os.path import join
from os import walk
from pygame.math import Vector2 as vector
from pygame.time import get_ticks

# Screen parameters
WINDOW_WIDTH, WINDOW_HEIGHT = 320, 180
SCALE = 4

# Tiles
TILE_SIZE = 8

# The objects animation speed and looping boolean
ANIMATION_INFO = {
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

# Dictionary for the animations between the 
ANIMATION_TRANSITIONS = {
    "player" : {
        ("embrace", "idle") : "fall-ground",
        ("embrace", "run") : "fall-ground",
        ("fall", "idle") : "fall-ground",
        ("fall", "run") : "fall-ground",
        ("idle", "jump") : "ground-jump",
        ("run", "jump") : "ground-jump",
    }
}

# z-layers
Z_LAYERS = {
	'bg': 0,
    "bg_details" : 1,
	'tiles': 2,
	'tile_details': 3,
	'main': 4,
	'fg': 5
}

# player data class
@dataclass(frozen=True)
class PlayerPhysics:
    x_speed        : float = 7
    x_max_speed    : float = 60
    jump_height    : float = 120
    gravity_num    : float = 330
    max_fall_speed : float = 160
    dash_speed     : float = 130
    climbing_speed : float = 50
    mantle_x_speed : float = 65
    mantle_y_speed : float= 80

PLAYER_PHYSICS = PlayerPhysics()



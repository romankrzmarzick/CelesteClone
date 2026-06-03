import pygame, sys
from pytmx.util_pygame import load_pygame
from os.path import join
from os import walk
from pygame.math import Vector2
from pygame.time import get_ticks

WINDOW_WIDTH, WINDOW_HEIGHT = 320, 180
SCALE = 4
TILE_SIZE = 8
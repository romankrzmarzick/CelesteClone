import pygame, sys
from pytmx.util_pygame import load_pygame
from os.path import join
from os import walk
from pygame.math import Vector2

WINDOW_WIDTH, WINDOW_HEIGHT = 320, 180
SCALE = 1
TILE_SIZE = 16
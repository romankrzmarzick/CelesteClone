import pygame
from pygame.math import Vector2 as vector
from pygame.time import get_ticks
from enum import Enum, auto, IntEnum
from dataclasses import dataclass
from pathlib import Path
from pytmx.util_pygame import load_pygame

WINDOW_WIDTH, WINDOW_HEIGHT = 320, 180

SCALE = 5

FRAMERATE = 120
MAX_DT = 0.05

TILE_SIZE = 8


class Z_LAYERS(IntEnum):
    BACKGROUND = 0
    BACKGROUND_DETAILS = 1
    TILES = 2
    TILE_DETAILS = 3
    MAIN = 4
    FOREGROUND = 5


class Map(Enum):
    ENTITIES = "Entities"
    DEATH = "Death"
    SPIKES = "Spikes"
    TERRAIN = "Terrain"


class AnimationEntity(Enum):
    PLAYER = auto()


class ProbeType(Enum):
    FLOOR = auto()
    LEFT = auto()
    RIGHT = auto()
    DANGLE = auto()
    EDGE = auto()
    EMBRACE_FALL = auto()
    MANTLE = auto()


class TimerType(Enum):
    COYOTE = auto()
    DELAY_DASH = auto()
    MANTLE = auto()
    DASH = auto()
    WALL_JUMP_ACTION = auto()
    DELAY_WALL_JUMP = auto()
    DELAY_BALANCE = auto()


class PlayerAnimationState(Enum):
    IDLE = "idle"
    RUN = "run"
    CROUCH = "crouch"
    PUSH = "push"
    JUMP = "jump"
    WALL = "wall"
    FALL = "fall"
    EMBRACE_FALL = "embrace_fall"
    CLIMB = "climb"
    BALANCE = "balance"
    DASH = "dash"
    FALL_GROUND = "fall_ground"
    GROUND_JUMP = "ground_jump"
    DEATH = "death"
    DANGLE = "dangle"


ANIMATION_INFO: dict[
    AnimationEntity, dict[PlayerAnimationState, tuple[float, bool]]
] = {
    AnimationEntity.PLAYER: {
        PlayerAnimationState.IDLE: (5, True),
        PlayerAnimationState.RUN: (12, True),
        PlayerAnimationState.CROUCH: (25, False),
        PlayerAnimationState.PUSH: (10, True),
        PlayerAnimationState.JUMP: (1, False),
        PlayerAnimationState.WALL: (1, False),
        PlayerAnimationState.FALL: (5, False),
        PlayerAnimationState.EMBRACE_FALL: (5, False),
        PlayerAnimationState.CLIMB: (18, True),
        PlayerAnimationState.BALANCE: (8, True),
        PlayerAnimationState.DASH: (15, False),
        PlayerAnimationState.FALL_GROUND: (25, False),
        PlayerAnimationState.GROUND_JUMP: (45, False),
        PlayerAnimationState.DEATH: (35, False),
        PlayerAnimationState.DANGLE: (8, True),
    }
}

ANIMATION_TRANSITIONS: dict[
    AnimationEntity,
    dict[tuple[PlayerAnimationState, PlayerAnimationState], PlayerAnimationState],
] = {
    AnimationEntity.PLAYER: {
        (
            PlayerAnimationState.EMBRACE_FALL,
            PlayerAnimationState.IDLE,
        ): PlayerAnimationState.FALL_GROUND,
        (
            PlayerAnimationState.EMBRACE_FALL,
            PlayerAnimationState.RUN,
        ): PlayerAnimationState.FALL_GROUND,
        (
            PlayerAnimationState.FALL,
            PlayerAnimationState.IDLE,
        ): PlayerAnimationState.FALL_GROUND,
        (
            PlayerAnimationState.FALL,
            PlayerAnimationState.RUN,
        ): PlayerAnimationState.FALL_GROUND,
        (
            PlayerAnimationState.IDLE,
            PlayerAnimationState.JUMP,
        ): PlayerAnimationState.GROUND_JUMP,
        (
            PlayerAnimationState.RUN,
            PlayerAnimationState.JUMP,
        ): PlayerAnimationState.GROUND_JUMP,
    }
}

ANIMATION_CORRECTION: dict[AnimationEntity, dict[PlayerAnimationState, vector]] = {
    AnimationEntity.PLAYER: {
        PlayerAnimationState.IDLE: vector(0, -2),
        PlayerAnimationState.RUN: vector(0, -2),
        PlayerAnimationState.CROUCH: vector(0, -2),
        PlayerAnimationState.PUSH: vector(2, -2),
        PlayerAnimationState.JUMP: vector(0, -2),
        PlayerAnimationState.WALL: vector(1, -2),
        PlayerAnimationState.FALL: vector(0, -2),
        PlayerAnimationState.EMBRACE_FALL: vector(0, -2),
        PlayerAnimationState.CLIMB: vector(1, -2),
        PlayerAnimationState.BALANCE: vector(1, -2),
        PlayerAnimationState.DASH: vector(1, -2),
        PlayerAnimationState.FALL_GROUND: vector(0, -2),
        PlayerAnimationState.GROUND_JUMP: vector(0, -2),
        PlayerAnimationState.DEATH: vector(0, -2),
        PlayerAnimationState.DANGLE: vector(2, -2),
    }
}


@dataclass(frozen=True)
class PlayerPhysics:
    x_acceleration: float = 420  # ground acceleration; 420/60 = ~0.14s to top speed
    x_max_speed: float = 60  # horizontal speed cap
    jump_height: float = 120  # upward launch speed for jump and wall jump
    gravity_num: float = (
        330  # downward acceleration; /8 of this is the wall-slide speed
    )
    max_fall_speed: float = 160  # terminal velocity
    dash_speed: float = 130  # speed while the dash timer is running
    climbing_speed: float = 50  # up/down speed while gripping a wall
    mantle_x_speed: float = 40  # sideways shove when pulling over a ledge
    mantle_y_speed: float = 80  # upward shove when pulling over a ledge


PLAYER_PHYSICS = PlayerPhysics()

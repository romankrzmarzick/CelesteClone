from settings import pygame, vector


class DataStorage:
    def __init__(self) -> None:
        # live player hitbox, in the current map's local space
        self.player_rect: pygame.FRect | None = None
        # where the next Level should place the player, in the current map's local space
        self.player_position = vector(24, 128)
        # momentum/animation carried across a map transition, None on a fresh spawn
        self.player_state: dict | None = None
        self.current_map = 1
        self.last_check_point = 1
        self.spawn_position = vector(24, 128)

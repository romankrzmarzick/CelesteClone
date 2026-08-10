from settings import TILE_SIZE, pygame, vector, Z_LAYERS, Map
from sprites import Sprite
from player import Player
from groups import AllSprites
from event_timer import Timer

from debug import debugger


class Level:
    def __init__(
        self,
        internal_canvas: pygame.Surface,
        tmx_map,
        level_frames: dict,
        data_storage,
        world,
        tmx_map_rect,
    ) -> None:
        self.world = world
        self.data_storage = data_storage
        self.internal_canvas = internal_canvas
        self.all_sprites = AllSprites(self.internal_canvas)
        self.collision_sprites = pygame.sprite.Group()
        self.spike_sprites = pygame.sprite.Group()

        self.tmx_map = tmx_map
        self.tmx_map_rect = tmx_map_rect

        self.pixel_width = tmx_map.width * TILE_SIZE
        self.pixel_height = tmx_map.height * TILE_SIZE
        self.setup(self.tmx_map, level_frames)
        self.player_outside_map = False

    def setup(self, tmx_map, level_frames: dict) -> None:
        for obj in tmx_map.get_layer_by_name(Map.ENTITIES.value):
            if obj.name == "player":
                self.data_storage.spawn_position = vector(obj.x, obj.y)

        # one player, placed wherever the world told us to put them
        self.player = Player(
            self.data_storage.player_position,
            self.all_sprites,
            self.collision_sprites,
            level_frames["player"],
            Z_LAYERS.MAIN,
        )

        # arriving from a neighbouring map: keep the speed we came in with
        if self.data_storage.player_state is not None:
            self.player.restore(self.data_storage.player_state)
            self.data_storage.player_state = None

        for x, y, image in tmx_map.get_layer_by_name(Map.TERRAIN.value).tiles():
            Sprite(
                (x * TILE_SIZE, y * TILE_SIZE),
                image,
                (self.all_sprites, self.collision_sprites),
                z=Z_LAYERS.TILES,
            )

        for (
            x,
            y,
            image,
        ) in tmx_map.get_layer_by_name(Map.SPIKES.value).tiles():
            Sprite(
                (x * TILE_SIZE, y * TILE_SIZE),
                image,
                self.all_sprites,
                z=Z_LAYERS.TILES,
            )

        for obj in tmx_map.get_layer_by_name(Map.DEATH.value):
            Sprite(
                (obj.x, obj.y),
                pygame.Surface((obj.width, obj.height)),
                self.spike_sprites,
                z=Z_LAYERS.TILES,
            )

        for obj in tmx_map.get_layer_by_name("Boundaries"):
            if obj:
                Sprite(
                    (obj.x, obj.y),
                    pygame.Surface((obj.width, obj.height)),
                    self.collision_sprites,
                    z=Z_LAYERS.TILES,
                )

    def death_collide(self) -> None:
        if self.spike_sprites:
            for sprite in self.spike_sprites:
                if self.player.hitbox_rect.colliderect(sprite):
                    self.player.start_dying = True

    def check_map_constraint(self):
        # fire as soon as the player's centre leaves the map. waiting for the whole
        # hitbox to clear the edge costs ~6px of height, and a jump only has ~22px
        center_x, center_y = self.player.hitbox_rect.center

        if (
            center_x < 0
            or center_x > self.pixel_width
            or center_y < 0
            or center_y > self.pixel_height
        ):
            self.player_outside_map = True

    def run(self, dt: float) -> None:
        # background fill
        self.internal_canvas.fill("#263D3B")
        self.all_sprites.update(dt)
        self.all_sprites.draw()

        # passes in the player hitbox_rect for check map.
        self.data_storage.player_rect = self.player.hitbox_rect

        self.check_map_constraint()
        if self.player_outside_map:
            self.player_outside_map = False
            self.world.find_map()
            # this Level has just been replaced - stop touching its stale player
            return

        # death mechanic
        self.death_collide()
        if self.player.dead:
            self.player.kill()
            self.world.respawn()

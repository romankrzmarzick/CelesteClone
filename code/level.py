from settings import *
from sprites import *
from player import *
from groups import *


class Level:
    def __init__(self, internal_canvas, tmx_map, level_frames):
        self.internal_canvas = internal_canvas
        self.all_sprites = AllSprites(self.internal_canvas)
        self.collision_sprites = pygame.sprite.Group()
        self.setup(tmx_map, level_frames)

    def setup(self, tmx_map, level_frames):
        """
        Setup uses for loops with the passed in tmx_map from Tiled to pass information around to the designated classes.
        In parrallel, it also uses the level_frames parameter, which is the imported folders, to pass in the images.
        """
        for obj in tmx_map.get_layer_by_name("Entities"):
            if obj.name == "player":
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, level_frames["player"], Z_LAYERS["main"], self.internal_canvas)
        
        for x, y, image in tmx_map.get_layer_by_name("Terrain").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites), z=Z_LAYERS["tiles"])

        for x, y, image, in tmx_map.get_layer_by_name("Spikes").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites, z=Z_LAYERS["tile_details"])

    def run(self, dt):
        # background fill
        self.internal_canvas.fill("#263D3B")
        self.all_sprites.update(dt)
        self.all_sprites.draw()
      
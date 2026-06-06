from settings import *
from sprites import *
from player import *
from groups import AllSprites

class Level:
    def __init__(self, interal_canvas, tmx_map, level_frames):
        self.internal_canvas = interal_canvas
        self.all_sprites = AllSprites(self.internal_canvas)
        self.collision_sprites = pygame.sprite.Group()
        self.setup(tmx_map, level_frames)

    def setup(self, tmx_map, level_frames):
        for obj in tmx_map.get_layer_by_name("Entities"):
            if obj.name == "player":
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites, level_frames["player"])
        
        for x, y, image in tmx_map.get_layer_by_name("Terrian").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites))

        for x, y, image, in tmx_map.get_layer_by_name("Spikes").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)

        for obj in tmx_map.get_layer_by_name("Death"):
            CollisionSprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.collision_sprites)



    def run(self, dt):
        self.internal_canvas.fill("#263D3B")
        self.all_sprites.update(dt)
        self.all_sprites.draw()
      
from settings import *
from sprites import *
from player import *
from groups import *
from event_timers import Timer

class Level:
    def __init__(self, internal_canvas, tmx_map, level_frames):
        self.internal_canvas = internal_canvas
        self.all_sprites = AllSprites(self.internal_canvas)
        self.collision_sprites = pygame.sprite.Group()
        self.spike_sprites = pygame.sprite.Group()
        
        self.player_frames = level_frames["player"]
        
        self.spawn_position = ()
        
        self.setup(tmx_map, level_frames)

        self.respawn_timer = Timer(3500, func=self.player_spawn)


    def setup(self, tmx_map, level_frames):
        """
        Setup uses for loops with the passed in tmx_map from Tiled to pass information around to the designated classes.
        In parrallel, it also uses the level_frames parameter, which is the imported folders, to pass in the images.
        """
        for obj in tmx_map.get_layer_by_name("Entities"):
            if obj.name == "player":
                self.spawn_position = (obj.x, obj.y)
                self.player = Player(self.spawn_position, self.all_sprites, self.collision_sprites, self.player_frames, Z_LAYERS["tile_details"])
        for x, y, image in tmx_map.get_layer_by_name("Terrain").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, (self.all_sprites, self.collision_sprites), z=Z_LAYERS["main"])

        for x, y, image, in tmx_map.get_layer_by_name("Spikes").tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites, z=Z_LAYERS["tiles"])

        for obj in tmx_map.get_layer_by_name("Death"):
            Sprite((obj.x, obj.y), pygame.Surface((obj.width, obj.height)), self.spike_sprites, z=Z_LAYERS["tiles"])

    def death_collide(self):
        if self.spike_sprites:
            for sprite in self.spike_sprites:
                if self.player.hitbox_rect.colliderect(sprite):
                    self.player.dead = True

    def respawn(self):
        if self.player.dead and not self.respawn_timer.active:
            self.respawn_timer.activate()
           

    def player_spawn(self):
        self.player = Player(self.spawn_position, self.all_sprites, self.collision_sprites, self.player_frames, Z_LAYERS["tile_details"])


    def run(self, dt):
        # background fill
        self.internal_canvas.fill("#263D3B")
        self.all_sprites.update(dt)
        self.all_sprites.draw()
       
        # death mechanic
        self.death_collide()
        if self.player.dead:
            self.respawn()
            self.respawn_timer.update()
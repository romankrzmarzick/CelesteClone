"""One playable stage: builds the world from a Tiled map and runs it."""

from settings import *
from sprites import *
from player import *
from groups import *
from event_timers import Timer


class Level:
    """
    Owns everything inside a single stage -- the sprite groups, the player, and
    the per-frame order of operations.

    Sprite groups:
        all_sprites       everything that gets drawn and updated.
        collision_sprites solid terrain the player is pushed out of.
        spike_sprites     invisible kill volumes; touched, never drawn.

    A sprite can be in more than one group: terrain tiles are in both
    all_sprites and collision_sprites, which is how one object is both visible
    and solid.
    """

    def __init__(self, internal_canvas: pygame.Surface, tmx_map, level_frames: dict) -> None:
        self.internal_canvas = internal_canvas
        self.all_sprites = AllSprites(self.internal_canvas)
        self.collision_sprites = pygame.sprite.Group()
        self.spike_sprites = pygame.sprite.Group()

        self.player_frames = level_frames["player"]

        self.spawn_position: tuple[float, float] = ()

        self.setup(tmx_map, level_frames)

        # Delay between dying and popping back in, long enough for the death
        # animation to play out.
        self.respawn_timer = Timer(3500, func=self.player_spawn)

    def setup(self, tmx_map, level_frames: dict) -> None:
        """
        Build the stage out of the Tiled map.

        Each named layer becomes a different kind of sprite, so adding content
        is mostly drawing it in Tiled and adding a loop here:

            "Entities"  objects; the one named "player" sets the spawn point.
            "Terrain"   tiles; solid ground, drawn and collidable.
            "Spikes"    tiles; spike artwork only, purely decorative.
            "Death"     objects; the rects that actually kill. Given a blank
                        surface and kept out of all_sprites, so invisible.

        Tile layers give grid coordinates, hence `* TILE_SIZE`; object layers
        already carry pixel positions.
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

    def death_collide(self) -> None:
        """Flag the player as dead if their hitbox overlaps any kill volume."""
        if self.spike_sprites:
            for sprite in self.spike_sprites:
                if self.player.hitbox_rect.colliderect(sprite):
                    self.player.dead = True

    def respawn(self) -> None:
        """Start the respawn countdown, once, on the frame the player dies."""
        if self.player.dead and not self.respawn_timer.active:
            self.respawn_timer.activate()

    def player_spawn(self) -> None:
        """
        Fired by `respawn_timer`: put a brand new player back at the spawn point.

        The old player already removed itself from its groups (Player.animate
        calls `kill()` on the last frame of the death clip), so replacing the
        object outright resets every bit of movement state for free.
        """
        self.player = Player(self.spawn_position, self.all_sprites, self.collision_sprites, self.player_frames, Z_LAYERS["tile_details"])

    def run(self, dt: float) -> None:
        """
        Advance and draw the stage for one frame.

        Order matters: update before draw, and the death check after the
        player has already moved this frame.
        """
        # background fill
        self.internal_canvas.fill("#263D3B")
        self.all_sprites.update(dt)
        self.all_sprites.draw()

        # death mechanic
        self.death_collide()
        if self.player.dead:
            self.respawn()
            self.respawn_timer.update()

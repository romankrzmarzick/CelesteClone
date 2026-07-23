"""Plain, non-moving sprites -- terrain tiles, spikes, and invisible triggers."""

from settings import *


class Sprite(pygame.sprite.Sprite):
    """
    A static image at a fixed position. Everything that isn't the player is one
    of these: terrain tiles, spike art, and the invisible death boxes.

    Args:
        pos:    top-left corner in internal pixels.
        image:  the surface to draw (invisible triggers pass a blank Surface
                and are kept out of the drawing group).
        groups: one group, or a tuple of groups, to join.
        z:      draw layer, see Z_LAYERS in settings.

    Attributes:
        old_rect: where the sprite was last frame. These never move, so it is
            just a copy of `rect` -- but Player.collisions reads it on whatever
            it hits, so every collidable needs one. A moving platform would
            have to refresh it at the top of each frame.
    """

    def __init__(
        self,
        pos: tuple[float, float],
        image: pygame.Surface,
        groups,
        z: int,
    ) -> None:
        super().__init__(groups)
        self.z = z
        self.image = image
        self.rect: pygame.FRect = self.image.get_frect(topleft=pos)
        self.old_rect: pygame.FRect = self.rect.copy()

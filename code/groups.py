"""Custom sprite groups -- currently just the one that owns drawing."""

from settings import *


class AllSprites(pygame.sprite.Group):
    """
    The group that draws the world.

    Subclassing Group replaces pygame's default `draw()`, so the game controls
    how sprites reach the screen -- currently sorting by `z` (see Z_LAYERS) so
    terrain can be painted over the player.

    This is also the hook for a camera: give the group an offset and blit at
    `sprite.rect.topleft - offset`. Nothing else would need to change.
    """

    def __init__(self, internal_canvas: pygame.Surface) -> None:
        super().__init__()
        self.internal_canvas = internal_canvas

    def draw(self) -> None:
        """Blit every sprite onto the internal canvas, back layer first."""
        for sprite in sorted(self, key=lambda s: s.z):
            self.internal_canvas.blit(sprite.image, sprite.rect.topleft)

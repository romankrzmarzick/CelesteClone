from settings import *

class AllSprites(pygame.sprite.Group):
    def __init__(self, internal_canvas: pygame.Surface) -> None:
        super().__init__()
        self.internal_canvas = internal_canvas

    def draw(self) -> None:
        """Blit every sprite onto the internal canvas, back layer first."""
        for sprite in sorted(self, key=lambda s: s.z):
            self.internal_canvas.blit(sprite.image, sprite.rect.topleft)

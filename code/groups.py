from settings import *

class AllSprites(pygame.sprite.Group):
    def __init__(self, internal_canvas):
        super().__init__()
        self.internal_canvas = internal_canvas
        self.offset = Vector2()

    def draw(self):
        for sprite in self:
            self.internal_canvas.blit(sprite.image, sprite.rect.topleft)
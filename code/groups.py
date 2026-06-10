from settings import *

class AllSprites(pygame.sprite.Group):
    """
    AllSprites as a class with pygame's Group is used to change and set custom properties to the draw method. 
    This can be used for controlling and constraining the camera during play. 
    """
    def __init__(self, internal_canvas):
        super().__init__()
        self.internal_canvas = internal_canvas

    def draw(self):
        for sprite in sorted(self, key=lambda s: s.z): # controlled draw method
            self.internal_canvas.blit(sprite.image, sprite.rect.topleft)
    